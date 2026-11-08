"""General decision-policy regressions; no culture-specific substitutions or LLM."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from transcreation.contracts import (
    CandidateEdit, CaptionStatus, PlanningInput, VerifiedObject,
)
from transcreation.stages.planning import parse_model_draft, validate_planning_result


def source_request(**changes):
    return PlanningInput(**{
        "source_caption": "A red ceramic cup sits on a table.",
        "caption_status": CaptionStatus.COMPLETE,
        "target_culture": "requested context",
        "verified_objects": (VerifiedObject("cup-1", "red ceramic cup"),),
        **changes,
    })


def proposal():
    return {
        "decision": "PROPOSE", "decision_reason": "A contextual presentation option for the requested setting.",
        "scene_summary": "The caption reports a red ceramic cup on a table.",
        "candidate_edits": [{
            "object_description": "red ceramic cup", "localization_phrase": "red ceramic cup on the table",
            "proposed_change": "blue ceramic cup", "cultural_reason": "A contextual preference, not a universal rule.",
            "identity_uncertain": False, "verified_object_id": "cup-1",
        }],
        "must_preserve": ["table", "cup position"], "uncertainties": [], "verification_requirements": [],
    }


def evaluate(payload, request=None):
    draft, issues = parse_model_draft(payload)
    return validate_planning_result(request or source_request(), draft, issues)


class TestDecisionPolicy(unittest.TestCase):
    def test_source_membership_does_not_validate_abstention_for_an_adaptation_request(self):
        payload = proposal()
        payload.update(decision="ABSTAIN", candidate_edits=[], decision_reason="The object already belongs to the source culture.")
        before = deepcopy(payload)
        result, issues = evaluate(payload, source_request(
            source_culture="original context", user_instructions="Consider adaptation; retain the activity.",
        ))
        self.assertEqual(result.decision, "REVIEW")
        self.assertIn("ABSTENTION_CONTEXT_UNVERIFIED", {item["code"] for item in issues})
        self.assertEqual(result.candidate_edits, ())
        self.assertEqual(payload, before)

    def test_placeholder_descriptions_are_rejected_and_quarantined(self):
        for value in ("", "null", "NULL", "none", "N/A", "undefined"):
            with self.subTest(value=value):
                payload = proposal()
                payload["candidate_edits"][0]["object_description"] = value
                with self.assertRaises(ValueError):
                    CandidateEdit(**payload["candidate_edits"][0])
                final, issues = evaluate(payload)
                self.assertEqual(final.decision, "REVIEW")
                self.assertFalse(final.candidate_edits)
                self.assertTrue(issues)

    def test_full_scene_localization_is_not_an_object_phrase(self):
        payload = proposal()
        payload["candidate_edits"][0]["localization_phrase"] = (
            "The cup is on a table beside a door. Several people stand behind it, "
            "while buildings and trees cover the entire background."
        )
        final, issues = evaluate(payload)
        self.assertEqual(final.candidate_edits, ())
        self.assertIn("LOCALIZATION_NOT_OBJECT_PHRASE", {item["code"] for item in issues})

    def test_actual_null_is_nullable_but_not_a_verified_identity(self):
        payload = proposal()
        payload["candidate_edits"][0].update(verified_object_id=None, identity_uncertain=True)
        draft, parse_issues = parse_model_draft(payload)
        self.assertFalse(parse_issues)
        self.assertIsNone(draft.candidate_edits[0].verified_object_id)
        final, issues = validate_planning_result(source_request(), draft)
        self.assertEqual(final.decision, "REVIEW")
        self.assertEqual(final.candidate_edits, ())
        self.assertIn("UNVERIFIED_SOURCE_OBJECT", {item["code"] for item in issues})

    def test_string_null_id_is_invalid(self):
        payload = proposal()
        payload["candidate_edits"][0]["verified_object_id"] = "null"
        final, issues = evaluate(payload)
        self.assertFalse(final.candidate_edits)
        self.assertIn("INVALID_VERIFIED_OBJECT_ID", {item["code"] for item in issues})

    def test_unknown_verified_id_is_removed(self):
        payload = proposal()
        payload["candidate_edits"][0]["verified_object_id"] = "invented"
        final, issues = evaluate(payload)
        self.assertEqual(final.decision, "REVIEW")
        self.assertFalse(final.candidate_edits)
        self.assertIn("UNKNOWN_VERIFIED_OBJECT_ID", {item["code"] for item in issues})

    def test_user_protected_content_cannot_silently_be_edited(self):
        final, issues = evaluate(proposal(), source_request(user_instructions="Protect the family cup and its role in this practice."))
        self.assertFalse(final.candidate_edits)
        self.assertEqual(final.decision, "REVIEW")
        self.assertIn("USER_CONSTRAINTS_UNRESOLVED", {item["code"] for item in issues})

    def test_unresolved_protection_paraphrase_is_not_claimed_compatible(self):
        final, issues = evaluate(proposal(), source_request(user_instructions="The user's treasured symbol and shared purpose must remain."))
        self.assertFalse(final.candidate_edits)
        self.assertTrue(any("cannot prove compatibility" in item["message"] for item in issues))

    def test_preserved_source_object_cannot_be_released_for_replacement(self):
        payload = proposal()
        payload["must_preserve"] = ["red ceramic cup"]
        final, issues = evaluate(payload)
        self.assertEqual(final.candidate_edits, ())
        self.assertIn("PRESERVATION_CONFLICT", {item["code"] for item in issues})

    def test_truncated_caption_cannot_release_even_verified_candidates(self):
        final, issues = evaluate(proposal(), source_request(caption_status=CaptionStatus.TRUNCATED))
        self.assertEqual(final.decision, "REVIEW")
        self.assertFalse(final.candidate_edits)
        self.assertIn("CAPTION_INCOMPLETE", {item["code"] for item in issues})

    def test_verified_edit_with_correct_source_localization_stays_a_draft(self):
        final, issues = evaluate(proposal())
        self.assertEqual(final.decision, "PROPOSE")
        self.assertEqual(len(final.candidate_edits), 1)
        self.assertFalse(issues)
        self.assertTrue(any("not approval" in check for check in final.verification_requirements))

    def test_review_is_nonactionable_even_if_its_candidate_is_well_formed(self):
        payload = proposal()
        payload["decision"] = "REVIEW"
        final, issues = evaluate(payload)
        self.assertFalse(final.candidate_edits)
        self.assertIn("MODEL_REVIEW_ONLY", {item["code"] for item in issues})

    def test_abstention_clears_unrelated_checks_without_claiming_cultural_correctness(self):
        payload = proposal()
        payload.update(decision="ABSTAIN", candidate_edits=[],
                       decision_reason="This ordinary object is culturally unacceptable.",
                       verification_requirements=["Check an invented national restriction."])
        before = deepcopy(payload)
        final, issues = evaluate(payload)
        self.assertEqual(final.decision, "ABSTAIN")
        self.assertEqual(final.candidate_edits, ())
        self.assertEqual(final.verification_requirements, ())
        self.assertNotIn("unacceptable", final.decision_reason)
        self.assertEqual(payload, before)
        self.assertEqual(issues[0]["code"], "ABSTENTION_NORMALIZED")

    def test_source_and_replacement_must_be_distinct(self):
        payload = proposal()
        payload["candidate_edits"][0]["proposed_change"] = "RED ceramic cup."
        final, issues = evaluate(payload)
        self.assertFalse(final.candidate_edits)
        self.assertIn("SOURCE_REPLACEMENT_IDENTICAL", {item["code"] for item in issues})

    def test_explicit_no_edit_review_stays_nonactionable(self):
        payload = proposal()
        payload.update(decision="REVIEW", candidate_edits=[], verification_requirements=["Unrelated background style check."])
        final, issues = evaluate(payload)
        self.assertEqual(final.decision, "REVIEW")
        self.assertFalse(final.candidate_edits)
        self.assertIn("MODEL_REVIEW_REQUESTED", {item["code"] for item in issues})

    def test_empty_proposal_resolves_only_to_no_action_with_an_explicit_code(self):
        payload = proposal()
        payload["candidate_edits"] = []
        final, issues = evaluate(payload)
        self.assertEqual(final.decision, "ABSTAIN")
        self.assertFalse(final.candidate_edits)
        self.assertEqual(final.verification_requirements, ())
        self.assertIn("PROPOSE_WITHOUT_EDITS", {item["code"] for item in issues})

    def test_empty_proposal_with_incomplete_caption_remains_review(self):
        payload = proposal()
        payload["candidate_edits"] = []
        final, issues = evaluate(payload, source_request(caption_status=CaptionStatus.TRUNCATED))
        self.assertEqual(final.decision, "REVIEW")
        self.assertFalse(final.candidate_edits)
        self.assertIn("CAPTION_INCOMPLETE", {item["code"] for item in issues})

    def test_one_invalid_candidate_does_not_release_the_rest_of_a_review_batch(self):
        payload = proposal()
        payload["candidate_edits"].append({**payload["candidate_edits"][0], "object_description": "null"})
        final, issues = evaluate(payload)
        self.assertEqual(final.decision, "REVIEW")
        self.assertFalse(final.candidate_edits)
        self.assertEqual(issues[0]["candidate_index"], 1)


if __name__ == "__main__":
    unittest.main()
