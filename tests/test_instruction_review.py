"""Synthetic instruction-bearing drafts; no live model or genuine human approval."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from io import StringIO
import json
import unittest

from scripts.review_edit_intent import decide, main, verify
from transcreation.contracts import CaptionStatus, PlanningInput
from transcreation.orchestration import PipelineState
from transcreation.stages.planning import parse_model_draft, validate_planning_result


INSTRUCTIONS = "Keep the background unchanged.\nPreserve the camera angle; do not infer cultural suitability."


class InstructionReviewTests(unittest.TestCase):
    def setUp(self):
        from test_edit_intent import EditIntentTests
        self.flow = EditIntentTests()
        self.flow.setUp()
        self.addCleanup(self.flow.doCleanups)
        self.base = self.flow.fixture
        self.base.request = replace(self.base.request, user_instructions=INSTRUCTIONS)

    def validate(self, change=None, **context):
        payload = deepcopy(self.base.raw)
        if change:
            change(payload)
        request = PlanningInput.from_caption(self.base.caption, self.base.request.target_culture,
            user_instructions=self.base.request.user_instructions, verified_objects=self.base.request.verified_objects)
        request = replace(request, **context)
        draft, initial = parse_model_draft(payload)
        return validate_planning_result(request, draft, initial)

    def accepted(self, decision='ACCEPT_FOR_GROUNDING_TEST', checked=True):
        pending = self.flow.proposal()
        return decide(pending, pending.with_name('decision.json'), decision,
            'synthetic test reviewer', 'Synthetic check of the full instruction text; not actual human approval.',
            True, True, checked_user_instructions=checked)

    def blocked(self, change=None, **context):
        result, issues = self.validate(change, **context)
        self.assertEqual(result.decision, 'REVIEW')
        self.assertEqual(result.candidate_edits, ())
        return {issue['code'] for issue in issues}

    def test_valid_draft_without_instructions_still_requires_pending_review(self):
        self.base.request = replace(self.base.request, user_instructions=None)
        result, _ = self.validate()
        self.assertEqual(result.decision, 'PROPOSE')
        pending = verify(self.flow.proposal())
        self.assertEqual(pending['decision'], 'PENDING')
        self.assertEqual(pending['user_constraints_status'], 'NOT_APPLICABLE')
        self.assertFalse(pending['image_edit_authorized'])

    def test_instructions_allow_unapproved_draft_with_explicit_human_warning(self):
        result, issues = self.validate()
        self.assertEqual(result.decision, 'PROPOSE')
        self.assertEqual(len(result.candidate_edits), 1)
        warning = next(i for i in issues if i['code'] == 'USER_CONSTRAINTS_UNRESOLVED')
        self.assertEqual(warning['severity'], 'human_verification')
        self.assertIn(warning['message'], result.verification_requirements)
        record = verify(self.flow.proposal())
        self.assertEqual(record['user_instructions'], INSTRUCTIONS)
        self.assertEqual(record['user_constraints_status'], 'REQUIRES_HUMAN_VERIFICATION')
        self.assertEqual(record['decision'], 'PENDING')
        self.assertFalse(record['checked_user_instructions'])

    def test_missing_verified_identity_still_blocks(self):
        codes = self.blocked(lambda p:p['candidate_edits'][0].update(verified_object_id=None), verified_objects=())
        self.assertIn('UNVERIFIED_SOURCE_OBJECT', codes)

    def test_unknown_verified_id_still_blocks(self):
        self.assertIn('UNKNOWN_VERIFIED_OBJECT_ID', self.blocked(
            lambda p:p['candidate_edits'][0].update(verified_object_id='invented-id')))

    def test_original_description_mismatch_still_blocks(self):
        self.assertIn('SOURCE_OBJECT_MISMATCH', self.blocked(
            lambda p:p['candidate_edits'][0].update(object_description='different object')))

    def test_replacement_localization_still_blocks(self):
        self.assertIn('SOURCE_LOCALIZATION_MISMATCH', self.blocked(
            lambda p:p['candidate_edits'][0].update(localization_phrase='a different surface material')))

    def test_placeholder_candidate_still_quarantined(self):
        codes = self.blocked(lambda p:p['candidate_edits'][0].update(object_description='null'))
        self.assertTrue({'PLACEHOLDER_OBJECT_FIELD','BATCH_REVIEW_REQUIRED'} <= codes)

    def test_malformed_candidate_still_quarantined(self):
        self.assertIn('CANDIDATE_SCHEMA_INVALID', self.blocked(
            lambda p:p['candidate_edits'][0].update(unexpected_field='invalid')))

    def test_preservation_conflict_still_blocks(self):
        self.assertIn('PRESERVATION_CONFLICT', self.blocked(lambda p:p.update(must_preserve=['synthetic object'])))

    def test_uncertain_source_identity_still_blocks(self):
        self.assertIn('SOURCE_IDENTITY_UNCERTAIN', self.blocked(
            lambda p:p['candidate_edits'][0].update(identity_uncertain=True)))

    def test_truncated_caption_still_blocks(self):
        self.assertIn('CAPTION_INCOMPLETE', self.blocked(caption_status=CaptionStatus.TRUNCATED))

    def test_uncertainty_and_identical_replacement_still_block(self):
        self.assertIn('EDIT_UNCERTAINTY_UNRESOLVED', self.blocked(lambda p:p.update(uncertainties=['Unresolved object material.'])))
        self.assertIn('SOURCE_REPLACEMENT_IDENTICAL', self.blocked(
            lambda p:p['candidate_edits'][0].update(proposed_change='synthetic object')))

    def test_raw_review_is_never_promoted(self):
        self.assertIn('MODEL_REVIEW_ONLY', self.blocked(lambda p:p.update(decision='REVIEW')))

    def test_complete_no_edit_raw_abstain_stays_abstain(self):
        result, _ = self.validate(lambda p:p.update(decision='ABSTAIN', candidate_edits=[]))
        self.assertEqual(result.decision, 'ABSTAIN')
        self.assertEqual(result.candidate_edits, ())

    def test_pending_review_cannot_dispatch(self):
        pending = self.flow.proposal()
        detector = self.flow.detector()
        result = self.flow.continuation(pending, detector)
        self.assertEqual(result.state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)
        detector.detect.assert_not_called()

    def test_rejected_review_cannot_dispatch_without_constraint_confirmation(self):
        review = self.accepted('REJECT', checked=False)
        detector = self.flow.detector()
        self.assertEqual(self.flow.continuation(review, detector).state, PipelineState.EDIT_INTENT_REJECTED)
        detector.detect.assert_not_called()

    def test_needs_review_cannot_dispatch(self):
        review = self.accepted('NEEDS_REVIEW', checked=False)
        detector = self.flow.detector()
        self.assertEqual(self.flow.continuation(review, detector).state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)
        detector.detect.assert_not_called()

    def test_acceptance_requires_instruction_check_beyond_two_inspection_flags(self):
        pending = self.flow.proposal()
        with self.assertRaisesRegex(ValueError, 'complete original user instructions'):
            decide(pending, pending.with_name('invalid.json'), 'ACCEPT_FOR_GROUNDING_TEST',
                   'synthetic reviewer', 'Synthetic check only', True, True)
        self.assertFalse(pending.with_name('invalid.json').exists())

    def test_confirmed_synthetic_acceptance_allows_original_phrase_grounding_only(self):
        review = self.accepted()
        self.assertTrue(verify(review)['checked_user_instructions'])
        detector = self.flow.detector()
        result = self.flow.continuation(review, detector)
        self.assertEqual(result.state, PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, result.errors)
        detector.detect.assert_called_once_with(self.flow.image, 'synthetic object')
        detector.close.assert_called_once()
        self.assertFalse(result.image_generation_permitted)
        for key in ('sam_authorized','image_edit_authorized','diffusion_authorized','cultural_transformation_authorized'):
            self.assertIs(verify(review)[key], False)

    def test_synthetic_acceptance_still_cannot_dispatch_real_model(self):
        result = self.flow.continuation(self.accepted())
        self.assertEqual(result.state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)

    def test_changed_review_instructions_invalidate_acceptance(self):
        review = self.accepted()
        self.flow.mutate(review, lambda v:v.update(user_instructions='Different instructions'))
        with self.assertRaises(ValueError):
            verify(review)

    def test_changed_planning_input_instructions_invalidate_acceptance(self):
        review = self.accepted()
        self.flow.mutate(review.parent/'evidence/planning_input.json', lambda v:v.update(user_instructions='Modified'))
        self.assertEqual(self.flow.continuation(review, self.flow.detector()).state, PipelineState.FAILED)

    def test_modified_image_and_plan_invalidate_review(self):
        review = self.accepted()
        image = review.parent/'original.png'
        before = image.read_bytes()
        image.write_bytes(before+b' ')
        with self.assertRaises(ValueError):verify(review)
        image.write_bytes(before)  # restore disposable fixture to isolate the plan check
        plan = review.parent/'evidence/validated_plan.json'
        plan.write_bytes(plan.read_bytes()+b' ')
        with self.assertRaises(ValueError):verify(review)

    def test_changed_confirmation_cannot_be_treated_as_acceptance(self):
        review = self.accepted()
        self.flow.mutate(review, lambda v:v.update(checked_user_instructions=False))
        with self.assertRaises(ValueError):verify(review)

    def test_pending_cannot_claim_instruction_confirmation(self):
        pending = self.flow.proposal()
        self.flow.mutate(pending, lambda v:v.update(checked_user_instructions=True))
        with self.assertRaises(ValueError):verify(pending)

    def test_warning_status_cannot_claim_automatic_satisfaction(self):
        pending = self.flow.proposal()
        self.flow.mutate(pending, lambda v:v.update(user_constraints_status='AUTOMATICALLY_SATISFIED'))
        with self.assertRaises(ValueError):verify(pending)

    def test_bound_warning_cannot_be_erased(self):
        pending = self.flow.proposal()
        self.flow.mutate(pending, lambda v:v.update(planning_issues=[]))
        with self.assertRaises(ValueError):verify(pending)

    def test_cli_presents_complete_review_context(self):
        pending = self.flow.proposal()
        with redirect_stdout(StringIO()) as output:
            main(['verify','--review',str(pending)])
        displayed = json.loads(output.getvalue())
        self.assertEqual(displayed['user_instructions'], INSTRUCTIONS)
        self.assertEqual(displayed['candidate']['localization_phrase'], 'synthetic object')
        self.assertEqual(displayed['candidate']['proposed_change'], 'a different surface material')
        self.assertIn('background', displayed['must_preserve'])
        self.assertEqual(displayed['planning_issues'][0]['code'], 'USER_CONSTRAINTS_UNRESOLVED')
        self.assertEqual(displayed['uncertainties'], [])
        self.assertTrue(displayed['original_image'].endswith('original.png'))

    def test_cli_requires_and_records_instruction_check_flag(self):
        pending = self.flow.proposal()
        out = pending.with_name('cli_decision.json')
        args = ['decide','--pending',str(pending),'--out',str(out),'--decision','ACCEPT_FOR_GROUNDING_TEST',
                '--reviewer','synthetic reviewer','--reason','Synthetic test only', '--inspected-original','--inspected-edit']
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit): main(args)
        with redirect_stdout(StringIO()): main(args+['--checked-user-instructions'])
        self.assertTrue(verify(out)['checked_user_instructions'])

    def test_legacy_no_instruction_review_remains_verifiable(self):
        self.base.request = replace(self.base.request, user_instructions=None)
        pending = self.flow.proposal()
        def legacy(record):
            record['schema_version'] = 1
            for key in ('user_constraints_status','planning_issues','uncertainties','checked_user_instructions'):
                record.pop(key)
        self.flow.mutate(pending, legacy)
        verify(pending)
        out = decide(pending, pending.with_name('legacy_decision.json'), 'ACCEPT_FOR_GROUNDING_TEST',
                     'synthetic reviewer', 'Synthetic legacy test', True, True)
        self.assertEqual(verify(out)['schema_version'], 1)
        self.assertEqual(self.flow.continuation(out, self.flow.detector()).state, PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW)

    def test_schema_downgrade_cannot_bypass_instruction_confirmation(self):
        review = self.accepted()
        self.flow.mutate(review, lambda v:v.update(schema_version=1))
        with self.assertRaisesRegex(ValueError, 'legacy review'):
            verify(review)

    def test_free_text_compatibility_is_not_certified_by_eligibility(self):
        # No claim that lexical validation can resolve this semantic conflict.
        self.base.request = replace(self.base.request, user_instructions='Keep the original object completely unchanged.')
        pending = self.flow.proposal()
        record = verify(pending)
        self.assertEqual(record['user_constraints_status'], 'REQUIRES_HUMAN_VERIFICATION')
        self.assertFalse(record['checked_user_instructions'])
        rejected = decide(pending, pending.with_name('rejected.json'), 'REJECT', 'synthetic reviewer',
            'Synthetic review: the requested preservation conflicts with the proposal.', True, True,
            checked_user_instructions=True)
        self.assertEqual(self.flow.continuation(rejected, self.flow.detector()).state, PipelineState.EDIT_INTENT_REJECTED)


if __name__ == '__main__':
    unittest.main()
