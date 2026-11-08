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
