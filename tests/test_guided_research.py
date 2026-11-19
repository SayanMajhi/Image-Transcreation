"""Synthetic/mocked guided handoffs; no real approvals, downloads or model calls."""
from dataclasses import asdict, replace
from contextlib import ExitStack, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from PIL import Image

from transcreation.guided_research import ResearchInput, file_hash, run_guided_research


class GuidedResearchTests(unittest.TestCase):
    def setUp(self):
        from test_mask_review import MaskReviewTests
        fixture = MaskReviewTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.image = fixture.source/'original.png'
        self.detection = fixture.source/'source_detection.json'
        self.segmentation = fixture.segmentation
        self.mask = fixture.source/'mask_1.png'
        self.root = fixture.root
        self.request = ResearchInput(str(self.image), file_hash(self.image), 'test source', 'test target',
            'Synthetic replacement objective', 'Preserve surrounding scene', 'synthetic object',
            'Synthetic blue surface', 'Synthetic unapproved research assumption', str(self.root/'run'))
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.idle = self.stack.enter_context(patch('transcreation.guided_research._planner_idle'))
        self.detector = self.stack.enter_context(patch('transcreation.stages.grounding.GroundingDetector'))
        self.segmenter = self.stack.enter_context(patch('transcreation.stages.segmentation.SamSegmenter'))
        self.generate = self.stack.enter_context(patch('transcreation.stages.inpainting.run_inpainting'))
        from scripts.review_grounding import _evidence
        self.grounding, _ = _evidence(self.image.read_bytes(), self.detection.read_bytes())
        self.detector.return_value.detect.return_value = self.grounding
        self.segmenter.return_value.segment.return_value = fixture.result
        self.counter = 0

    def box(self, **kwargs):
        return replace(self.request, detection_file=str(self.detection), detection_sha256=file_hash(self.detection),
                       prediction_index=0, selection_note='Synthetic explicit inspection choice', **kwargs)

    def mask_request(self):
        return replace(self.box(), segmentation_file=str(self.segmentation),
                       segmentation_sha256=file_hash(self.segmentation), mask_index=1, mask_sha256=file_hash(self.mask))

    def run_case(self, request):
        self.counter += 1
        return run_guided_research(replace(request, output_dir=str(self.root/f'run_{self.counter}')))

    def fake_generation(self, request, config, out):
        out.mkdir()
        with Image.open(request.source_image) as original, Image.open(request.mask_file) as mask:
            Image.composite(Image.new('RGB', original.size, 'blue'), original, mask).save(out/'final.png')
        return {'status':'COMPLETED'}

    def test_missing_box_selection_stops_after_live_boundary_mock(self):
        result = self.run_case(self.request)
        self.assertEqual(result['status'], 'SOURCE_OBJECT_REQUIRES_REVIEW')
        self.detector.return_value.close.assert_called_once()
        self.segmenter.assert_not_called(); self.generate.assert_not_called()

    def test_no_implicit_selection_from_saved_detection(self):
        result = self.run_case(replace(self.box(), prediction_index=None))
        self.assertEqual(result['status'], 'SOURCE_OBJECT_REQUIRES_REVIEW')
        self.segmenter.assert_not_called(); self.generate.assert_not_called()

    def test_explicit_box_to_sam_handoff_uses_source_not_replacement(self):
        result = self.run_case(self.box())
        self.assertEqual(result['status'], 'MASK_REQUIRES_REVIEW')
        supplied = self.segmenter.return_value.segment.call_args.args[0]
        self.assertEqual(supplied.source_phrase, 'synthetic object')
        self.assertNotEqual(supplied.source_phrase, self.request.generation_prompt)
        self.assertEqual(supplied.selection_status, 'RESEARCH_ONLY')
        self.segmenter.return_value.close.assert_called_once(); self.generate.assert_not_called()

    def test_missing_mask_selection_keeps_all_candidates(self):
        req = replace(self.mask_request(), mask_index=None, mask_sha256=None)
        result = self.run_case(req)
        self.assertEqual(result['status'], 'MASK_REQUIRES_REVIEW')
        self.generate.assert_not_called()

    def test_explicit_lower_score_mask_generation_and_independent_pixel_check(self):
        self.generate.side_effect = self.fake_generation
        result = self.run_case(self.mask_request())
        self.assertEqual(result['status'], 'GENERATION_COMPLETED')
        self.assertFalse(result['human_approved']); self.assertFalse(result['automated_plan_success'])
        self.assertFalse(result['cultural_edit_authorized'])
        supplied = self.generate.call_args.args[0]
        self.assertEqual(supplied.candidate_index, 1)
        self.assertEqual(supplied.scope, 'RESEARCH_ONLY')
        self.assertEqual(result['pixel_verification']['changed_outside_mask'], 0)
        self.assertGreater(result['pixel_verification']['changed_inside_mask'], 0)
        self.detector.assert_not_called(); self.segmenter.assert_not_called()

    def test_false_success_with_outside_changes_is_rejected(self):
        def corrupt(req, config, out):
            self.fake_generation(req, config, out)
            with Image.open(out/'final.png') as im:
                im.putpixel((0,0),(0,0,0)); im.save(out/'final.png')
            return {'status':'COMPLETED'}
        self.generate.side_effect = corrupt
        self.assertEqual(self.run_case(self.mask_request())['status'], 'FAILED')

    def test_failed_generation_is_not_success(self):
        self.generate.return_value = {'status':'ERROR','observations':['synthetic CUDA failure']}
        result = self.run_case(self.mask_request())
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('synthetic CUDA failure', result['reason'])

    def test_protected_sample_in_mask_blocks_generation(self):
        result = self.run_case(replace(self.mask_request(), protected_points=((12,12),)))
        self.assertEqual(result['status'], 'MASK_REQUIRES_REVIEW')
        self.assertEqual(result['mask_guard_check']['included_protected_samples'], [[12,12]])
        self.generate.assert_not_called()

    def test_outside_protected_samples_do_not_expand_edit_scope(self):
        self.generate.side_effect = self.fake_generation
        result = self.run_case(replace(self.mask_request(), protected_points=((0,0),)))
        self.assertEqual(result['status'], 'GENERATION_COMPLETED')
        self.assertEqual(result['mask_guard_check']['included_protected_samples'], [])
        self.assertEqual(result['pixel_verification']['changed_outside_mask'], 0)

    def test_protected_samples_require_original_coordinates(self):
        with self.assertRaises(ValueError):replace(self.request, protected_points=((True,5),))
        result = self.run_case(replace(self.request, protected_points=((999,5),)))
        self.assertEqual(result['status'], 'FAILED')
        self.detector.assert_not_called()

    def test_failure_releases_detector(self):
        self.detector.return_value.detect.side_effect = RuntimeError('synthetic failure')
        self.assertEqual(self.run_case(self.request)['status'], 'FAILED')
        self.detector.return_value.close.assert_called_once(); self.segmenter.assert_not_called()

    def test_failure_releases_sam_and_blocks_generation(self):
        self.segmenter.return_value.segment.side_effect = RuntimeError('synthetic SAM error')
        self.assertEqual(self.run_case(self.box())['status'], 'FAILED')
        self.segmenter.return_value.close.assert_called_once(); self.generate.assert_not_called()

    def test_model_order_residency_preflight_then_sam_then_release(self):
        order = Mock()
        order.attach_mock(self.idle, 'idle'); order.attach_mock(self.segmenter, 'sam')
        self.run_case(self.box())
        names = [c[0] for c in order.mock_calls]
        self.assertLess(names.index('idle'), names.index('sam'))
        self.assertLess(names.index('sam().segment'), names.index('sam().close'))

    def test_unrelated_resident_model_blocks_dispatch(self):
        self.idle.side_effect = RuntimeError('unrelated model resident')
        self.assertEqual(self.run_case(self.request)['status'], 'FAILED')
        self.detector.assert_not_called(); self.segmenter.assert_not_called(); self.generate.assert_not_called()

    def test_all_pinned_evidence_tampering_blocks_generation(self):
        for name in ('image_sha256','detection_sha256','segmentation_sha256','mask_sha256'):
            with self.subTest(name=name):
                result = self.run_case(replace(self.mask_request(), **{name:'f'*64}))
                self.assertEqual(result['status'], 'FAILED')
                self.generate.assert_not_called()

    def test_replacement_as_source_query_mismatch_is_rejected(self):
        self.assertEqual(self.run_case(replace(self.box(), source_phrase='future blue object'))['status'], 'FAILED')
        self.segmenter.assert_not_called()

    def test_invalid_index_and_unselected_multiple_boxes(self):
        result = self.run_case(replace(self.box(), prediction_index=99))
        self.assertEqual(result['status'], 'FAILED'); self.segmenter.assert_not_called()

    def test_no_detections_are_retained_without_dispatch(self):
        from dataclasses import asdict
        data = replace(self.grounding, status='NO_DETECTIONS', detections=())
        self.detection.write_text(json.dumps(asdict(data)))
        self.assertEqual(self.run_case(self.box())['status'], 'SOURCE_OBJECT_REQUIRES_REVIEW')
        self.segmenter.assert_not_called()

    def test_no_approval_or_rejected_plan_fields_accepted(self):
        for field in ('planner_audit','review_file','human_approved','candidate_edits','edit_intent'):
            with self.subTest(field=field), self.assertRaises(TypeError):
                ResearchInput(**{**asdict(self.request),field:'synthetic rejected plan'})
        for scope in ('PROPOSE','REVIEW','ABSTAIN','APPROVED'):
            with self.assertRaises(ValueError):replace(self.request,scope=scope)

    def test_require_complete_explicit_specification_and_paired_hashes(self):
        for fields in ({'generation_prompt':''},{'image_sha256':None},{'research_assumptions':''},
                       {'detection_file':'x'},{'prediction_index':True},{'mask_index':1},
                       {'execution_mode':'AUTOMATED_PLANNING'}):
            with self.subTest(fields=fields),self.assertRaises(ValueError):replace(self.request,**fields)

    def test_originals_preserved_and_outputs_cannot_overwrite(self):
        before = {p:p.read_bytes() for p in self.fixture.source.iterdir() if p.is_file()}
        self.generate.side_effect = self.fake_generation
        req = self.mask_request(); result = run_guided_research(req)
        self.assertEqual(result['status'], 'GENERATION_COMPLETED')
        self.assertTrue(all(p.read_bytes()==data for p,data in before.items()))
        with self.assertRaises(FileExistsError): run_guided_research(req)

    def test_cli_routes_guided_request_without_planner(self):
        from transcreation.cli import main
        path = self.root/'input.json'; path.write_text(json.dumps(asdict(self.request)))
        with redirect_stdout(StringIO()): main(['run','--input',str(path)])
        self.detector.assert_called_once(); self.segmenter.assert_not_called()

