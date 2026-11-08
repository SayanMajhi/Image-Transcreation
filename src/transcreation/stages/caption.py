"""Caption an image with SmolVLM, including model loading and run measurements."""
from dataclasses import dataclass, field
import random
import time
from typing import Any, Callable, TypeVar

import torch
from PIL import Image

from transcreation.config import CaptionConfig
from transcreation.contracts import CaptionTaskResult

Decoded = TypeVar("Decoded")


def _transformers() -> Any:
    try:
        import transformers
    except ImportError as exc:
        raise RuntimeError("Install project dependencies: python -m pip install -e .") from exc
    if transformers.__version__ != "4.57.6":
        raise RuntimeError(
            f"Transformers {transformers.__version__} is installed; this adapter requires "
            "the compatibility-pinned transformers==4.57.6. Run python -m pip install -e ."
        )
    return transformers


def _seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    # Greedy/beam decoding is deterministic; avoid cuDNN algorithm benchmarking.
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def _sync(config: CaptionConfig) -> None:
    if config.device == "cuda":
        torch.cuda.synchronize()


def _load(config: CaptionConfig, processor_class: Any, model_class: Any,
          use_safetensors: bool = True, processor_options: dict[str, Any] | None = None,
          **extra: Any) -> tuple[Any, Any, float]:
    if config.device not in ("cpu", "cuda"):
        raise ValueError("Resolve device through create_captioner before constructing adapters")
    if config.device == "cpu" and config.precision != "float32":
        raise ValueError("CPU adapters require float32; use create_captioner for fallback")
    _seed(config.seed)
    _sync(config)
    start = time.perf_counter()
    kwargs = {"revision": config.revision, "trust_remote_code": False}
    processor = processor_class.from_pretrained(config.model_id, **kwargs, **(processor_options or {}))
    # Bind processor and weights to the same resolved commit, even for a moving branch.
    tokenizer = getattr(processor, "tokenizer", None)
    commit = getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
    if isinstance(commit, str):
        kwargs["revision"] = commit
    model = model_class.from_pretrained(
        config.model_id, **kwargs, dtype=getattr(torch, config.precision),
        use_safetensors=use_safetensors, **extra,
    ).to(config.device)
    model.eval()
    _sync(config)
    return processor, model, (time.perf_counter() - start) * 1000


def _run_inference(config: CaptionConfig, model: Any,
                   loading_ms: float, image: Image.Image,
                   prepare: Callable[[Image.Image], Any],
                   decode: Callable[[Any, Image.Image], Decoded]) -> tuple[Decoded, dict[str, Any]]:
    """Generate a caption and collect runtime measurements."""
    image = image.convert("RGB")
    _seed(config.seed)
    _sync(config)
    if config.device == "cuda":
        # Peak includes resident weights, excludes model-loading transients.
        torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    with torch.inference_mode():
        inputs = prepare(image)
        inputs = {
            key: value.to(
                device=config.device,
                dtype=getattr(torch, config.precision) if value.is_floating_point() else value.dtype,
            )
            for key, value in inputs.items()
        }
        generated = model.generate(**inputs, **config.generation_settings())
        # Move only output token IDs to CPU; don't retain GPU tensors in results.
        generated_cpu = generated.cpu()
        decoded = decode(generated_cpu, image)
        _sync(config)
        elapsed = (time.perf_counter() - start) * 1000
        peak = torch.cuda.max_memory_allocated() if config.device == "cuda" else None
        del inputs, generated, generated_cpu
    revision = getattr(model.config, "_commit_hash", None)
    return decoded, dict(
        model_id=config.model_id,
        resolved_revision=revision if isinstance(revision, str) else None,
        requested_revision=config.revision, image_dimensions=image.size,
        seed=config.seed, task=config.task, generation_settings=config.generation_settings(),
        device=config.device, precision=config.precision,
        torch_version=torch.__version__, transformers_version=_transformers().__version__,
        model_loading_ms=loading_ms, inference_ms=elapsed, peak_gpu_memory_bytes=peak,
    )


def _generated_token_count(tokens: Any, generation_config: Any,
                           skip_decoder_start: bool = True) -> int:
    """Count generated output IDs through EOS inclusive.

    Padding after EOS is excluded. This measures generated IDs, not a retokenization
    of the postprocessed caption, which can remove special tokens.
    """
    ids = tokens[0].tolist()[1 if skip_decoder_start else 0:]
    eos = generation_config.eos_token_id
    eos_ids = {eos} if isinstance(eos, int) else set(eos or [])
    for index, token in enumerate(ids):
        if token in eos_ids:
            return index + 1
    pad = generation_config.pad_token_id
    while ids and ids[-1] == pad:
        ids.pop()
    return len(ids)


PROMPT = (
    "Describe the visible objects, activities, and spatial relationships in this image. "
    "Use only visible evidence. Do not guess uncertain identities, cultural identities, "
    "locations, or events; describe their visible appearance instead."
)
PROCESSOR_SETTINGS = {"size": {"longest_edge": 1024}}
CONCISE_PROMPT = (
    "Describe the main subject, activity, important visible objects, and their relationships "
    "in at most four short sentences. Prioritize details essential to understanding the scene. "
    "Avoid repetition, speculation, and unsupported cultural identities. Do not describe minor "
    "background details unless they are important."
)
PROMPTS = {"default": PROMPT, "concise_grounded": CONCISE_PROMPT}


@dataclass(frozen=True)
class SmolCaptionResult(CaptionTaskResult):
    prompt_text: str = PROMPT
    formatted_prompt: str = ""
    processor_settings: dict[str, Any] = field(default_factory=dict)
    eos_reached: bool = False
    token_ceiling_reached: bool = False
    prompt_variant: str = "default"


class SmolVLMCaptioner:
    def __init__(self, config: CaptionConfig) -> None:
        self.config = config
        self.prompt_text = PROMPTS[config.prompt_variant]
        tf = _transformers()
        self.processor, self.model, self.loading_ms = _load(
            config, tf.AutoProcessor, tf.AutoModelForImageTextToText,
            processor_options=PROCESSOR_SETTINGS, attn_implementation="sdpa",
        )

    def caption(self, image: Image.Image) -> SmolCaptionResult:
        prompt_length = 0
        formatted_prompt = ""

        def prepare(rgb: Image.Image) -> Any:
            nonlocal prompt_length, formatted_prompt
            messages = [{"role": "user", "content": [
                {"type": "image"}, {"type": "text", "text": self.prompt_text},
            ]}]
            formatted_prompt = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
            inputs = self.processor(text=formatted_prompt, images=[rgb], return_tensors="pt")
            prompt_length = inputs["input_ids"].shape[-1]
            return inputs

        def decode(tokens: Any, rgb: Image.Image) -> dict[str, Any]:
            # Idefics3 is decoder-only: remove the entire image/text prompt before decoding.
            new_tokens = tokens[:, prompt_length:]
            text = self.processor.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()
            count = _generated_token_count(new_tokens, self.model.generation_config, skip_decoder_start=False)
            eos = self.model.generation_config.eos_token_id
            eos_ids = {eos} if isinstance(eos, int) else set(eos or [])
            return {"caption": text, "generated_tokens": count,
                    "eos_reached": any(token in eos_ids for token in new_tokens[0].tolist()),
                    "token_ceiling_reached": count >= self.config.max_new_tokens}

        decoded, metadata = _run_inference(
            self.config, self.model, self.loading_ms, image, prepare, decode,
        )
        image_processor = self.processor.image_processor
        settings = {
            "size": image_processor.size, "do_image_splitting": image_processor.do_image_splitting,
            "max_image_size": image_processor.max_image_size, "attention_implementation": "sdpa",
        }
        return SmolCaptionResult(**metadata, **decoded, prompt_text=self.prompt_text,
                                 formatted_prompt=formatted_prompt, processor_settings=settings,
                                 prompt_variant=self.config.prompt_variant)
