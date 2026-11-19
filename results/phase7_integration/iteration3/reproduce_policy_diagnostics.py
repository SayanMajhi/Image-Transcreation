"""Offline synthetic validator diagnostics, not an LLM run or image verification.

Run from the repository root with src on PYTHONPATH. Writes only the specified
new output file; never changes application code or research inputs.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

from transcreation.contracts import CaptionStatus, PlanningInput, VerifiedObject
from transcreation.stages.planning import parse_model_draft, validate_planning_result


def evaluate():
    request = PlanningInput("The synthetic caption reports a synthetic bowl on a surface.",
        CaptionStatus.COMPLETE, "synthetic target context", verified_objects=(VerifiedObject("test-object-1", "synthetic bowl"),))
    raw = {"decision": "PROPOSE", "decision_reason": "Synthetic policy diagnostic only.",
        "scene_summary": "The synthetic caption reports a synthetic bowl on a surface.",
        "candidate_edits": [{"object_description": "synthetic bowl", "localization_phrase": "synthetic bowl",
            "proposed_change": "a different surface finish", "cultural_reason": "Synthetic non-cultural policy diagnostic.",
            "identity_uncertain": False, "verified_object_id": "test-object-1"}],
        "must_preserve": ["background"], "uncertainties": [], "verification_requirements": []}
    cases = []

    def add(name, supplied=request, change=None):
        payload = deepcopy(raw)
        if change:
            change(payload)
        draft, initial = parse_model_draft(payload)
        final, issues = validate_planning_result(supplied, draft, initial)
        cases.append({"case": name, "scope": "SYNTHETIC_POLICY_DIAGNOSTIC_NOT_IMAGE_VERIFICATION",
            "input": asdict(supplied), "synthetic_raw_draft": payload, "final_result": asdict(final),
            "issues": issues, "issue_codes": [issue["code"] for issue in issues],
            "llm_calls": 0, "verified_real_objects": 0})

    add("complete_verified_no_instructions")
    add("same_candidate_with_satisfied_preservation_instruction",
        replace(request, user_instructions="Keep the background unchanged."))
    add("same_candidate_with_general_non_preservation_instruction",
        replace(request, user_instructions="Consider the supplied target context."))
    add("missing_verified_identity", replace(request, verified_objects=()),
        lambda v: v["candidate_edits"][0].update(verified_object_id=None))
    add("unknown_verified_identity", change=lambda v: v["candidate_edits"][0].update(verified_object_id="missing-id"))
    add("description_case_difference", change=lambda v: v["candidate_edits"][0].update(
        object_description="Synthetic bowl", localization_phrase="Synthetic bowl"))
    add("replacement_used_for_localization", change=lambda v: v["candidate_edits"][0].update(
        localization_phrase="a different surface finish"))
    add("preserve_position_mentions_source_label", change=lambda v: v.update(must_preserve=["position of the synthetic bowl"]))
    add("source_identity_uncertain", change=lambda v: v["candidate_edits"][0].update(identity_uncertain=True))
    add("truncated_caption", replace(request, caption_status=CaptionStatus.TRUNCATED))
    add("minor_unrelated_uncertainty_with_edit", change=lambda v: v.update(uncertainties=["Uncertain background wall color."]))
    add("source_and_replacement_identical", change=lambda v: v["candidate_edits"][0].update(proposed_change="synthetic bowl"))
    add("future_scene_summary", change=lambda v: v.update(scene_summary="The scene shows a different surface finish."))
    add("model_review", change=lambda v: v.update(decision="REVIEW"))
    return {"scope": "SYNTHETIC_POLICY_DIAGNOSTIC_NOT_IMAGE_VERIFICATION", "cases": cases,
            "model_calls": 0, "policy_modified": False,
            "interpretation": "This isolates validator behavior; no case establishes real planning quality or cultural correctness."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf8") as output:
        json.dump(evaluate(), output, indent=2, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()
