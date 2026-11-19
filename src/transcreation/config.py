"""Read and validate separate captioning and local Ollama settings."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
import math
from urllib.parse import urlparse

import yaml

MODEL_IDS = {
    "smolvlm": "HuggingFaceTB/SmolVLM-500M-Instruct",
}


@dataclass(frozen=True)
class CaptionConfig:
    active_model: str
    model_id: str
    revision: str | None = None
    device: str = "auto"
    precision: str = "float32"
    task: str = "caption"
    max_new_tokens: int = 128
    num_beams: int = 1
    seed: int = 42
    prompt_variant: str = "default"

    def __post_init__(self) -> None:
        if not isinstance(self.active_model, str) or self.active_model not in MODEL_IDS:
            raise ValueError("active_model must be 'smolvlm'")
        if self.prompt_variant not in ("default", "concise_grounded"):
            raise ValueError("prompt_variant must be default or concise_grounded")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("model_id must be a nonempty string")
        if self.model_id != MODEL_IDS["smolvlm"]:
            raise ValueError("model_id must be HuggingFaceTB/SmolVLM-500M-Instruct")
        if self.revision is not None and (
            not isinstance(self.revision, str) or not self.revision.strip()
        ):
            raise ValueError("revision must be a nonempty string or null")
        if self.device not in ("auto", "cpu", "cuda"):
            raise ValueError("device must be auto, cpu, or cuda")
        if self.precision not in ("float32", "float16"):
            raise ValueError("precision must be float32 or float16")
        tasks = {"caption"}
        if not isinstance(self.task, str) or self.task not in tasks:
            raise ValueError(f"task for {self.active_model} must be one of {sorted(tasks)}")
        for name in ("max_new_tokens", "num_beams"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be an integer in [0, 2**32)")

    def generation_settings(self) -> dict[str, Any]:
        return {
            "max_new_tokens": self.max_new_tokens,
            "num_beams": self.num_beams,
            "do_sample": False,
            "num_return_sequences": 1,
            "use_cache": True,
        }


def validate_config(config: Mapping[str, Any], model: str | None = None) -> CaptionConfig:
    if not isinstance(config, Mapping):
        raise ValueError("Configuration must be a mapping")
    unknown = set(config) - {"active_model", "models", "device", "precision", "seed"}
    if unknown:
        raise ValueError(f"Unknown configuration fields: {sorted(unknown, key=str)}")
    active = model if model is not None else config.get("active_model", "smolvlm")
    if not isinstance(active, str) or active not in MODEL_IDS:
        raise ValueError(f"Unsupported captioner: {active!r}; choose smolvlm")
    models = config.get("models")
    if not isinstance(models, Mapping) or active not in models:
        raise ValueError(f"Missing model settings for {active}")
    validated = {}
    for name, settings in models.items():
        if name not in MODEL_IDS:
            raise ValueError(f"Unsupported model in configuration: {name!r}")
        if not isinstance(settings, Mapping):
            raise ValueError(f"Model settings for {name} must be a mapping")
        unknown = set(settings) - {
            "model_id", "revision", "task", "max_new_tokens", "num_beams", "prompt_variant"
        }
        if unknown:
            raise ValueError(f"Unknown settings for {name}: {sorted(unknown, key=str)}")
        values = {
            "model_id": MODEL_IDS[name],
            "task": "caption",
            "max_new_tokens": 128,
            "num_beams": 1,
            **settings,
        }
        validated[name] = CaptionConfig(
            active_model=name, device=config.get("device", "auto"),
            precision=config.get("precision", "float32"), seed=config.get("seed", 42),
            **values,
        )
    return validated[active]


def load_config(path: Path, model: str | None = None) -> CaptionConfig:
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    return validate_config(config, model)


@dataclass(frozen=True)
class PlannerConfig:
    """Local Ollama settings, independent of the existing VLM configuration."""

    model: str = "qwen2.5:3b"
    endpoint: str = "http://127.0.0.1:11434/api/chat"
    timeout: float = 180.0
    keep_alive: int = 0
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("planner model must be a nonempty string")
        if not isinstance(self.endpoint, str):
            raise ValueError("planner endpoint must be a string")
        parsed = urlparse(self.endpoint)
        if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
                or parsed.path != "/api/chat" or parsed.query or parsed.fragment
                or parsed.username or parsed.password):
            raise ValueError("planner endpoint must be a local http /api/chat URL")
        if type(self.timeout) not in (int, float) or not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("planner timeout must be a positive finite number")
        if type(self.keep_alive) is not int or self.keep_alive < 0:
            raise ValueError("keep_alive must be nonnegative seconds; use 0 to unload")
        options = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 1024}
        if not isinstance(self.options, dict):
            raise ValueError("planner options must be an object")
        options.update(self.options)
        for name, value in options.items():
            if name in ("seed", "num_ctx", "num_predict", "num_gpu", "top_k"):
                minimum = 0 if name in ("seed", "num_gpu") else 1
                if type(value) is not int or value < minimum:
                    raise ValueError(f"invalid planner option: {name}")
            elif name in ("temperature", "top_p", "repeat_penalty"):
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid planner option: {name}")
            else:
                raise ValueError(f"unknown planner option: {name}")
        object.__setattr__(self, "options", options)


def load_planner_config(path: Path) -> PlannerConfig:
    try:
        values = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("planner configuration must be an object")
        return PlannerConfig(**values)
    except (TypeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid planner configuration: {exc}") from exc


@dataclass(frozen=True)
class GroundingConfig:
    """Independent, batch-one Grounding DINO experiment settings."""

    model_id: str = "IDEA-Research/grounding-dino-tiny"
    revision: str = "a2bb814dd30d776dcf7e30523b00659f4f141c71"
    device: str = "cuda"
    cpu_fallback: bool = True
    box_threshold: float = 0.30
    text_threshold: float = 0.25
    seed: int = 42

    def __post_init__(self) -> None:
        if self.model_id != "IDEA-Research/grounding-dino-tiny":
            raise ValueError("this milestone supports only Grounding DINO Tiny")
        if not isinstance(self.revision, str) or len(self.revision) != 40 or any(
            ch not in "0123456789abcdef" for ch in self.revision
        ):
            raise ValueError("grounding revision must be a pinned 40-character commit")
        if self.device not in ("cuda", "cpu") or type(self.cpu_fallback) is not bool:
            raise ValueError("grounding requires cuda/cpu and a boolean cpu_fallback")
        for name in ("box_threshold", "text_threshold"):
            value = getattr(self, name)
            if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and between 0 and 1")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("grounding seed must be an integer in [0, 2**32)")


def load_grounding_config(path: Path) -> GroundingConfig:
    try:
        values = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("grounding configuration must be an object")
        return GroundingConfig(**values)
    except (TypeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid grounding configuration: {exc}") from exc


@dataclass(frozen=True)
class SamConfig:
    model_id: str = "facebook/sam-vit-base"
    revision: str = "70c1a07f894ebb5b307fd9eaaee97b9dfc16068f"
    device: str = "cuda"
    cpu_fallback: bool = True
    precision: str = "float32"
    seed: int = 42
    multimask_output: bool = True
    mask_threshold: float = 0.0

    def __post_init__(self) -> None:
        if self.model_id != "facebook/sam-vit-base" or self.precision != "float32":
            raise ValueError("this milestone uses SAM ViT Base in float32")
        if not isinstance(self.revision, str) or len(self.revision) != 40 or any(c not in "0123456789abcdef" for c in self.revision):
            raise ValueError("SAM revision must be a pinned commit")
        if self.device not in ("cpu", "cuda") or type(self.cpu_fallback) is not bool:
            raise ValueError("SAM requires cpu/cuda and a boolean fallback setting")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("SAM seed must be an integer in [0, 2**32)")
        if (self.multimask_output is not True or type(self.mask_threshold) not in (int, float)
                or self.mask_threshold != 0.0):
            raise ValueError("retain all SAM candidates using the initial zero-logit mask threshold")


def load_sam_config(path: Path) -> SamConfig:
    try:
        values = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("SAM configuration must be an object")
        return SamConfig(**values)
    except (TypeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid SAM configuration: {exc}") from exc


@dataclass(frozen=True)
class InpaintingConfig:
    model_id: str = "stable-diffusion-v1-5/stable-diffusion-inpainting"
    revision: str = "8a4288a76071f7280aedbdb3253bdb9e9d5d84bb"
    processing_size: int = 512
    context_margin: int = 64
    seed: int = 42
    steps: int = 20
    guidance_scale: float = 7.5
    strength: float = 0.9

    def __post_init__(self) -> None:
        if self.model_id != "stable-diffusion-v1-5/stable-diffusion-inpainting":
            raise ValueError("this milestone uses the dedicated SD 1.5 inpainting checkpoint")
        if not isinstance(self.revision, str) or len(self.revision) != 40 or any(c not in "0123456789abcdef" for c in self.revision):
            raise ValueError("inpainting requires a pinned checkpoint commit")
        if type(self.processing_size) is not int or self.processing_size != 512:
            raise ValueError("this experiment uses a 512-pixel processing square")
        if type(self.context_margin) is not int or self.context_margin < 0:
            raise ValueError("context margin must be a nonnegative integer")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be an integer in [0, 2**32)")
        if type(self.steps) is not int or self.steps <= 0:
            raise ValueError("steps must be a positive integer")
        for name in ("guidance_scale", "strength"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.guidance_scale < 0 or not 0 < self.strength <= 1:
            raise ValueError("invalid guidance or strength")


def load_inpainting_config(path: Path) -> InpaintingConfig:
    try:
        values = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("inpainting configuration must be an object")
        return InpaintingConfig(**values)
    except (TypeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid inpainting configuration: {exc}") from exc
