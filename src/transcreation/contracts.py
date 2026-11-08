"""Single-image captioning interface and serializable result."""
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from PIL import Image

@dataclass(frozen=True)
class CaptionResult:
    caption: str
    model_id: str
    resolved_revision: str | None = None
    requested_revision: str | None = None
    image_dimensions: tuple[int, int] | None = None
    seed: int = 42
    task: str = "caption"
    generation_settings: dict[str, Any] = field(default_factory=dict)
    device: str = "cpu"
    precision: str = "float32"
    torch_version: str | None = None
    transformers_version: str | None = None
    model_loading_ms: float | None = None
    inference_ms: float | None = None
    peak_gpu_memory_bytes: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.caption, str) or not self.caption.strip():
            raise ValueError("Model generated an empty caption")
        if not self.model_id.strip():
            raise ValueError("model_id must be nonempty")


@dataclass(frozen=True)
class CaptionTaskResult(CaptionResult):
    """Measured task result; the existing single-caption schema stays unchanged."""

    generated_tokens: int = 0


@runtime_checkable
class Captioner(Protocol):
    def caption(self, image: Image.Image) -> CaptionResult:
        ...
