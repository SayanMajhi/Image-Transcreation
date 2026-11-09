"""Prepare the captioning model and run the implemented pipeline stage."""
from dataclasses import replace
from typing import Any, Mapping
import warnings

from PIL import Image

from transcreation.config import CaptionConfig, validate_config
from transcreation.contracts import Captioner, CaptionResult


def run_caption(image: Image.Image, config: CaptionConfig) -> CaptionResult:
    """Run captioning; the cultural planner is invoked separately."""
    return create_captioner(config).caption(image)


def create_captioner(config: CaptionConfig | Mapping[str, Any]) -> Captioner:
    if not isinstance(config, CaptionConfig):
        config = validate_config(config)
    import torch

    device = config.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    elif device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable; set device: cpu or auto")
    precision = config.precision
    if device == "cpu" and precision == "float16":
        warnings.warn("CPU captioning uses float32 instead of float16", RuntimeWarning)
        precision = "float32"
    resolved = replace(config, device=device, precision=precision)
    from transcreation.stages.caption import SmolVLMCaptioner
    return SmolVLMCaptioner(resolved)
