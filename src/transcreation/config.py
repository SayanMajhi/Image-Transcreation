"""Read models.yaml and check the captioning settings."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

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
