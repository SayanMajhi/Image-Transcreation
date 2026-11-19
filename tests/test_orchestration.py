"""Mocked integration: no weights, service or real human approval required."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from transcreation.config import PlannerConfig
from transcreation.contracts import InpaintingInput, VerifiedObject
from transcreation.orchestration import PipelineInput, PipelineState, ReplayChain, run_pipeline, validate_planner_audit
from transcreation.stages.caption import SmolCaptionResult
from transcreation.stages.planning import parse_model_draft, validate_planning_result


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(request, raw):
    draft, initial = parse_model_draft(raw)
    final, issues = validate_planning_result(request, draft, initial)
    return {"input": json.loads(json.dumps(asdict(request))), "response": {"message": {"content": json.dumps(raw)}},
            "raw_planning_result": raw, "planning_result": json.loads(json.dumps(asdict(final))),
            "validation": {"status": "valid", "issues": issues}, "unload": {"status": "sent"}}


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        from test_mask_review import MaskReviewTests
        self.fixture = MaskReviewTests(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root; self.image = self.fixture.source/"original.png"
        self.request = PipelineInput(str(self.image), sha(self.image), "test target", str(self.root/"run"), "AUTOMATED_PLANNING",
                                     verified_objects=(VerifiedObject("object-1", "synthetic object"),))
        self.caption = SmolCaptionResult("A synthetic object sits on a surface.", "synthetic captioner",
                                        image_dimensions=(60, 40), eos_reached=True)
        self.captioner = SimpleNamespace(model=object(), processor=object(), caption=Mock(return_value=self.caption))
        self.raw = {"decision": "PROPOSE", "decision_reason": "A conditional material adaptation.",
                    "scene_summary": "Caption describes a synthetic object.", "candidate_edits": [{
                        "object_description": "synthetic object", "localization_phrase": "synthetic object",
                        "proposed_change": "a different surface material", "cultural_reason": "Contextual test suggestion only",
                        "identity_uncertain": False, "verified_object_id": "object-1"}],
                    "must_preserve": ["background"], "uncertainties": [], "verification_requirements": []}
        self.planner = Mock(); self.planner.config = PlannerConfig(); self.planner.api.return_value = {"models": []}
        self.planner.last_record = {}; self.planner.record_plan.side_effect = self.record

    def record(self, request):
        self.assertIsNone(self.captioner.model)  # caption weights released BEFORE Qwen execution
        result = audit(request, self.raw); self.planner.last_record = result
        return result

    def automated(self):
        with patch('transcreation.orchestration.create_captioner', return_value=self.captioner), \
             patch('transcreation.orchestration.OllamaPlanner', return_value=self.planner), \
             patch('transcreation.stages.inpainting.run_inpainting') as generation, \
             patch('transcreation.stages.grounding.GroundingDetector') as grounding, \
             patch('transcreation.stages.segmentation.SamSegmenter') as sam:
            result = run_pipeline(self.request)
            generation.assert_not_called(); grounding.assert_not_called(); sam.assert_not_called()
        return result

    def chain(self, accepted_box=True, accepted_mask=False, with_generation=True):
        from scripts.review_grounding import prepare, decide
        source = self.fixture.source
        box_file = None
        if accepted_box:
            pending = prepare(source/'source_detection.json', self.image, self.root/'box_review')
            box_file = pending.parent/'accepted.json'
            decide(pending, box_file, 'ACCEPT', 'synthetic named reviewer', 'Unit-test fixture only', 0, True, True)
        mask_review = self.fixture.request
        if accepted_mask:
            self.fixture.accept(); mask_review = self.fixture.out
        fixed = 'Synthetic fixed research material prompt'
        generation = None
        if with_generation:
            directory = self.root/'old_inpainting'; directory.mkdir()
            mask_path = source/'mask_1.png'
            with Image.open(mask_path) as mask:
                final = Image.composite(Image.new('RGB', (60, 40), 'blue'), Image.new('RGB', (60, 40), 'white'), mask)
            final.save(directory/'final.png')
            previous = InpaintingInput(str(self.image), sha(self.image), str(self.fixture.segmentation), sha(self.fixture.segmentation),
                                        str(mask_path), sha(mask_path), 1, fixed, 'Synthetic fixture, not human approval', 'RESEARCH_ONLY')
            bound = self.fixture.result.request
            payload = {"status":"COMPLETED", "scope":"RESEARCH_ONLY", "human_approved":False,"cultural_edit_authorized":False,
                       "request":asdict(previous),"source_sam":{"model_id":self.fixture.result.model_id,"revision":self.fixture.result.resolved_revision,
                       "grounding_index":bound.prediction_index,"grounding_box":list(bound.selected_detection.box),"detection_sha256":bound.detection_sha256,
                       "point_sha256":bound.point_prompt_sha256,"selection_status":bound.selection_status},
                       "artifact_sha256":{"final.png":sha(directory/'final.png')}}
            generation = directory/'inpainting.json'; generation.write_text(json.dumps(payload))
        return ReplayChain('synthetic object', str(source/'source_detection.json'), sha(source/'source_detection.json'), fixed,
                           0, str(self.fixture.segmentation), sha(self.fixture.segmentation), 1, sha(source/'mask_1.png'),
                           str(box_file) if box_file else None, sha(box_file) if box_file else None,
                           str(mask_review), sha(mask_review), str(generation) if generation else None, sha(generation) if generation else None)

    def replay(self, chain):
        request = replace(self.request, execution_mode='RESEARCH_REPLAY', replay=chain)
        with patch('transcreation.orchestration.create_captioner') as caption, \
             patch('transcreation.orchestration.OllamaPlanner') as planner, \
             patch('transcreation.stages.grounding.GroundingDetector') as detector, \
             patch('transcreation.stages.segmentation.SamSegmenter') as sam, \
             patch('transcreation.stages.inpainting.run_inpainting') as generation:
            result = run_pipeline(request)
            for operation in [caption,planner,detector,sam,generation]: operation.assert_not_called()
        return result

    def test_caption_to_planner_handoff_and_propose_gate(self):
        result = self.automated()
        self.assertEqual(result.state, PipelineState.EDIT_PROPOSAL_READY)
        actual = self.planner.record_plan.call_args.args[0]
        self.assertEqual(actual.source_caption, self.caption.caption)
        self.assertEqual(actual.verified_objects, self.request.verified_objects)
        self.assertFalse(result.image_generation_permitted)
        self.assertEqual(result.stopped_at, 'edit_intent_review')

    def test_caption_truncation_requires_review(self):
        self.captioner.caption.return_value = replace(self.caption,eos_reached=False,token_ceiling_reached=True)
        result = self.automated(); self.assertEqual(result.state,PipelineState.PLAN_REQUIRES_REVIEW)

    def test_qwen_review_stops(self):
        self.raw.update(decision='REVIEW')
        result = self.automated();self.assertEqual(result.state,PipelineState.PLAN_REQUIRES_REVIEW)
        self.assertIn('planning',result.completed_stages)

    def test_qwen_abstain_stops_without_edit(self):
        self.raw.update(decision='ABSTAIN',candidate_edits=[],uncertainties=['minor descriptive uncertainty'])
        self.assertEqual(self.automated().state,PipelineState.NO_EDIT_JUSTIFIED)

    def test_invalid_candidate_quarantined(self):
        self.raw['candidate_edits'][0]['object_description']='null'
        result=self.automated();self.assertEqual(result.state,PipelineState.PLAN_REQUIRES_REVIEW)
        saved=json.loads((Path(self.request.output_dir)/'validated_plan.json').read_text())
        self.assertEqual(saved['planning_result']['candidate_edits'],[])

    def test_future_object_localization_is_not_used(self):
        self.raw['candidate_edits'][0]['localization_phrase']='replacement vase'
        self.assertEqual(self.automated().state,PipelineState.PLAN_REQUIRES_REVIEW)

    def test_original_image_hash_mismatch(self):
        self.request=replace(self.request,image_sha256='f'*64)
        result=self.automated();self.assertEqual(result.state,PipelineState.FAILED)
        self.planner.record_plan.assert_not_called();self.captioner.caption.assert_not_called()

    def test_caption_failure_cleanup_and_error(self):
        self.captioner.caption.side_effect=RuntimeError('synthetic caption failure')
        result=self.automated();self.assertEqual(result.state,PipelineState.FAILED)
        self.assertIn('synthetic caption failure',result.reason);self.assertIsNone(self.captioner.model)
        self.planner.unload.assert_called_once();self.planner.record_plan.assert_not_called()

    def test_planner_connection_error_propagates_code(self):
        def failed(request):
            record={'validation':{'status':'error','code':'connection_failed','message':'synthetic connection failure'},'unload':{'status':'sent'}}
            self.planner.last_record=record;return record
        self.planner.record_plan.side_effect=failed
        result=self.automated();self.assertEqual(result.state,PipelineState.FAILED)
        self.assertEqual(result.errors[-1]['code'],'connection_failed')

    def test_cleanup_failure_is_not_hidden(self):
        def record(request):
            value=audit(request,self.raw);value['unload']={'status':'error'};self.planner.last_record=value;return value
        self.planner.record_plan.side_effect=record;self.planner.unload.side_effect=RuntimeError('unload failed')
        result=self.automated();self.assertEqual(result.state,PipelineState.FAILED);self.assertEqual(result.stopped_at,'resource_cleanup')

    def test_stage_order_and_release_before_plan(self):
        result=self.automated();actions=[x['action'] for x in result.transitions]
        self.assertLess(actions.index('CAPTION_COMPLETED'),actions.index('MODEL_REFERENCES_RELEASED'))
        self.assertLess(actions.index('MODEL_REFERENCES_RELEASED'),actions.index('VALIDATED'))
        self.assertLess(actions.index('VALIDATED'),actions.index('QWEN_UNLOAD_CONFIRMED'))
        self.assertEqual(result.transitions[-1]['action'],'STOP')

    def test_source_changed_during_caption_stops_before_qwen(self):
        def mutate(image):
            self.image.write_bytes(self.image.read_bytes()+b'changed');return self.caption
        self.captioner.caption.side_effect=mutate
        result=self.automated();self.assertEqual(result.state,PipelineState.FAILED);self.planner.record_plan.assert_not_called()

    def test_replay_success_is_not_permission_or_generation(self):
        result=self.replay(self.chain(accepted_mask=True))
        self.assertEqual(result.state,PipelineState.RESEARCH_REPLAY_VALIDATED);self.assertTrue(result.replay_validated)
        self.assertFalse(result.image_generation_permitted);self.assertEqual(result.stopped_at,'generation_authorization')
        self.assertEqual(result.completed_stages,('source','grounding_evidence','segmentation_evidence','inpainting_evidence'))

    def test_grounding_no_detection_stops_before_sam(self):
        chain=self.chain(accepted_box=False)
        p=Path(chain.detection_file);data=json.loads(p.read_text());data.update(status='NO_DETECTIONS',detections=[]);p.write_text(json.dumps(data))
        result=self.replay(replace(chain,detection_sha256=sha(p)))
        self.assertEqual(result.state,PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW);self.assertNotIn('segmentation',result.artifact_ids)

    def test_multiple_boxes_without_explicit_index(self):
        chain=self.chain(accepted_box=False);p=Path(chain.detection_file);data=json.loads(p.read_text());data['detections']*=2;p.write_text(json.dumps(data))
        result=self.replay(replace(chain,prediction_index=None,detection_sha256=sha(p)))
        self.assertEqual(result.state,PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW);self.assertNotIn('segmentation',result.artifact_ids)

    def test_mismatched_source_query_stops(self):
        chain=self.chain();result=self.replay(replace(chain,source_phrase='future replacement'))
        self.assertEqual(result.state,PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW);self.assertNotIn('segmentation',result.artifact_ids)

    def test_missing_box_review_is_not_promoted(self):
        result=self.replay(self.chain(accepted_box=False))
        self.assertEqual(result.state,PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW)
        self.assertTrue(result.replay_validated);self.assertIn('BOX_REVIEW_MISSING',result.required_reviews)

    def test_incorrect_box_review_does_not_reach_sam(self):
        chain=self.chain();p=Path(chain.box_review_file);data=json.loads(p.read_text());data['reviewer']='YOUR_NAME';p.write_text(json.dumps(data))
        result=self.replay(replace(chain,box_review_sha256=sha(p)))
        self.assertEqual(result.state,PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW);self.assertNotIn('segmentation',result.artifact_ids)

    def test_pending_mask_requires_review(self):
        result=self.replay(self.chain())
        self.assertEqual(result.state,PipelineState.MASK_REQUIRES_REVIEW);self.assertFalse(result.image_generation_permitted)
        self.assertIn('MASK_REVIEW_PENDING',result.required_reviews)

    def test_mask_review_wrong_selected_candidate(self):
        chain=self.chain();p=self.fixture.case/'pending_0.json'
        result=self.replay(replace(chain,mask_review_file=str(p),mask_review_sha256=sha(p)))
        self.assertEqual(result.state,PipelineState.FAILED);self.assertNotIn('inpainting',result.artifact_ids)

    def test_invalid_mask_or_hash_cannot_reach_inpainting(self):
        chain=self.chain();p=self.fixture.source/'mask_1.png';p.write_bytes(p.read_bytes()+b'changed')
        result=self.replay(chain);self.assertEqual(result.state,PipelineState.FAILED);self.assertNotIn('inpainting',result.artifact_ids)

    def test_detection_hash_mismatch(self):
        result=self.replay(replace(self.chain(),detection_sha256='f'*64))
        self.assertEqual(result.state,PipelineState.FAILED);self.assertEqual(result.stopped_at,'grounding_evidence')

    def test_existing_inpainting_failure_propagates_without_retry(self):
        chain=self.chain();p=Path(chain.inpainting_file);d=json.loads(p.read_text());d.update(status='ERROR',observations=['synthetic saved OOM']);p.write_text(json.dumps(d))
        result=self.replay(replace(chain,inpainting_sha256=sha(p)))
        self.assertEqual(result.state,PipelineState.FAILED);self.assertIn('synthetic saved OOM',result.reason)

    def test_wrong_fixed_prompt_is_not_silently_replaced(self):
        result=self.replay(replace(self.chain(),fixed_generation_prompt='a different prompt'))
        self.assertEqual(result.state,PipelineState.FAILED);self.assertEqual(result.stopped_at,'inpainting_evidence')

    def test_tampered_final_image_rejected(self):
        chain=self.chain();p=Path(chain.inpainting_file).parent/'final.png';p.write_bytes(p.read_bytes()+b'tampered')
        result=self.replay(chain);self.assertEqual(result.state,PipelineState.FAILED)

    def test_separate_modes_and_missing_target(self):
        with self.assertRaises(ValueError):replace(self.request,target_culture='')
        with self.assertRaises(ValueError):replace(self.request,replay={'raw_rejected_plan':True})
        with self.assertRaises(ValueError):replace(self.request,execution_mode='RESEARCH_REPLAY')
        with self.assertRaises(TypeError):PipelineInput(**{**asdict(self.request),'image_generation_permitted':True})

    def test_no_overwrite_user_output(self):
        out=Path(self.request.output_dir);out.mkdir();(out/'pipeline_result.json').write_text('user work')
        with self.assertRaises(FileExistsError):self.automated()
        self.assertEqual((out/'pipeline_result.json').read_text(),'user work')

    def test_research_evidence_cannot_claim_human_approval(self):
        chain=self.chain();p=Path(chain.inpainting_file);d=json.loads(p.read_text());d['human_approved']=True;p.write_text(json.dumps(d))
        self.assertEqual(self.replay(replace(chain,inpainting_sha256=sha(p))).state,PipelineState.FAILED)


if __name__=='__main__':
    unittest.main()
