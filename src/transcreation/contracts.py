"""Typed captioning and cultural-planning interfaces and results."""
from dataclasses import dataclass, field
from enum import StrEnum
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


class CaptionStatus(StrEnum):
    COMPLETE = "COMPLETE"
    TRUNCATED = "TRUNCATED"
    UNKNOWN = "UNKNOWN"


class PlanningDecision(StrEnum):
    PROPOSE = "PROPOSE"
    REVIEW = "REVIEW"
    ABSTAIN = "ABSTAIN"


def _require_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _require_text_tuple(value: object, name: str) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a tuple of nonempty strings")
    for item in value:
        _require_text(item, name)


class PlanningContractError(ValueError):
    """Machine-readable failure for an individual planning field."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _require_object_text(value: str, name: str) -> None:
    _require_text(value, name)
    if value.strip().casefold() in {"null", "none", "n/a", "na", "undefined"}:
        raise PlanningContractError("PLACEHOLDER_OBJECT_FIELD", f"{name} cannot be a placeholder")


def validate_localization_phrase(value: str) -> None:
    """A bounded object phrase; brevity alone does not prove correct grounding."""
    _require_object_text(value, "localization_phrase")
    if len(value.split()) > 16 or len(value) > 160:
        raise PlanningContractError("LOCALIZATION_NOT_OBJECT_PHRASE",
                                    "localization_phrase must be a short source-object phrase (at most 16 words / 160 characters)")


@dataclass(frozen=True)
class VerifiedObject:
    """Information supplied by a user who checked the image, never by a model."""

    object_id: str
    description: str

    def __post_init__(self) -> None:
        _require_object_text(self.object_id, "object_id")
        _require_object_text(self.description, "description")


@dataclass(frozen=True)
class PlanningInput:
    """The caption is an unverified model claim; cultures are user declarations."""

    source_caption: str
    caption_status: CaptionStatus
    target_culture: str
    source_culture: str | None = None
    user_instructions: str | None = None
    verified_objects: tuple[VerifiedObject, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.source_caption, "source_caption")
        _require_text(self.target_culture, "target_culture")
        if not isinstance(self.caption_status, CaptionStatus):
            raise ValueError("caption_status must be a CaptionStatus")
        for name in ("source_culture", "user_instructions"):
            value = getattr(self, name)
            if value is not None:
                _require_text(value, name)
        if not isinstance(self.verified_objects, tuple) or any(
            not isinstance(item, VerifiedObject) for item in self.verified_objects
        ):
            raise ValueError("verified_objects must be a tuple of VerifiedObject values")
        ids = [item.object_id for item in self.verified_objects]
        if len(set(ids)) != len(ids):
            raise ValueError("verified object ids must be unique")

    @classmethod
    def from_caption(cls, caption: CaptionResult, target_culture: str, *,
                     source_culture: str | None = None,
                     user_instructions: str | None = None,
                     verified_objects: tuple[VerifiedObject, ...] = ()) -> "PlanningInput":
        """Reuse existing results without requiring the SmolVLM module or torch."""
        if not isinstance(caption, CaptionResult):
            raise ValueError("caption must be a CaptionResult")
        if getattr(caption, "eos_reached", None) is True:
            status = CaptionStatus.COMPLETE
        elif getattr(caption, "token_ceiling_reached", None) is True:
            status = CaptionStatus.TRUNCATED
        else:
            status = CaptionStatus.UNKNOWN
        return cls(caption.caption, status, target_culture, source_culture,
                   user_instructions, verified_objects)


@dataclass(frozen=True)
class CandidateEdit:
    """A draft edit, never proof of identity or cultural suitability.

    object_description names the original object. localization_phrase locates that
    same original object and must retain its label. Only proposed_change describes
    the intended replacement/modification; none of these fields confirms visibility.
    """

    object_description: str
    localization_phrase: str
    proposed_change: str
    cultural_reason: str
    identity_uncertain: bool
    verified_object_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("object_description", "localization_phrase", "proposed_change", "cultural_reason"):
            _require_object_text(getattr(self, name), name)
        validate_localization_phrase(self.localization_phrase)
        if type(self.identity_uncertain) is not bool:
            raise ValueError("identity_uncertain must be a boolean")
        if self.verified_object_id is not None:
            try:
                _require_object_text(self.verified_object_id, "verified_object_id")
            except ValueError as exc:
                raise PlanningContractError("INVALID_VERIFIED_OBJECT_ID",
                                            "verified_object_id must be a real id or actual JSON null") from exc


@dataclass(frozen=True)
class PlanningResult:
    """PROPOSE is a draft; ABSTAIN permits no change, never an image edit.

    scene_summary describes only the original, unedited scene, attributing uncertain
    caption claims rather than confirming them. must_preserve lists unchanged
    elements/features and relationships, not the identity of an object being replaced.
    uncertainties lists unresolved facts material to this planning decision.
    verification_requirements lists specific checks before any edit is permitted.
    Generated prose remains unverified, even when its structure is valid.
    This type can also hold raw drafts. Final policy results release no candidates
    for REVIEW or ABSTAIN; raw proposals remain in the separate audit record.
    """

    decision: PlanningDecision
    decision_reason: str
    scene_summary: str
    candidate_edits: tuple[CandidateEdit, ...]
    must_preserve: tuple[str, ...]
    uncertainties: tuple[str, ...]
    verification_requirements: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.decision, PlanningDecision):
            raise ValueError("decision must be a PlanningDecision")
        _require_text(self.decision_reason, "decision_reason")
        _require_text(self.scene_summary, "scene_summary")
        if not isinstance(self.candidate_edits, tuple) or any(
            not isinstance(item, CandidateEdit) for item in self.candidate_edits
        ):
            raise ValueError("candidate_edits must be a tuple of CandidateEdit values")
        for name in ("must_preserve", "uncertainties", "verification_requirements"):
            _require_text_tuple(getattr(self, name), name)
        if self.decision == PlanningDecision.PROPOSE and not self.candidate_edits:
            raise ValueError("PROPOSE requires at least one candidate edit")
        if self.decision == PlanningDecision.ABSTAIN and self.candidate_edits:
            raise ValueError("ABSTAIN cannot contain candidate edits")
        if self.candidate_edits and not self.must_preserve:
            raise ValueError("candidate edits require features to preserve")


@runtime_checkable
class CulturalPlanner(Protocol):
    def plan(self, request: PlanningInput) -> PlanningResult:
        ...


@dataclass(frozen=True)
class GroundingDetection:
    """One model-returned source-image box; not approval to modify an object."""

    box: tuple[float, float, float, float]
    score: float
    label: str

    def validate(self, width: int, height: int) -> None:
        import math

        if width <= 0 or height <= 0:
            raise ValueError("image dimensions must be positive")
        if len(self.box) != 4 or any(type(v) not in (float, int) or not math.isfinite(v) for v in self.box):
            raise ValueError("box requires four finite coordinates")
        x0, y0, x1, y1 = self.box
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError("box must be ordered and within original-image boundaries")
        if type(self.score) not in (float, int) or not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be finite and within [0, 1]")
        if not isinstance(self.label, str):
            raise ValueError("returned label must be text")


@dataclass(frozen=True)
class GroundingResult:
    image_sha256: str
    original_dimensions: tuple[int, int]
    source_phrase: str
    model_id: str
    resolved_revision: str
    status: str
    detections: tuple[GroundingDetection, ...]
    settings: dict[str, Any]
    timing: dict[str, Any]
    memory: dict[str, Any]
    raw_predictions: dict[str, Any]
    observations: tuple[dict[str, Any], ...] = ()
    research_only: bool = True

    def __post_init__(self) -> None:
        if self.status not in ("DETECTED", "NO_DETECTIONS", "INVALID_OUTPUT", "ERROR"):
            raise ValueError("invalid detection status")
        if len(self.original_dimensions) != 2 or any(type(v) is not int or v <= 0 for v in self.original_dimensions):
            raise ValueError("original dimensions must be positive integer width and height")
        for item in self.detections:
            item.validate(*self.original_dimensions)
        if (self.status == "DETECTED" and not self.detections) or (
            self.status in ("NO_DETECTIONS", "ERROR") and self.detections
        ):
            raise ValueError("detection status and boxes disagree")


@dataclass(frozen=True)
class SamPoint:
    x: float
    y: float
    label: int
    note: str = ""

    def __post_init__(self) -> None:
        import math

        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (self.x, self.y)):
            raise ValueError("SAM point coordinates must be finite numbers")
        if type(self.label) is not int or self.label not in (0, 1):
            raise ValueError("SAM point label must be integer 1 (foreground) or 0 (background)")
        if not isinstance(self.note, str):
            raise ValueError("point note must be text")


@dataclass(frozen=True)
class SegmentationInput:
    source_image: str
    image_sha256: str
    original_dimensions: tuple[int, int]
    detection_file: str
    detection_sha256: str
    prediction_index: int
    selected_detection: GroundingDetection
    source_phrase: str
    grounding_model_id: str
    grounding_revision: str
    selection_status: str
    selection_note: str
    review_file: str | None = None
    review_sha256: str | None = None
    image_edit_authorized: bool = False
    cultural_transformation_authorized: bool = False
    points: tuple[SamPoint, ...] = ()
    point_prompt_file: str | None = None
    point_prompt_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.image_edit_authorized is not False or self.cultural_transformation_authorized is not False:
            raise ValueError("segmentation research cannot authorize editing")
        if self.selection_status not in ("RESEARCH_ONLY", "REVIEWED_SELECTION"):
            raise ValueError("choose explicit research-only or validated reviewed selection")
        if type(self.prediction_index) is not int or self.prediction_index < 0:
            raise ValueError("segmentation requires an explicit zero-based index")
        if not isinstance(self.selection_note, str) or not self.selection_note.strip():
            raise ValueError("record why this source box is being tested")
        if self.selection_status == "REVIEWED_SELECTION" and (not self.review_file or not self.review_sha256):
            raise ValueError("reviewed selection requires bound review evidence")
        self.selected_detection.validate(*self.original_dimensions)
        if not isinstance(self.points, tuple) or any(not isinstance(point, SamPoint) for point in self.points):
            raise ValueError("points must be a tuple of SamPoint values")
        if self.point_prompt_file is not None:
            if self.selection_status != "RESEARCH_ONLY" or not self.point_prompt_sha256:
                raise ValueError("new point annotations require explicit research-only provenance")
        elif self.points or self.point_prompt_sha256:
            raise ValueError("point annotations require a bound source file/hash")
        width, height = self.original_dimensions
        if any(not (0 <= point.x < width and 0 <= point.y < height) for point in self.points):
            raise ValueError("point coordinates must lie inside the original image")


@dataclass(frozen=True)
class SegmentationMask:
    index: int
    filename: str
    dimensions: tuple[int, int]
    sam_score: float
    foreground_pixels: int
    mask_box: tuple[int, int, int, int] | None
    status: str

    def __post_init__(self) -> None:
        import math

        if type(self.index) is not int or self.index < 0 or not self.filename:
            raise ValueError("mask requires an index and filename")
        if len(self.dimensions) != 2 or any(type(v) is not int or v <= 0 for v in self.dimensions):
            raise ValueError("mask dimensions must be positive integer width and height")
        if type(self.sam_score) not in (int, float) or not math.isfinite(self.sam_score):
            raise ValueError("SAM score must be finite; it is not measured accuracy")
        width, height = self.dimensions
        if type(self.foreground_pixels) is not int or not 0 <= self.foreground_pixels <= width * height:
            raise ValueError("invalid foreground pixel count")
        if self.status not in ("VALID", "REJECTED_EMPTY"):
            raise ValueError("unknown mask status")
        if self.status == "REJECTED_EMPTY":
            if self.foreground_pixels != 0 or self.mask_box is not None:
                raise ValueError("empty rejected mask cannot have foreground bounds")
        else:
            if not self.foreground_pixels or self.mask_box is None:
                raise ValueError("valid mask cannot be empty")
            GroundingDetection(self.mask_box, 0.0, "mask extent").validate(width, height)


@dataclass(frozen=True)
class SegmentationResult:
    request: SegmentationInput
    model_id: str
    resolved_revision: str | None
    status: str
    masks: tuple[SegmentationMask, ...]
    visualization_mask_index: int | None
    settings: dict[str, Any]
    timing: dict[str, Any]
    memory: dict[str, Any]
    observations: tuple[dict[str, Any], ...]
    image_edit_authorized: bool = False
    cultural_transformation_authorized: bool = False

    def __post_init__(self) -> None:
        if self.status not in ("SEGMENTED", "PARTIAL_INVALID", "INVALID_OUTPUT", "ERROR"):
            raise ValueError("unknown segmentation status")
        if self.image_edit_authorized is not False or self.cultural_transformation_authorized is not False:
            raise ValueError("segmentation results never authorize editing")
        valid = [mask.index for mask in self.masks if mask.status == "VALID"]
        if self.visualization_mask_index is not None and self.visualization_mask_index not in valid:
            raise ValueError("visualization must reference a nonempty saved mask")
        if self.status == "SEGMENTED" and (not self.masks or len(valid) != len(self.masks)):
            raise ValueError("segmented status requires valid masks")


@dataclass(frozen=True)
class InpaintingInput:
    source_image: str
    image_sha256: str
    segmentation_file: str
    segmentation_sha256: str
    mask_file: str
    mask_sha256: str
    candidate_index: int
    prompt: str
    selection_note: str
    scope: str  # explicit user-directed isolated research, never inferred from a review or plan
    mask_kind: str = "SAM_CANDIDATE"

    def __post_init__(self) -> None:
        if self.scope != "RESEARCH_ONLY":
            raise ValueError("only explicit isolated RESEARCH_ONLY generation is supported")
        for name in ("source_image", "segmentation_file", "mask_file", "prompt", "selection_note"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or value.strip().lower() in ("null", "none", "n/a"):
                raise ValueError(f"{name} must be meaningful text")
        for name in ("image_sha256", "segmentation_sha256", "mask_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be a SHA-256")
        if type(self.candidate_index) is not int or self.candidate_index < 0:
            raise ValueError("select one explicit integer SAM candidate index")
        if self.mask_kind not in ("SAM_CANDIDATE", "COMBINED"):
            raise ValueError("mask_kind must be SAM_CANDIDATE or COMBINED")
