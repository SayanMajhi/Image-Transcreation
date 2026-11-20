"""Synthetic end-to-end workflow tests. No real models or human approvals."""
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from transcreation.contracts import GroundingDetection, GroundingResult, SegmentationMask, SegmentationResult
from transcreation.stages.grounding import save_grounding_artifacts
from transcreation.stages.segmentation import load_segmentation_input
from transcreation.stages.inpainting import validate_inputs
from transcreation.stages.planning import parse_model_draft, validate_planning_result
from transcreation.workflow import Workflow, sha, read, write


class SyntheticBackend:
    def __init__(self):
        self.calls = []
        self.decision = 'PROPOSE'
        self.fail = False
        self.corrupt = False
        self.overlap = False

    def caption(self, source):
        self.calls.append('caption')
        return {'caption': 'A cup and bowl sit on a table.', 'model_id': 'SYNTHETIC', 'eos_reached': True}

    def plan(self, request):
        self.calls.append('plan')
        raw = {'decision': self.decision, 'decision_reason': 'Synthetic test proposal.',
               'scene_summary': 'The caption reports a cup and bowl on a table.',
               'candidate_edits': [], 'must_preserve': ['table'], 'uncertainties': [],
               'verification_requirements': ['Inspect the image']}
        if self.decision == 'PROPOSE':
            raw['candidate_edits'] = [dict(object_description=o.description, localization_phrase=o.description,
                proposed_change='change exterior to blue', cultural_reason='Synthetic requested styling',
                identity_uncertain=False, verified_object_id=o.object_id) for o in request.verified_objects]
        draft, issues = parse_model_draft(raw)
        result, issues = validate_planning_result(request, draft, issues)
        return json.loads(json.dumps({'input': asdict(request), 'response': {'message': {'content': json.dumps(raw)}},
                                     'raw_planning_result': raw, 'planning_result': asdict(result),
                                     'validation': {'status': 'valid', 'issues': issues}}))

    def ground(self, source, phrase, out):
        self.calls.append('ground')
        x = 5 if phrase == 'cup' or self.overlap else 35
        result = GroundingResult(sha(source), (60, 40), phrase, 'synthetic detector', 'a'*40,
            'DETECTED', (GroundingDetection((x, 5, x+15, 25), .8, phrase),), {}, {}, {}, {})
        save_grounding_artifacts(source, result, out)

    def segment(self, source, detection, index, note, out):
        self.calls.append('segment')
        request = load_segmentation_input(source, detection, index, True, note=note)
        out.mkdir()
        shutil.copyfile(source, out / 'source.png')
        shutil.copyfile(detection, out / 'source_detection.json')
        x0,y0,x1,y1 = map(int, request.selected_detection.box)
        mask = Image.new('L', (60,40)); mask.paste(255, (x0,y0,x1,y1)); mask.save(out/'mask_0.png')
        with Image.open(source) as image:
            image.convert('RGB').save(out/'overlay_0.png')
            image.convert('RGB').save(out/'box.png')
        result = SegmentationResult(request, 'synthetic sam', 'b'*40, 'SEGMENTED',
            (SegmentationMask(0, 'mask_0.png', (60,40), .9, (x1-x0)*(y1-y0), (x0,y0,x1,y1), 'VALID'),), 0,
            {'model_id':'synthetic sam','revision':'b'*40,'source_image_copy':'source.png','source_detection_copy':'source_detection.json'}, {},{},())
        write(out/'segmentation.json', asdict(result))

    def generate(self, request, out):
        self.calls.append('generate')
        out.mkdir()
        if self.fail:
            write(out/'partial.json', {'synthetic_error': True})
            raise RuntimeError('Synthetic model unavailable')
        source, mask, _, _ = validate_inputs(request)
        edited = Image.composite(Image.new('RGB',source.size,'blue'), source, mask)
        if self.corrupt:
            edited.putpixel((0,0), (0,0,0))
        edited.save(out/'final.png')
        write(out/'inpainting.json', {'status':'COMPLETED','request':asdict(request)})


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root/'input.png'
        Image.new('RGB',(60,40),'white').save(self.image)
        self.backend = SyntheticBackend()
        self.wf = Workflow.create(self.root/'run', self.image, 'Change object exterior colors', 'test context', backend=self.backend)

    def review(self, action, **values):
        return self.wf.review(action, 'Synthetic test reviewer', 'Synthetic test declaration only', **values)

    def prepare(self, objects=None):
        self.assertEqual(self.wf.advance(), 'CAPTION_REVIEW')
        self.review('confirm_source', caption='A cup and bowl sit on a table.', objects=objects or ['cup'])
        return self.wf.advance()

    def to_generation(self):
        self.assertEqual(self.wf.advance(),'BOX_REVIEW')
        self.review('select_box',index=0)
        self.assertEqual(self.wf.advance(),'MASK_REVIEW')
        self.review('select_mask',index=0)
        self.assertEqual(self.wf.state['stage'],'GENERATION_REVIEW')
        self.review('authorize_generation')

    def test_complete_two_pass_run_resume_and_final_review(self):
        self.assertEqual(self.prepare(['cup','bowl']),'PLAN_REVIEW')
        self.review('approve_plan')
        self.to_generation()
        first_source = self.wf.state['current_source']
        self.assertEqual(self.wf.advance(),'GROUNDING')
        first_final = self.wf.state['current_source']
        self.assertNotEqual(sha(first_source),sha(first_final))
        self.wf = Workflow(self.root/'run',self.backend)
        self.to_generation()
        request = read(self.wf.state['generation_input'])
        self.assertEqual(request['image_sha256'],sha(first_final))
        self.assertIn('change exterior to blue',request['prompt'])
        self.assertIn('table',request['prompt'])
        self.assertEqual(self.wf.advance(),'FINAL_REVIEW')
        report = read(self.wf.state['final_verification'])
        self.assertEqual(report['changed_outside'],0)
        self.assertEqual(report['changed_inside'],600)
        self.review('needs_changes')
        self.assertEqual(self.wf.state['visual_review'],'NEEDS_CHANGES')
        self.wf.check()

    def test_review_plan_never_dispatches_grounding(self):
        self.backend.decision='REVIEW'
        self.assertEqual(self.prepare(),'REVIEW_REQUIRED')
        with self.assertRaises(ValueError):
            self.review('approve_plan')
        with self.assertRaises(ValueError):
            self.wf.advance()
        self.assertNotIn('ground',self.backend.calls)

    def test_abstain_is_terminal(self):
        self.backend.decision='ABSTAIN'
        self.assertEqual(self.prepare(),'NO_EDIT')
        with self.assertRaises(ValueError):
            self.review('approve_plan')

    def test_review_can_replan_without_rewriting_old_evidence(self):
        self.backend.decision='REVIEW'; self.prepare()
        old = self.wf.state['plan_file']; digest=sha(old)
        self.backend.decision='PROPOSE'
        self.review('confirm_source',caption='A cup on a table.',objects=['cup'],request='Make its exterior blue')
        self.assertEqual(self.wf.advance(),'PLAN_REVIEW')
        self.assertNotEqual(old,self.wf.state['plan_file'])
        self.assertEqual(sha(old),digest)

    def test_mask_and_prompt_require_separate_generation_authorization(self):
        self.prepare(); self.review('approve_plan'); self.wf.advance()
        self.review('select_box',index=0); self.wf.advance(); self.review('select_mask',index=0)
        with self.assertRaises(ValueError):
            self.wf.advance()
        self.assertNotIn('generate', self.backend.calls)

    def test_changed_source_is_rejected_before_model_call(self):
        Path(self.wf.state['original']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.wf.advance()
        self.assertFalse(self.backend.calls)

    def test_changed_prompt_is_rejected(self):
        self.prepare(); self.review('approve_plan'); self.to_generation()
        p=Path(self.wf.state['generation_input']); data=read(p); data['prompt']='unapproved'; write(p,data)
        with self.assertRaises(ValueError):
            self.wf.advance()
        self.assertNotIn('generate',self.backend.calls)

    def test_failure_retries_in_new_directory_without_duplicate_passes(self):
        self.prepare(); self.review('approve_plan'); self.to_generation()
        self.backend.fail=True
        self.assertEqual(self.wf.advance(),'FAILED')
        old_attempt=self.wf.state['attempt']
        self.assertEqual(len(self.wf.state['passes']),0)
        self.backend.fail=False
        self.wf=Workflow(self.root/'run',self.backend); self.wf.retry()
        self.assertEqual(self.wf.advance(),'FINAL_REVIEW')
        self.assertEqual(len(self.wf.state['passes']),1)
        self.assertEqual(self.wf.state['attempt'],old_attempt+1)

    def test_outside_pixel_change_fails_and_rolls_back_pass(self):
        self.prepare(); self.review('approve_plan'); self.to_generation(); self.backend.corrupt=True
        self.assertEqual(self.wf.advance(),'FAILED')
        self.assertIn('Pixel verification failed',self.wf.state['error'])
        self.assertEqual(self.wf.state['passes'],[])
        self.assertFalse((self.wf.root/'final.png').exists())

    def test_second_mask_cannot_overwrite_first_edit(self):
        self.prepare(['cup','bowl']); self.review('approve_plan'); self.to_generation(); self.wf.advance()
        self.backend.overlap=True
        self.wf.advance(); self.review('select_box',index=0); self.wf.advance()
        with self.assertRaisesRegex(ValueError,'overlaps earlier edits'):
            self.review('select_mask',index=0)
        self.assertEqual(len(self.wf.state['passes']),1)

    def test_invalid_box_selection_does_not_advance(self):
        self.prepare(); self.review('approve_plan'); self.wf.advance()
        with self.assertRaises(ValueError):
            self.review('select_box',index=9)
        self.assertEqual(read(self.wf.root/'session.json')['stage'],'BOX_REVIEW')

    def test_interrupt_can_resume_as_failed_attempt(self):
        with patch.object(self.backend,'caption',side_effect=KeyboardInterrupt):
            self.assertEqual(self.wf.advance(),'FAILED')
        self.wf=Workflow(self.root/'run',self.backend); self.wf.retry()
        self.assertEqual(self.wf.advance(),'CAPTION_REVIEW')

    def test_review_page_and_cli_status(self):
        from scripts.workflow import main, review_page
        page=review_page(self.wf)
        self.assertTrue(page.exists())
        self.assertIn('CAPTIONING',page.read_text())
        main(['status','--run',str(self.wf.root)])


if __name__=='__main__':
    unittest.main()
