"""Offline SAM tests. No model weights or human approval needed by fixtures."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
import torch

from scripts.review_grounding import prepare, decide, digest
from transcreation.config import SamConfig
from transcreation.contracts import SamPoint, GroundingDetection, GroundingResult, PlanningDecision, PlanningResult
from transcreation.stages.segmentation import SamSegmenter, load_segmentation_input, validate_binary_mask


class Inputs(dict):
    def to(self, device):
        return self


class SamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "source.png"
        Image.new("RGB", (100, 60), "white").save(self.image)
        self.detection = self.root / "detection.json"
        result = GroundingResult(digest(self.image.read_bytes()), (100, 60), "test object", "test detector", "a" * 40,
                                 "DETECTED", (GroundingDetection((10, 5, 80, 50), .9, "test object"),), {}, {}, {}, {})
        self.detection.write_text(json.dumps(asdict(result)), encoding="utf-8")
        self.request = self.load()
        self.processor = MagicMock()
        self.inputs = Inputs(pixel_values=torch.zeros((1, 3, 64, 64)), input_boxes=torch.tensor([[[10., 5., 80., 50.]]]),
                             original_sizes=torch.tensor([[60, 100]]), reshaped_input_sizes=torch.tensor([[38, 64]]))
        self.processor.return_value = self.inputs
        self.processor.image_processor.to_dict.return_value = {"test": True}
        self.restored = torch.zeros((1, 3, 60, 100), dtype=torch.bool)
        self.restored[0, :, 5:30, 10:60] = True
        self.processor.image_processor.post_process_masks.return_value = [self.restored]
        self.model = MagicMock()
        self.model.config._commit_hash = SamConfig().revision
        self.model.config._attn_implementation = "test-only"
        self.model.to.return_value = self.model
        self.outputs = SimpleNamespace(pred_masks=torch.zeros((1, 1, 3, 4, 4)), iou_scores=torch.tensor([[[.5, .9, .7]]]))
        self.model.return_value = self.outputs
        self.factories = (MagicMock(), MagicMock())
        self.factories[0].from_pretrained.return_value = self.processor
        self.factories[1].from_pretrained.return_value = self.model
        patcher = patch("transcreation.stages.segmentation._factories", return_value=self.factories)
        patcher.start();self.addCleanup(patcher.stop)

    def load(self, **overrides):
        kwargs = dict(index=0, research_only=True, note="Explicit synthetic box for a research test")
        kwargs.update(overrides)
        return load_segmentation_input(self.image, self.detection, **kwargs)

    def segment(self):
        return SamSegmenter(SamConfig(device="cpu")).segment(self.request, self.root / "out")

    def test_original_coordinates_and_box_input_dimensions(self):
        self.segment()
        self.assertEqual(self.processor.call_args.kwargs["input_boxes"], [[[10, 5, 80, 50]]])
        self.assertEqual(self.request.original_dimensions, (100, 60))

    def test_restore_exact_original_size(self):
        result = self.segment()
        args = self.processor.image_processor.post_process_masks.call_args
        self.assertEqual(args.args[1].tolist(), [[60, 100]])
        self.assertEqual(args.args[2].tolist(), [[38, 64]])
        self.assertTrue(args.kwargs["binarize"])
        self.assertEqual(result.masks[0].dimensions, (100, 60))

    def test_multiple_masks_and_explicit_visualization_ranking(self):
        result = self.segment()
        self.assertEqual(len(result.masks), 3)
        self.assertEqual(result.visualization_mask_index, 1)
        self.assertEqual(result.masks[0].foreground_pixels, 1250)
        self.assertEqual(result.masks[0].mask_box, (10, 5, 60, 30))

    def test_binary_files_and_source_preservation(self):
        before_image, before_detection = self.image.read_bytes(), self.detection.read_bytes()
        result = self.segment()
        for mask in result.masks:
            with Image.open(self.root / "out" / mask.filename) as image:
                self.assertEqual(image.mode, "L")
                self.assertEqual(image.size, (100, 60))
                self.assertEqual(set(image.tobytes()), {0, 255})
        self.assertEqual(before_image, self.image.read_bytes())
        self.assertEqual(before_detection, self.detection.read_bytes())

    def test_empty_mask_rejected_but_audited(self):
        self.restored[0, 1].zero_()
        result = self.segment()
        self.assertEqual(result.status, "PARTIAL_INVALID")
        self.assertEqual(result.masks[1].status, "REJECTED_EMPTY")
        self.assertNotEqual(result.visualization_mask_index, 1)
        self.assertTrue((self.root / "out/mask_1.png").is_file())

    def test_all_empty_masks_invalid(self):
        self.restored.zero_()
        result = self.segment()
        self.assertEqual(result.status, "INVALID_OUTPUT")
        self.assertIsNone(result.visualization_mask_index)

    def test_unexpected_mask_resolution_rejected(self):
        self.processor.image_processor.post_process_masks.return_value = [torch.ones((1, 3, 30, 50), dtype=torch.bool)]
        result = self.segment()
        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.observations[-1]["code"], "SAM_ERROR")

    def test_nonbinary_tensor_rejected(self):
        for mask in (torch.ones((60, 100)), torch.full((60, 100), 255, dtype=torch.uint8)):
            with self.assertRaises(ValueError):validate_binary_mask(mask, 100, 60)

    def test_index_is_explicit_not_highest_score(self):
        for index in (None, -1, 1, True):
            with self.assertRaises(ValueError):self.load(index=index)

    def test_invalid_box(self):
        data=json.loads(self.detection.read_text());data["detections"][0]["box"]=[-1,0,10,10]
        self.detection.write_text(json.dumps(data))
        with self.assertRaises(ValueError):self.load()

    def test_source_image_hash_mismatch(self):
        self.image.write_bytes(self.image.read_bytes()+b"changed")
        with self.assertRaises(ValueError):self.load()

    def test_explicit_expected_image_hash(self):
        with self.assertRaises(ValueError):self.load(expected_image_sha256="0"*64)

    def test_detection_changed_after_selection(self):
        self.detection.write_bytes(self.detection.read_bytes()+b"\n")
        with self.assertRaises(ValueError):self.segment()
        self.factories[1].from_pretrained.assert_not_called()

    def test_lazy_load_eval_and_pinned_revision(self):
        SamSegmenter(SamConfig())
        self.factories[1].from_pretrained.assert_not_called()
        self.segment()
        self.model.eval.assert_called_once()
        self.assertEqual(self.factories[1].from_pretrained.call_args.kwargs["revision"], SamConfig().revision)

    def test_inference_mode(self):
        def forward(**kwargs):
            self.assertTrue(torch.is_inference_mode_enabled())
            self.assertTrue(kwargs["multimask_output"])
            return self.outputs
        self.model.side_effect = forward
        self.assertEqual(self.segment().status, "SEGMENTED")

    def test_model_loading_error_saved(self):
        self.factories[1].from_pretrained.side_effect=OSError("missing checkpoint")
        result=self.segment()
        self.assertEqual(result.status, "ERROR")
        self.assertIsNone(result.resolved_revision)
        self.assertTrue((self.root / "out/segmentation.json").is_file())

    @patch("transcreation.stages.segmentation.torch.cuda")
    def test_cuda_oom_explicit_cpu_fallback(self, cuda):
        cuda.is_available.return_value=True
        cuda.OutOfMemoryError=torch.OutOfMemoryError
        cuda.max_memory_allocated.return_value=123
        segmenter=SamSegmenter(SamConfig())
        real_load=segmenter._load
        def load(device):
            if device=="cuda":raise torch.OutOfMemoryError("synthetic OOM")
            real_load(device)
        with patch.object(segmenter,"_load",side_effect=load):
            result=segmenter.segment(self.request,self.root/'out')
        self.assertEqual(result.status,"SEGMENTED")
        self.assertEqual(result.memory["effective_device"],"cpu")
        self.assertIn("CUDA_OOM",[issue["code"] for issue in result.observations])
        self.assertEqual(result.memory["failed_cuda_peak_allocated_bytes"],123)

    @patch("transcreation.stages.segmentation.torch.cuda.is_available",return_value=False)
    def test_cuda_unavailable_cpu_fallback(self, available):
        result=SamSegmenter(SamConfig()).segment(self.request,self.root/'out')
        self.assertEqual(result.memory["effective_device"],"cpu")

    def test_research_only_provenance_and_serialization(self):
        result=self.segment()
        data=json.loads(json.dumps(asdict(result),allow_nan=False))
        self.assertEqual(data["request"]["selection_status"],"RESEARCH_ONLY")
        self.assertFalse(data["image_edit_authorized"])
        self.assertFalse(data["cultural_transformation_authorized"])

    def test_editing_request_forbidden(self):
        with self.assertRaises(ValueError):replace(self.request,image_edit_authorized=True)

    def test_planner_outputs_forbidden(self):
        for decision in (PlanningDecision.REVIEW,PlanningDecision.ABSTAIN):
            plan=PlanningResult(decision,"No approval","Scene",(),(),(),())
            self.detection.write_text(json.dumps(asdict(plan)))
            with self.assertRaises(ValueError):self.load()

    def test_research_and_review_mode_not_implicit(self):
        with self.assertRaises(ValueError):self.load(research_only=False)

    def test_pending_review_cannot_be_used_as_acceptance(self):
        pending=prepare(self.detection,self.image,self.root/'review')
        with self.assertRaises(ValueError):self.load(research_only=False,review=pending)

    def test_valid_review_selection_and_hash_binding(self):
        pending=prepare(self.detection,self.image,self.root/'review')
        accepted=pending.with_name('accepted.json')
        decide(pending,accepted,"ACCEPT","synthetic named reviewer","Unit test only",0,True,True)
        request=self.load(research_only=False,review=accepted)
        self.assertEqual(request.selection_status,"REVIEWED_SELECTION")
        self.assertIsNotNone(request.review_sha256)

    def test_placeholder_reviewer_not_claimed_as_confirmed(self):
        pending=prepare(self.detection,self.image,self.root/'review')
        accepted=pending.with_name('accepted.json')
        decide(pending,accepted,"ACCEPT","YOUR_NAME","Unit test only",0,True,True)
        with self.assertRaises(ValueError):self.load(research_only=False,review=accepted)

    def test_no_overwriting_output(self):
        self.segment()
        with self.assertRaises(FileExistsError):self.segment()

    def test_nonfinite_scores_rejected(self):
        self.outputs.iou_scores[0,0,0]=float('nan')
        self.assertEqual(self.segment().status,"ERROR")

    def test_multiple_grounding_detections_require_manual_index(self):
        data=json.loads(self.detection.read_text())
        data['detections'].append({'box':[20,10,40,30],'score':.1,'label':'test object'})
        self.detection.write_text(json.dumps(data))
        request=self.load(index=1)
        self.assertEqual(request.selected_detection.score,.1)
        self.assertEqual(request.prediction_index,1)

    def test_unexpected_processor_box_shape(self):
        self.inputs['input_boxes']=torch.zeros((1,4))
        self.assertEqual(self.segment().status,'ERROR')
        self.model.assert_not_called()

    def test_review_changed_after_selection(self):
        pending=prepare(self.detection,self.image,self.root/'review')
        accepted=pending.with_name('accepted.json')
        decide(pending,accepted,'ACCEPT','synthetic named reviewer','Unit test only',0,True,True)
        request=self.load(research_only=False,review=accepted)
        accepted.write_bytes(accepted.read_bytes()+b'\n')
        with self.assertRaises(ValueError):
            SamSegmenter(SamConfig(device='cpu')).segment(request,self.root/'out')

    def test_config_keeps_initial_precision_and_all_masks(self):
        for fields in ({'precision':'float16'},{'multimask_output':False},{'mask_threshold':True}):
            with self.assertRaises(ValueError):SamConfig(**fields)

    def point_file(self, points=None, **overrides):
        document = {
            'annotation_status': 'RESEARCH_ONLY_REQUIRES_REVIEW',
            'coordinate_system': 'original_image_xy_pixels',
            'source_image_sha256': digest(self.image.read_bytes()),
            'detection_json_sha256': digest(self.detection.read_bytes()),
            'prediction_index': 0, 'target_definition': 'Synthetic target; not ground truth',
            'points': points if points is not None else [{'x':10,'y':5,'label':1},{'x':80,'y':50,'label':0}],
        }
        document.update(overrides)
        path = self.root / 'points.json'
        path.write_text(json.dumps(document), encoding='utf-8')
        return path

    def point_inputs(self):
        self.inputs['input_points'] = torch.tensor([[[[6.4, 3.166667], [51.2, 31.666667]]]])
        self.inputs['input_labels'] = torch.tensor([[[1,0]]])

    def test_point_positive_and_negative_labels(self):
        request = self.load(points_file=self.point_file())
        self.assertEqual([point.label for point in request.points], [1,0])
        self.assertEqual(request.selection_status, 'RESEARCH_ONLY')

    def test_invalid_point_labels(self):
        for label in (-1, 2, True, 1.0, None):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.load(points_file=self.point_file([{'x':10,'y':5,'label':label}]))

    def test_point_coordinate_bounds_and_finite_values(self):
        for x,y in [(-1,0),(100,0),(0,60),(float('nan'),0),(0,float('inf')),(True,5)]:
            with self.subTest(x=x,y=y), self.assertRaises(ValueError):
                self.load(points_file=self.point_file([{'x':x,'y':y,'label':1}]))

    def test_combined_box_and_point_tensor_shapes(self):
        self.request = self.load(points_file=self.point_file())
        self.point_inputs()
        result = self.segment()
        self.assertEqual(result.status, 'SEGMENTED')
        self.assertEqual(self.processor.call_args.kwargs['input_points'], [[[10,5],[80,50]]])
        self.assertEqual(self.processor.call_args.kwargs['input_labels'], [[1,0]])
        self.assertEqual(self.processor.call_args.kwargs['input_boxes'], [[[10,5,80,50]]])
        self.assertEqual(tuple(self.model.call_args.kwargs['input_points'].shape),(1,1,2,2))
        self.assertEqual(tuple(self.model.call_args.kwargs['input_labels'].shape),(1,1,2))

    def test_no_point_call_remains_box_only(self):
        self.segment()
        self.assertNotIn('input_points', self.processor.call_args.kwargs)
        self.assertNotIn('input_labels', self.processor.call_args.kwargs)
        self.assertNotIn('input_points', self.model.call_args.kwargs)
        self.assertNotIn('input_labels', self.model.call_args.kwargs)
        self.assertEqual(self.request.points, ())

    def test_empty_point_list_does_not_send_empty_sam_tensors(self):
        self.request = self.load(points_file=self.point_file([]))
        self.assertEqual(self.segment().status, 'SEGMENTED')
        self.assertNotIn('input_points', self.model.call_args.kwargs)

    def test_point_provenance_serialization_and_pre_forward_preview(self):
        path = self.point_file()
        source_before, detection_before = self.image.read_bytes(), self.detection.read_bytes()
        self.request = self.load(points_file=path)
        self.point_inputs()
        def forward(**kwargs):
            self.assertTrue((self.root/'out/points.png').is_file())
            self.assertEqual((self.root/'out/points.json').read_bytes(),path.read_bytes())
            return self.outputs
        self.model.side_effect = forward
        result = self.segment()
        data = json.loads(json.dumps(asdict(result)))
        self.assertEqual(data['request']['points'][0]['label'],1)
        self.assertEqual(data['request']['point_prompt_sha256'],digest(path.read_bytes()))
        self.assertEqual(data['settings']['point_annotation_status'],'RESEARCH_ONLY_REQUIRES_REVIEW')
        self.assertEqual(source_before,self.image.read_bytes())
        self.assertEqual(detection_before,self.detection.read_bytes())

    def test_changed_point_file_rejected_before_loading(self):
        path=self.point_file();self.request=self.load(points_file=path)
        path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaises(ValueError):self.segment()
        self.factories[1].from_pretrained.assert_not_called()

    def test_point_document_bound_to_image_detection_and_index(self):
        for fields in ({'source_image_sha256':'0'*64},{'detection_json_sha256':'0'*64},{'prediction_index':1}):
            with self.assertRaises(ValueError):self.load(points_file=self.point_file(**fields))

    def test_points_cannot_claim_box_review_approval(self):
        path=self.point_file()
        with self.assertRaises(ValueError):
            replace(self.request,selection_status='REVIEWED_SELECTION',review_file='review.json',review_sha256='a'*64,
                    points=(SamPoint(10,5,1),),point_prompt_file=str(path),point_prompt_sha256=digest(path.read_bytes()))
        with self.assertRaises(ValueError):
            self.load(points_file=self.point_file(annotation_status='HUMAN_APPROVED'))

    def test_bad_point_tensor_dimensions_or_labels_rejected(self):
        self.request=self.load(points_file=self.point_file());self.point_inputs()
        self.inputs['input_labels']=torch.tensor([[1,0]])
        self.assertEqual(self.segment().status,'ERROR')
        self.model.assert_not_called()

    def test_installed_processor_transforms_points_without_weights(self):
        from transformers import SamImageProcessor, SamProcessor
        processor=SamProcessor(image_processor=SamImageProcessor(size={'longest_edge':64},pad_size={'height':64,'width':64}))
        with Image.open(self.image) as image:
            inputs=processor(images=image,input_boxes=[[[10,5,80,50]]],input_points=[[[10,5],[80,50]]],input_labels=[[1,0]],return_tensors='pt')
        self.assertEqual(tuple(inputs['input_points'].shape),(1,1,2,2))
        self.assertEqual(tuple(inputs['input_labels'].shape),(1,1,2))
        self.assertAlmostEqual(float(inputs['input_points'][0,0,0,0]),6.4,places=4)
        self.assertAlmostEqual(float(inputs['input_points'][0,0,0,1]),5*38/60,places=4)

    def test_cli_point_file_option_offline(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from scripts.segment_sam import main
        path=self.point_file();self.point_inputs()
        config=self.root/'sam.yaml';config.write_text('model_id: facebook/sam-vit-base\n')
        out=self.root/'cli_out'
        with redirect_stdout(StringIO()):
            main(['--image',str(self.image),'--detection',str(self.detection),'--prediction-index','0',
                  '--research-only','--points',str(path),'--note','synthetic points only',
                  '--device','cpu','--config',str(config),'--out',str(out)])
        self.assertEqual(json.loads((out/'segmentation.json').read_text())['request']['points'][1]['label'],0)
