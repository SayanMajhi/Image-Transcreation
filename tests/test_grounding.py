"""Offline localization tests: no weights or network required."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
import torch

from transcreation.config import GroundingConfig
from transcreation.contracts import GroundingDetection, PlanningDecision, PlanningResult
from transcreation.stages.grounding import GroundingDetector, save_grounding_artifacts, validate_phrase


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "source.png"
        Image.new("RGB", (100, 60), "white").save(self.image)
        self.processor = MagicMock()
        self.inputs = {"input_ids": torch.tensor([[1]])}
        self.processor.return_value.to.return_value = self.inputs
        self.processor.image_processor.to_dict.return_value = {"test": True}
        self.predictions = {"boxes": torch.tensor([[10., 5., 80., 50.]]),
                            "scores": torch.tensor([.8]), "text_labels": ["bicycle"]}
        self.processor.post_process_grounded_object_detection.return_value = [self.predictions]
        self.model = MagicMock()
        self.model.config._commit_hash = GroundingConfig().revision
        self.model.to.return_value = self.model
        factories = (MagicMock(), MagicMock())
        factories[0].from_pretrained.return_value = self.processor
        factories[1].from_pretrained.return_value = self.model
        self.factories = factories
        patcher = patch("transcreation.stages.grounding._factories", return_value=factories)
        patcher.start()
        self.addCleanup(patcher.stop)

    def detect(self):
        return GroundingDetector(GroundingConfig(device="cpu")).detect(self.image, "bicycle")

    def test_dimensions_and_postprocessing_signature(self):
        result = self.detect()
        self.assertEqual(result.original_dimensions, (100, 60))
        kwargs = self.processor.post_process_grounded_object_detection.call_args.kwargs
        self.assertEqual(kwargs["target_sizes"], [(60, 100)])
        self.assertEqual(kwargs["threshold"], .30)
        self.assertNotIn("box_threshold", kwargs)

    def test_valid_box(self):
        self.assertEqual(self.detect().detections[0].box, (10, 5, 80, 50))

    def test_invalid_coordinates(self):
        for box in ((10, 5, 9, 50), (0, 0, float("nan"), 10), (0, 0, float("inf"), 10)):
            with self.subTest(box=box), self.assertRaises(ValueError):
                GroundingDetection(box, .8, "object").validate(100, 60)

    def test_out_of_bounds(self):
        for box in ((-1, 0, 10, 10), (0, 0, 101, 10), (0, 0, 10, 61)):
            with self.subTest(box=box), self.assertRaises(ValueError):
                GroundingDetection(box, .8, "object").validate(100, 60)

    def test_invalid_score(self):
        for score in (-.1, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                GroundingDetection((0, 0, 10, 10), score, "object").validate(100, 60)

    def test_no_detections(self):
        self.predictions.update(boxes=torch.empty((0, 4)), scores=torch.empty(0), text_labels=[])
        self.assertEqual(self.detect().status, "NO_DETECTIONS")

    def test_multiple_detections(self):
        self.predictions.update(boxes=torch.tensor([[0., 0., 10., 10.], [20., 20., 30., 30.]]),
                                scores=torch.tensor([.8, .7]), text_labels=["lamp", "lamp"])
        self.assertEqual(len(self.detect().detections), 2)

    def test_invalid_predictions_quarantined(self):
        self.predictions["boxes"] = torch.tensor([[-1., 0., 10., 10.]])
        result = self.detect()
        self.assertEqual(result.status, "INVALID_OUTPUT")
        self.assertEqual(result.detections, ())
        self.assertEqual(result.raw_predictions["boxes"][0][0], -1)

    def test_nonfinite_predictions_have_serializable_audit(self):
        self.predictions["boxes"] = torch.tensor([[0., 0., float("nan"), 10.]])
        result = self.detect()
        self.assertEqual(result.status, "INVALID_OUTPUT")
        json.dumps(asdict(result), allow_nan=False)
        self.assertEqual(result.raw_predictions["boxes"][0][2], "nan")

    def test_invalid_dimensions(self):
        from dataclasses import replace
        with self.assertRaises(ValueError):
            replace(self.detect(), original_dimensions=(0, 60))

    @patch("transcreation.stages.grounding.torch.cuda.is_available", return_value=False)
    def test_cuda_unavailable_fallback(self, available):
        result = GroundingDetector(GroundingConfig()).detect(self.image, "bicycle")
        self.assertEqual(result.status, "DETECTED")
        self.assertEqual(result.memory["device"], "cpu")

    @patch("transcreation.stages.grounding.torch.cuda.is_available", return_value=False)
    def test_cuda_unavailable_without_fallback(self, available):
        result = GroundingDetector(GroundingConfig(cpu_fallback=False)).detect(self.image, "bicycle")
        self.assertEqual(result.status, "ERROR")

    def test_invalid_queries(self):
        for phrase in ("", " ", "null", "None", "N/A", ".", 123):
            with self.subTest(phrase=phrase), self.assertRaises(ValueError):
                validate_phrase(phrase)

    def test_rejected_plans_are_not_inputs(self):
        for decision in (PlanningDecision.REVIEW, PlanningDecision.ABSTAIN):
            plan = PlanningResult(decision, "Not approved", "Original bicycle scene", (), (), (), ())
            for unsupported in (plan, {"decision": decision, "localization_phrase": "bicycle"}):
                with self.assertRaises(ValueError):
                    GroundingDetector(GroundingConfig()).detect(self.image, unsupported)
        self.factories[0].from_pretrained.assert_not_called()

    def test_json_serialization(self):
        encoded = json.loads(json.dumps(asdict(self.detect()), allow_nan=False))
        self.assertEqual(encoded["detections"][0]["box"], [10, 5, 80, 50])
        self.assertTrue(encoded["research_only"])

    def test_visualization_and_source_protection(self):
        before = hashlib.sha256(self.image.read_bytes()).hexdigest()
        out = Path(self.temp.name) / "artifacts"
        save_grounding_artifacts(self.image, self.detect(), out)
        with Image.open(out / "comparison.png") as comparison:
            self.assertEqual(comparison.size, (200, 100))
        self.assertEqual(before, hashlib.sha256(self.image.read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            save_grounding_artifacts(self.image, self.detect(), out)

    def test_lazy_pinned_model_load(self):
        GroundingDetector(GroundingConfig(device="cpu"))
        self.factories[1].from_pretrained.assert_not_called()
        self.detect()
        self.model.eval.assert_called_once()
        kwargs = self.factories[1].from_pretrained.call_args.kwargs
        self.assertEqual(kwargs["revision"], GroundingConfig().revision)
        self.assertTrue(kwargs["disable_custom_kernels"])

    def test_inference_mode(self):
        self.model.side_effect = lambda **kwargs: self.assertTrue(torch.is_inference_mode_enabled())
        self.assertEqual(self.detect().status, "DETECTED")

    def test_model_loading_error(self):
        self.factories[1].from_pretrained.side_effect = OSError("missing weights")
        result = self.detect()
        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.observations[-1]["code"], "GROUNDING_ERROR")

    def test_revision_mismatch(self):
        self.model.config._commit_hash = "incorrect"
        self.assertEqual(self.detect().status, "ERROR")

    @patch("transcreation.stages.grounding.torch.cuda")
    def test_cuda_oom_cpu_retry(self, cuda):
        cuda.is_available.return_value = True
        detector = GroundingDetector(GroundingConfig())
        real_load = detector._load
        def load(device):
            if device == "cuda":
                raise torch.cuda.OutOfMemoryError("mock OOM")
            real_load(device)
        # Keep the actual exception class when mocking the CUDA namespace.
        cuda.OutOfMemoryError = torch.OutOfMemoryError
        with patch.object(detector, "_load", side_effect=load):
            result = detector.detect(self.image, "bicycle")
        self.assertEqual(result.status, "DETECTED")
        self.assertEqual(result.memory["device"], "cpu")
        self.assertEqual(result.observations[0]["code"], "CUDA_OOM")

    @patch("transcreation.stages.grounding.torch.cuda")
    def test_cuda_error_is_explicit(self, cuda):
        cuda.is_available.return_value = True
        cuda.OutOfMemoryError = torch.OutOfMemoryError
        cuda.max_memory_allocated.return_value = 0
        detector = GroundingDetector(GroundingConfig())
        with patch.object(detector, "_load", side_effect=RuntimeError("CUDA failure")):
            result = detector.detect(self.image, "bicycle")
        self.assertEqual(result.status, "ERROR")

    def test_threshold_validation(self):
        for threshold in (-1, 2, float("nan"), True):
            with self.assertRaises(ValueError):
                GroundingConfig(box_threshold=threshold)
