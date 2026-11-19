"""Synthetic approvals and mock detectors only: no real reviewer or model invocation."""
from dataclasses import asdict, replace
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from scripts.review_edit_intent import prepare, decide, verify, main
from transcreation.contracts import GroundingDetection, GroundingResult
from transcreation.orchestration import IntentReference, PipelineState, run_pipeline


class EditIntentTests(unittest.TestCase):
    def setUp(self):
        from test_orchestration import OrchestrationTests
        self.fixture = OrchestrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.image = self.fixture.root, self.fixture.image
        original_record = self.fixture.record

        def synthetic(request):
            record = original_record(request)
            record["fixture_scope"] = "SYNTHETIC_TEST_ONLY"
            return record

        self.fixture.planner.record_plan.side_effect = synthetic
        self.run = self.root/"run"/"pipeline_result.json"

    def proposal(self):
        self.assertEqual(self.fixture.automated().state, PipelineState.EDIT_PROPOSAL_READY)
        return prepare(self.run, self.image, 0, self.root/"intent")

    def accepted(self, decision="ACCEPT_FOR_GROUNDING_TEST"):
        pending = self.proposal()
        return decide(pending, pending.with_name("decision.json"), decision,
                      "synthetic test reviewer", "Synthetic inspection declaration, not actual human approval", True, True)

    def mutate(self, path, change):
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))

    def rebind_artifact(self, name):
        # Deliberately update a synthetic manifest to exercise semantic revalidation,
        # rather than stopping at the first byte-hash mismatch.
        from scripts.review_grounding import digest
        entry = json.loads(self.run.read_text())['artifact_ids'][name]
        new_hash = digest((self.run.parent/entry['path']).read_bytes())
        def update(value):
            value['artifact_ids'][name].update(id=new_hash, sha256=new_hash)
        self.mutate(self.run, update)

    def detector(self, count=2):
        boxes = tuple(GroundingDetection((i*10, 0, i*10+9, 20), .5, "synthetic object") for i in range(count))
        result = GroundingResult(self.fixture.request.image_sha256, (60, 40), "synthetic object",
                                 "synthetic detector", "a"*40, "DETECTED" if count else "NO_DETECTIONS",
                                 boxes, {}, {}, {}, {})
        detector = Mock()
        detector.detect.return_value = result
        return detector

    def continuation(self, review, detector=None):
        from scripts.review_grounding import digest
        request = replace(self.fixture.request, execution_mode="GROUNDING_TEST", output_dir=str(self.root/"continuation"),
                          edit_intent=IntentReference(str(review), digest(review.read_bytes())) if review else None)
        with patch('transcreation.orchestration.create_captioner') as caption, \
             patch('transcreation.orchestration.OllamaPlanner') as planner, \
             patch('transcreation.stages.grounding.GroundingDetector') as native, \
             patch('transcreation.stages.segmentation.SamSegmenter') as sam, \
             patch('transcreation.stages.inpainting.run_inpainting') as diffusion:
            factory = Mock(return_value=detector) if detector else None
            result = run_pipeline(request, grounding_factory=factory)
            for operation in (caption, planner, native, sam, diffusion):
                operation.assert_not_called()
        return result

    def test_pending_review_binds_exact_original_and_replacement(self):
        pending = self.proposal()
        record = verify(pending)
        self.assertEqual(record['decision'], 'PENDING')
        self.assertEqual(record['candidate']['object_description'], 'synthetic object')
        self.assertEqual(record['candidate']['proposed_change'], 'a different surface material')
        self.assertEqual(record['evidence_scope'], 'SYNTHETIC_TEST_ONLY')
        self.assertIsNone(record['reviewer'])
        self.assertEqual(len(record['planning_result_sha256']), 64)
        self.assertIn('background', record['must_preserve'])

    def test_explicit_acceptance_releases_grounding_only(self):
        review = self.accepted()
        record = verify(review)
        self.assertEqual(record['decision'], 'ACCEPT_FOR_GROUNDING_TEST')
        for key in ('image_edit_authorized', 'sam_authorized', 'diffusion_authorized', 'cultural_transformation_authorized'):
            self.assertIs(record[key], False)

    def test_original_phrase_handoff_all_boxes_retained_then_stop(self):
        review = self.accepted()
        detector = self.detector()
        result = self.continuation(review, detector)
        self.assertEqual(result.state, PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, result.errors)
        detector.detect.assert_called_once_with(self.image, 'synthetic object')
        detector.close.assert_called_once()
        saved = json.loads((self.root/'continuation/grounding/detection.json').read_text())
        self.assertEqual(len(saved['detections']), 2)
        pending = json.loads((self.root/'continuation/box_review/pending.json').read_text())
        self.assertEqual(pending['decision'], 'PENDING')
        self.assertIsNone(pending['selected_prediction_index'])
        self.assertFalse(result.image_generation_permitted)
        copied = self.root/'continuation/evidence/edit_intent/decision.json'
        self.assertEqual(verify(copied)['decision'], 'ACCEPT_FOR_GROUNDING_TEST')
        actions = [e['action'] for e in result.transitions]
        self.assertLess(actions.index('MODEL_RELEASED'), actions.index('STOP'))

    def test_no_detection_stops_for_review(self):
        result = self.continuation(self.accepted(), self.detector(0))
        self.assertEqual(result.state, PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW)
        self.assertEqual(result.stopped_at, 'box_review')

    def test_pending_cannot_dispatch(self):
        result = self.continuation(self.proposal(), self.detector())
        self.assertEqual(result.state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)

    def test_reject_cannot_dispatch(self):
        result = self.continuation(self.accepted('REJECT'), self.detector())
        self.assertEqual(result.state, PipelineState.EDIT_INTENT_REJECTED)

    def test_needs_review_cannot_dispatch(self):
        result = self.continuation(self.accepted('NEEDS_REVIEW'), self.detector())
        self.assertEqual(result.state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)

    def test_missing_review_cannot_dispatch(self):
        self.assertEqual(self.continuation(None).state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)

    def test_synthetic_acceptance_cannot_dispatch_live_detector(self):
        self.assertEqual(self.continuation(self.accepted()).state, PipelineState.EDIT_INTENT_REQUIRES_REVIEW)

    def test_invalid_index_not_implicitly_zero(self):
        self.fixture.automated()
        for index in (-1, 1, None, True):
            with self.subTest(index=index), self.assertRaises(ValueError):
                prepare(self.run, self.image, index, self.root/'invalid')

    def test_placeholder_identity_rejected(self):
        pending = self.proposal()
        for name in ('YOUR_NAME', '<name>', '', 'reviewer', 'null'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                decide(pending, pending.with_name('invalid.json'), 'ACCEPT_FOR_GROUNDING_TEST', name, 'Test reason', True, True)

    def test_both_inspection_declarations_required(self):
        pending = self.proposal()
        for image, edit in ((False, True), (True, False)):
            with self.assertRaises(ValueError):
                decide(pending, pending.with_name('invalid.json'), 'REJECT', 'Synthetic reviewer', 'Test reason', image, edit)

    def test_review_abstain_and_quarantine_block_preparation(self):
        for decision in ('REVIEW', 'ABSTAIN'):
            with self.subTest(decision=decision):
                self.fixture.raw['decision'] = decision
                self.fixture.raw['candidate_edits'] = []
                self.fixture.request = replace(self.fixture.request, output_dir=str(self.root/('run_'+decision)))
                self.fixture.automated()
                with self.assertRaises(ValueError):
                    prepare(self.root/('run_'+decision)/'pipeline_result.json', self.image, 0, self.root/('intent_'+decision))

    def test_tampered_image_blocked(self):
        pending = self.proposal()
        (pending.parent/'original.png').write_bytes(b'modified')
        with self.assertRaises(ValueError):
            verify(pending)

    def test_changed_plan_blocked(self):
        pending = self.proposal()
        target = pending.parent/'evidence/validated_plan.json'
        target.write_bytes(target.read_bytes()+b' ')
        with self.assertRaises(ValueError):
            verify(pending)

    def test_changed_audit_blocked(self):
        pending = self.proposal()
        target = pending.parent/'evidence/planner_audit.json'
        target.write_bytes(target.read_bytes()+b' ')
        with self.assertRaises(ValueError):
            verify(pending)

    def test_changed_original_candidate_in_review_blocked(self):
        pending = self.proposal()
        self.mutate(pending, lambda v: v['candidate'].update(localization_phrase='a different surface material'))
        with self.assertRaises(ValueError):
            verify(pending)

    def test_reviewer_name_alone_not_acceptance(self):
        pending = self.proposal()
        self.mutate(pending, lambda v: v.update(reviewer='Synthetic reviewer'))
        with self.assertRaises(ValueError):
            verify(pending)

    def test_original_run_and_final_audit_preserved(self):
        self.fixture.automated()
        before = {p.name: p.read_bytes() for p in self.run.parent.glob('*.json')}
        pending = prepare(self.run, self.image, 0, self.root/'intent')
        decide(pending, pending.with_name('rejected.json'), 'REJECT', 'Synthetic reviewer', 'Test only', True, True)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.run.parent.glob('*.json')})

    def test_existing_decision_not_overwritten(self):
        decision = self.accepted()
        with self.assertRaises(FileExistsError):
            decide(decision.with_name('pending.json'), decision, 'REJECT', 'Synthetic reviewer', 'Test only', True, True)

    def test_tampered_pending_breaks_decision_chain(self):
        decision = self.accepted()
        pending = decision.with_name('pending.json')
        pending.write_bytes(pending.read_bytes()+b' ')
        with self.assertRaises(ValueError):
            verify(decision)

    def test_edit_permission_cannot_be_added(self):
        pending = self.proposal()
        self.mutate(pending, lambda v: v.update(image_edit_authorized=True))
        with self.assertRaises(ValueError):
            verify(pending)

    def test_wrong_grounding_phrase_fails_and_cleans_up(self):
        review = self.accepted()
        detector = self.detector()
        detector.detect.return_value = replace(detector.detect.return_value, source_phrase='replacement')
        result = self.continuation(review, detector)
        self.assertEqual(result.state, PipelineState.FAILED)
        detector.close.assert_called_once()

    def test_detection_error_propagation_and_cleanup(self):
        detector = self.detector()
        detector.detect.side_effect = RuntimeError('synthetic detection failure')
        result = self.continuation(self.accepted(), detector)
        self.assertEqual(result.state, PipelineState.FAILED)
        self.assertIn('synthetic detection failure', result.reason)
        detector.close.assert_called_once()

    def test_review_hash_mismatch_fails_before_dispatch(self):
        from transcreation.orchestration import IntentReference
        review = self.accepted()
        request = replace(self.fixture.request, execution_mode='GROUNDING_TEST', output_dir=str(self.root/'bad_hash'),
                          edit_intent=IntentReference(str(review), '0'*64))
        result = run_pipeline(request)
        self.assertEqual(result.state, PipelineState.FAILED)

    def test_changed_target_context_fails_before_dispatch(self):
        review = self.accepted()
        self.fixture.request = replace(self.fixture.request, target_culture='other target')
        result = self.continuation(review, self.detector())
        self.assertEqual(result.state, PipelineState.FAILED)

    def test_cli_displays_exact_candidate(self):
        pending = self.proposal()
        with redirect_stdout(StringIO()) as output:
            main(['verify', '--review', str(pending)])
        self.assertIn('synthetic object', output.getvalue())
        self.assertIn('a different surface material', output.getvalue())

    def test_quarantined_candidate_is_not_reviewable_even_with_propose_label(self):
        self.fixture.automated()
        self.mutate(self.run.parent/'planner_audit.json', lambda v: v['validation'].update(
            rejected_candidates=[{'candidate_index': 0, 'issue_codes': ['SYNTHETIC_REJECTION']}]))
        self.rebind_artifact('planner_audit.json')
        with self.assertRaises(ValueError):
            prepare(self.run, self.image, 0, self.root/'intent')

    def test_raw_response_and_saved_final_mismatch_rejected(self):
        self.fixture.automated()
        def change(value):
            raw = json.loads(value['response']['message']['content'])
            raw['candidate_edits'][0]['proposed_change'] = 'a different invented replacement'
            value['response']['message']['content'] = json.dumps(raw)
        self.mutate(self.run.parent/'planner_audit.json', change)
        self.rebind_artifact('planner_audit.json')
        with self.assertRaises(ValueError):
            prepare(self.run, self.image, 0, self.root/'intent')

    def test_unrelated_caption_cannot_be_substituted_with_new_hash(self):
        self.fixture.automated()
        self.mutate(self.run.parent/'caption.json', lambda v: v.update(caption='An unrelated synthetic scene.'))
        self.rebind_artifact('caption.json')
        with self.assertRaises(ValueError):
            prepare(self.run, self.image, 0, self.root/'intent')

    def test_missing_audit_rejected(self):
        self.fixture.automated()
        (self.run.parent/'planner_audit.json').unlink()  # disposable synthetic fixture
        with self.assertRaises(FileNotFoundError):
            prepare(self.run, self.image, 0, self.root/'intent')

    def test_selection_change_in_accepted_record_rejected(self):
        review = self.accepted()
        self.mutate(review, lambda v: v.update(candidate_index=1))
        with self.assertRaises(ValueError):
            verify(review)

    def test_synthetic_marker_cannot_be_removed_from_review(self):
        review = self.accepted()
        self.mutate(review, lambda v: v.update(evidence_scope='REAL_PLANNING_EVIDENCE'))
        with self.assertRaises(ValueError):
            verify(review)

    def test_prepare_does_not_overwrite_evidence(self):
        pending = self.proposal()
        before = pending.read_bytes()
        with self.assertRaises(FileExistsError):
            prepare(self.run, self.image, 0, pending.parent)
        self.assertEqual(before, pending.read_bytes())

    def test_native_route_preflight_precedes_mocked_detector_and_releases(self):
        # Branch coverage only: all verification and model boundaries are mocked.
        # No REAL acceptance record is written or claimed.
        from scripts.review_edit_intent import _proposal
        from scripts.review_grounding import digest
        review = self.accepted()
        record = verify(review)
        binding, payload = _proposal(review.parent/record['run_file'], self.image, 0)
        record['evidence_scope'] = binding['evidence_scope'] = 'REAL_PLANNING_EVIDENCE'
        detector = self.detector()
        order = []
        detector.detect.side_effect = lambda *args: (order.append('detect') or self.detector().detect.return_value)
        detector.close.side_effect = lambda: order.append('close')
        request = replace(self.fixture.request, execution_mode='GROUNDING_TEST', output_dir=str(self.root/'native_mock'),
                          edit_intent=IntentReference(str(review), digest(review.read_bytes())))
        with patch('scripts.review_edit_intent.verify', return_value=record), \
             patch('scripts.review_edit_intent._proposal', return_value=(binding, payload)), \
             patch('transcreation.orchestration._planner_idle', side_effect=lambda p: order.append('idle')), \
             patch('transcreation.orchestration.OllamaPlanner'), \
             patch('transcreation.stages.grounding.GroundingDetector', return_value=detector), \
             patch('transcreation.stages.segmentation.SamSegmenter') as sam, \
             patch('transcreation.stages.inpainting.run_inpainting') as diffusion:
            result = run_pipeline(request)
            sam.assert_not_called(); diffusion.assert_not_called()
        self.assertEqual(result.state, PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, result.errors)
        self.assertEqual(order, ['idle', 'detect', 'close'])

    def test_failed_model_construction_stops_before_downstream(self):
        from scripts.review_grounding import digest
        review = self.accepted()
        request = replace(self.fixture.request, execution_mode='GROUNDING_TEST', output_dir=str(self.root/'load_failure'),
                          edit_intent=IntentReference(str(review), digest(review.read_bytes())))
        factory = Mock(side_effect=RuntimeError('synthetic load failure'))
        result = run_pipeline(request, grounding_factory=factory)
        self.assertEqual(result.state, PipelineState.FAILED)
        self.assertIn('synthetic load failure', result.reason)

    def test_intent_cannot_be_attached_to_research_replay_or_planning(self):
        for mode in ('AUTOMATED_PLANNING', 'RESEARCH_REPLAY'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                replace(self.fixture.request, execution_mode=mode, edit_intent=IntentReference('x.json', '0'*64))

    def test_second_candidate_requires_explicit_index_and_is_bound(self):
        self.fixture.raw['candidate_edits'].append({**self.fixture.raw['candidate_edits'][0],
                                                  'proposed_change': 'another synthetic material'})
        self.fixture.automated()
        pending = prepare(self.run, self.image, 1, self.root/'intent')
        record = verify(pending)
        self.assertEqual(record['candidate_index'], 1)
        self.assertEqual(record['candidate']['proposed_change'], 'another synthetic material')

    def test_continuation_cli_parses_typed_reference(self):
        from types import SimpleNamespace
        from scripts.run_pipeline import main as pipeline_main
        review = self.accepted()
        from scripts.review_grounding import digest
        request = replace(self.fixture.request, execution_mode='GROUNDING_TEST', output_dir=str(self.root/'cli'),
                          edit_intent=IntentReference(str(review), digest(review.read_bytes())))
        path = self.root/'cli_input.json'
        path.write_text(json.dumps(asdict(request)))
        with patch('scripts.run_pipeline.run_pipeline', return_value=SimpleNamespace(
                state=PipelineState.EDIT_INTENT_REQUIRES_REVIEW, stopped_at='review', image_generation_permitted=False)) as run, \
             redirect_stdout(StringIO()):
            pipeline_main(['--input', str(path)])
        self.assertEqual(run.call_args.args[0], request)


if __name__ == '__main__':
    unittest.main()
