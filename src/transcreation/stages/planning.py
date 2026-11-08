"""Validate cultural plans and apply review rules independently of model adapters."""
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, TypedDict
import re

from transcreation.contracts import (
    CandidateEdit, CaptionStatus, CulturalPlanner, PlanningDecision,
    PlanningInput, PlanningResult,
    validate_localization_phrase,
)


def parse_planning_result(payload: Mapping[str, object]) -> PlanningResult:
    """Parse a JSON-shaped response. Reject missing, extra, and malformed fields."""
    if not isinstance(payload, Mapping):
        raise ValueError("planner response must be an object")
    values: dict[str, Any] = dict(payload)
    try:
        edits = values["candidate_edits"]
        if not isinstance(edits, list) or any(not isinstance(edit, Mapping) for edit in edits):
            raise ValueError("candidate_edits must be a list of objects")
        values["candidate_edits"] = tuple(CandidateEdit(**edit) for edit in edits)
        for name in ("must_preserve", "uncertainties", "verification_requirements"):
            if not isinstance(values[name], list):
                raise ValueError(f"{name} must be a list of nonempty strings")
            values[name] = tuple(values[name])
        values["decision"] = PlanningDecision(values["decision"])
        return PlanningResult(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed planner response: {exc}") from exc


def _contains_label(text: str, label: str) -> bool:
    """Match an explicit label, ignoring case/punctuation, without guessing synonyms."""
    words = tuple(re.findall(r"\w+", text.casefold()))
    reference = tuple(re.findall(r"\w+", label.casefold()))
    return bool(reference) and any(
        words[start:start + len(reference)] == reference
        for start in range(len(words) - len(reference) + 1)
    )


def edit_consistency_issues(request: PlanningInput, result: PlanningResult) -> tuple[str, ...]:
    """Compatibility diagnostic using the same policy as final validation."""
    _, issues = validate_planning_result(request, result)
    return tuple(issue["message"] for issue in issues if issue["candidate_index"] is not None)


class ValidationIssue(TypedDict):
    code: str
    message: str
    candidate_index: int | None
    severity: str


def _issue(code: str, message: str, index: int | None = None,
           severity: str = "review") -> ValidationIssue:
    return {"code": code, "message": message, "candidate_index": index, "severity": severity}


def parse_model_draft(payload: Mapping[str, object]) -> tuple[PlanningResult, list[ValidationIssue]]:
    """Quarantine bad candidates; still reject malformed JSON/top-level contracts.

    The caller retains the untouched raw payload. Bad candidates become REVIEW;
    an empty PROPOSE can only become coded no-action ABSTAIN, never an invented edit.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("planner response must be an object")
    edits = payload.get("candidate_edits")
    if not isinstance(edits, list):
        raise ValueError("candidate_edits must be a list")
    accepted = []
    issues: list[ValidationIssue] = []
    for index, edit in enumerate(edits):
        try:
            if not isinstance(edit, Mapping):
                raise ValueError("candidate edit must be an object")
            CandidateEdit(**edit)
            accepted.append(dict(edit))
        except (TypeError, ValueError) as exc:
            issues.append(_issue(getattr(exc, "code", "CANDIDATE_SCHEMA_INVALID"), str(exc), index))
            # Keep the independent locality failure visible even when another
            # field (for example a placeholder description) failed first.
            if isinstance(edit, Mapping) and isinstance(edit.get("localization_phrase"), str):
                try:
                    validate_localization_phrase(edit["localization_phrase"])
                except ValueError as phrase_error:
                    code = getattr(phrase_error, "code", "CANDIDATE_SCHEMA_INVALID")
                    if code != getattr(exc, "code", "CANDIDATE_SCHEMA_INVALID"):
                        issues.append(_issue(code, str(phrase_error), index))
    values = dict(payload)
    values["candidate_edits"] = accepted
    if payload.get("decision") == PlanningDecision.ABSTAIN and edits:
        issues.append(_issue("ABSTAIN_WITH_EDITS", "An abstention cannot contain proposed edits."))
    if payload.get("decision") == PlanningDecision.PROPOSE and not edits:
        issues.append(_issue("PROPOSE_WITHOUT_EDITS", "The raw decision proposed no edit; resolve only to a no-action disposition, never invent a candidate.", severity="info"))
        values["decision"] = PlanningDecision.ABSTAIN
    if any(issue["severity"] == "review" for issue in issues):
        # Validate the other top-level fields first; never repair an invalid enum
        # or a missing reason/summary by inventing one.
        PlanningDecision(payload["decision"])
        issues.append(_issue("BATCH_REVIEW_REQUIRED", "The raw candidate batch failed validation; no candidate is released until reviewed."))
        values["decision"] = PlanningDecision.REVIEW
        values["candidate_edits"] = []
    draft = parse_planning_result(values)
    return draft, issues


def validate_planning_result(
    request: PlanningInput, result: PlanningResult,
    initial_issues: list[ValidationIssue] | None = None,
) -> tuple[PlanningResult, list[ValidationIssue]]:
    """Return a final plan and codes. REVIEW contains no downstream candidates."""
    if not isinstance(request, PlanningInput) or not isinstance(result, PlanningResult):
        raise ValueError("expected typed planning input and result")
    issues = list(initial_issues or [])
    if request.caption_status != CaptionStatus.COMPLETE:
        issues.append(_issue("CAPTION_INCOMPLETE", "Verify the complete source caption and image before planning an edit."))
    verified = {item.object_id: item.description for item in request.verified_objects}
    source_text = "\n".join((request.source_caption, *verified.values()))
    for index, edit in enumerate(result.candidate_edits):
        if edit.verified_object_id is None:
            issues.append(_issue("UNVERIFIED_SOURCE_OBJECT", f"Verify the source-object identity of: {edit.object_description}.", index))
        elif edit.verified_object_id not in verified:
            issues.append(_issue("UNKNOWN_VERIFIED_OBJECT_ID", "The verified source-object identity id does not exist in the supplied input.", index))
        elif verified[edit.verified_object_id] != edit.object_description:
            issues.append(_issue("SOURCE_OBJECT_MISMATCH", "The source-object identity does not match the user-verified description.", index))
        if edit.identity_uncertain:
            issues.append(_issue("SOURCE_IDENTITY_UNCERTAIN", "Resolve the source-object identity before an edit.", index))
        if not _contains_label(edit.localization_phrase, edit.object_description):
            issues.append(_issue("SOURCE_LOCALIZATION_MISMATCH", f"Localization must retain the original object label: {edit.object_description}.", index))
        if _normalized_label(edit.object_description) == _normalized_label(edit.proposed_change):
            issues.append(_issue("SOURCE_REPLACEMENT_IDENTICAL", "The proposed replacement/modification is indistinguishable from the original object.", index))
        if (not _contains_label(source_text, edit.proposed_change)
                and _contains_label(result.scene_summary, edit.proposed_change)):
            issues.append(_issue("FUTURE_SCENE_CONTAMINATION", "Scene summary contains an intended-change phrase absent from source evidence.", index))
        if any(_contains_label(item, edit.object_description) for item in result.must_preserve):
            issues.append(_issue("PRESERVATION_CONFLICT", f"Potential preserve/edit conflict involving: {edit.object_description}; distinguish identity from unchanged features.", index))
        if any(_contains_label(item, edit.proposed_change) for item in result.must_preserve):
            issues.append(_issue("PRESERVATION_CONFLICT", "A preservation statement names the intended change.", index))
    # User constraints are opaque prose in the existing contract. Even candidates
    # rejected before construction must not bypass this protection boundary.
    had_candidates = bool(result.candidate_edits) or any(
        issue["candidate_index"] is not None for issue in (initial_issues or [])
    )
    if request.user_instructions and had_candidates:
        issues.append(_issue("USER_CONSTRAINTS_UNRESOLVED", "Check all proposals against supplied user instructions/protected constraints; text validation cannot prove compatibility."))
    if result.uncertainties and result.candidate_edits:
        issues.append(_issue("EDIT_UNCERTAINTY_UNRESOLVED", "Resolve uncertainties material to the proposed edits; relevance is not automatically proven."))
    if result.decision == PlanningDecision.REVIEW and result.candidate_edits:
        issues.append(_issue("MODEL_REVIEW_ONLY", "The model requested review; its candidates are draft-only, not downstream edits."))
    elif result.decision == PlanningDecision.REVIEW and not initial_issues:
        issues.append(_issue("MODEL_REVIEW_REQUESTED", "The model requested context review; no direct edit is authorized."))
    if (not result.candidate_edits and request.source_culture
            and request.source_culture.casefold() != request.target_culture.casefold()
            and request.verified_objects and request.user_instructions):
        # This does NOT force a substitution or infer that two cultures require one.
        # It identifies an unassessed adaptation request, not a proven semantic error.
        issues.append(_issue("ABSTENTION_CONTEXT_UNVERIFIED", "Review the target-context justification: an object's source-culture membership alone neither requires nor rules out adaptation."))
    blocking = [issue for issue in issues if issue["severity"] == "review"]
    decision = PlanningDecision.REVIEW if blocking else result.decision
    if decision == PlanningDecision.REVIEW:
        requirements = tuple(dict.fromkeys((
            *(issue["message"] for issue in blocking),
            "Review the original-scene summary and any paraphrased identities against the image.",
            "Human review must check protected content and preservation; text checks cannot prove semantic correctness.",
        )))
        reason = "Review required; no candidate edit is released downstream. " + " ".join(
            dict.fromkeys(issue["message"] for issue in blocking)
        )
        return replace(result, decision=decision, decision_reason=reason,
                       candidate_edits=(), verification_requirements=requirements), issues
    if decision == PlanningDecision.ABSTAIN:
        issues.append(_issue("ABSTENTION_NORMALIZED", "No-edit reason and checks normalized; raw cultural claims/checks remain in the audit.", severity="info"))
        return replace(
            result, decision=decision, candidate_edits=(), verification_requirements=(),
            decision_reason="No justified image edit is established; leave the source image unchanged. This does not authorize modification or certify cultural appropriateness.",
        ), issues
    requirements = tuple(dict.fromkeys((*result.verification_requirements,
        "Check proposed changes and cultural reasons with the user; PROPOSE is not approval.",
        "Verify localization phrases against the original image before grounding or editing.",
        "Compare scene_summary with the original image; caption-only claims and paraphrased identities remain unverified.",
        "Check every preservation statement against the edit; text checks cannot prove semantic or cultural correctness.",
    )))
    return replace(result, verification_requirements=requirements, must_preserve=tuple(dict.fromkeys((
        *result.must_preserve, "original scene purpose", "important people", "activity", "person and object relationships",
    )))), issues


def _normalized_label(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\w+", value.casefold()))


def plan_cultural_edits(request: PlanningInput, planner: CulturalPlanner) -> PlanningResult:
    if not isinstance(request, PlanningInput):
        raise ValueError("request must be a PlanningInput")
    result, _ = validate_planning_result(request, planner.plan(request))
    return result


class MockPlanner:
    """Return caller-supplied fixture data for tests/examples; no cultural rules."""

    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response

    def plan(self, request: PlanningInput) -> PlanningResult:
        return parse_planning_result(self.response)
