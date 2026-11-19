"""Synthetic reviewer declarations in tests are not actual human confirmations."""
from dataclasses import asdict
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts.review_grounding import decide, digest, main, prepare, read_candidate
from transcreation.contracts import GroundingDetection, GroundingResult, PlanningDecision, PlanningResult


class GroundingReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "image.png"
        Image.new("RGB", (100, 60), "white").save(self.image)
        self.source = self.root / "detection.json"
        self.result = GroundingResult(digest(self.image.read_bytes()), (100, 60), "test object",
                                      "test-only-model", "a" * 40, "DETECTED",
                                      (GroundingDetection((0, 0, 20, 20), .9, "test object"),
                                       GroundingDetection((30, 10, 60, 40), .5, "test object")),
                                      {}, {}, {}, {})
        self.write_source()
        self.request = prepare(self.source, self.image, self.root / "review")
        self.out = self.request.with_name("decision.json")

    def write_source(self):
        self.source.write_text(json.dumps(asdict(self.result)), encoding="utf-8")

    def accept(self, **kwargs):
        values = dict(index=1, inspected_original=True, inspected_boxes=True)
        values.update(kwargs)
        return decide(self.request, self.out, "ACCEPT", "synthetic test reviewer", "Synthetic test declaration only", **values)

    def mutate(self, path, change):
        record = json.loads(path.read_text())
        change(record)
        path.write_text(json.dumps(record), encoding="utf-8")

    def test_accept_valid_explicit_lower_scoring_box(self):
        record = self.accept()
        self.assertEqual(record["selected_prediction_index"], 1)
        self.assertEqual(record["selected_prediction"]["score"], .5)
        self.assertEqual(read_candidate(self.out), self.result.detections[1])
        self.assertEqual(record["candidate_kind"], "reviewed segmentation-test candidate")

    def test_reject_incorrect_query_prediction(self):
        # Geometric validity cannot diagnose semantics; the synthetic reviewer rejects.
        record = decide(self.request, self.out, "REJECT", "synthetic reviewer", "Query does not match the visible object")
        self.assertIsNone(record["selected_prediction"])
        self.assertIsNone(record["candidate_kind"])
        with self.assertRaises(ValueError):
            read_candidate(self.out)

    def test_no_detection_rejection(self):
        from dataclasses import replace
        self.result = replace(self.result, status="NO_DETECTIONS", detections=())
        self.write_source()
        request = prepare(self.source, self.image, self.root / "empty")
        record = decide(request, request.with_name("reject.json"), "REJECT", "synthetic reviewer", "No detected object")
        self.assertIsNone(record["selected_prediction"])

    def test_no_detection_cannot_accept(self):
        from dataclasses import replace
        self.result = replace(self.result, status="NO_DETECTIONS", detections=())
        self.write_source()
        request = prepare(self.source, self.image, self.root / "empty")
        with self.assertRaises(ValueError):
            decide(request, request.with_name("accept.json"), "ACCEPT", "test", "test", 0, True, True)

    def test_invalid_prediction_index(self):
        for index in (-1, 2, True, 1.0):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.accept(index=index)
        self.assertFalse(self.out.exists())

    def test_multiple_detections_require_explicit_selection(self):
        with self.assertRaises(ValueError):
            self.accept(index=None)

    def test_single_detection_still_requires_index(self):
        from dataclasses import replace
        self.result = replace(self.result, detections=self.result.detections[:1])
        self.write_source()
        request = prepare(self.source, self.image, self.root / "single")
        with self.assertRaises(ValueError):
            decide(request, request.with_name("accept.json"), "ACCEPT", "test", "test", None, True, True)

    def test_modified_source_image_hash(self):
        bound_image = self.request.parent / "original.png"
        bound_image.write_bytes(bound_image.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.accept()

    def test_changed_input_before_preparation(self):
        self.image.write_bytes(self.image.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            prepare(self.source, self.image, self.root / "changed")

    def test_modified_detection_file_hash_even_for_whitespace(self):
        bound = self.request.parent / "detection.json"
        bound.write_bytes(bound.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.accept()

    def test_modified_annotation_hash(self):
        bound = self.request.parent / "annotated.png"
        bound.write_bytes(bound.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.accept()

    def test_inspection_declarations_required(self):
        for flags in ({"inspected_original": False}, {"inspected_boxes": False}):
            with self.assertRaises(ValueError):
                self.accept(**flags)

    def test_human_details_required(self):
        for name, reason in (("", "reason"), ("reviewer", " ")):
            with self.assertRaises(ValueError):
                decide(self.request, self.out, "ACCEPT", name, reason, 0, True, True)

    def test_pending_has_no_fabricated_confirmation(self):
        record = json.loads(self.request.read_text())
        self.assertEqual(record["decision"], "PENDING")
        for field in ("selected_prediction_index", "selected_prediction", "reviewer", "reviewed_at_utc", "candidate_kind"):
            self.assertIsNone(record[field])
        self.assertFalse(record["inspected_original"])
        self.assertFalse(record["inspected_boxes"])
        with self.assertRaises(ValueError):
            read_candidate(self.request)

    def test_needs_review_releases_nothing(self):
        record = decide(self.request, self.out, "NEEDS_REVIEW", "synthetic reviewer", "Identity is unresolved")
        self.assertIsNone(record["selected_prediction"])
        with self.assertRaises(ValueError):
            read_candidate(self.out)

    def test_nonaccept_cannot_select(self):
        for decision in ("REJECT", "NEEDS_REVIEW"):
            with self.assertRaises(ValueError):
                decide(self.request, self.out, decision, "test", "test", 0)

    def test_no_editing_authorization(self):
        record = self.accept()
        self.assertIs(record["image_edit_authorized"], False)
        self.assertIs(record["cultural_transformation_authorized"], False)
        self.mutate(self.out, lambda r: r.update(image_edit_authorized=True))
        with self.assertRaises(ValueError):
            read_candidate(self.out)

    def test_modified_selected_box_rejected(self):
        self.accept()
        self.mutate(self.out, lambda r: r["selected_prediction"]["box"].__setitem__(0, 31))
        with self.assertRaisesRegex(ValueError, "differs"):
            read_candidate(self.out)

    def test_modified_selected_score_and_label_rejected(self):
        self.accept()
        original = self.out.read_bytes()
        for fields in ({"score": .99}, {"label": "different"}):
            self.out.write_bytes(original)
            self.mutate(self.out, lambda r: r["selected_prediction"].update(fields))
            with self.assertRaisesRegex(ValueError, "differs"):
                read_candidate(self.out)

    def test_changed_request_breaks_audit_chain(self):
        self.accept()
        self.request.write_bytes(self.request.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "source review request"):
            read_candidate(self.out)

    def test_metadata_must_match_evidence(self):
        self.mutate(self.request, lambda r: r.update(source_phrase="other query"))
        with self.assertRaisesRegex(ValueError, "metadata"):
            self.accept()

    def test_serialization_and_source_audit_preserved(self):
        source_before = self.source.read_bytes()
        request_before = self.request.read_bytes()
        record = self.accept()
        self.assertEqual(record, json.loads(self.out.read_text()))
        self.assertEqual(source_before, self.source.read_bytes())
        self.assertEqual(request_before, self.request.read_bytes())
        self.assertEqual(record["detection_json_sha256"], hashlib.sha256(source_before).hexdigest())
        self.assertEqual(len(json.loads((self.request.parent / "detection.json").read_text())["detections"]), 2)

    def test_existing_outputs_are_not_overwritten(self):
        self.accept()
        before = self.out.read_bytes()
        with self.assertRaises(FileExistsError):
            self.accept()
        self.assertEqual(before, self.out.read_bytes())
        with self.assertRaises(FileExistsError):
            prepare(self.source, self.image, self.request.parent)

    def test_invalid_coordinates_and_dimensions(self):
        for values in ({"detections": [{"box": [-1, 0, 10, 10], "score": .5, "label": "test"}]},
                       {"original_dimensions": [101, 60]}):
            self.write_source()
            self.mutate(self.source, lambda r: r.update(values))
            with self.assertRaises(ValueError):
                prepare(self.source, self.image, self.root / "bad")

    def test_planner_review_abstain_are_not_box_acceptance(self):
        for decision in (PlanningDecision.REVIEW, PlanningDecision.ABSTAIN):
            plan = PlanningResult(decision, "No approval", "Original scene", (), (), (), ())
            path = self.root / f"{decision.value}.json"
            path.write_text(json.dumps(asdict(plan)), encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare(path, self.image, self.root / "planner")

    def test_cli_prepare_is_pending(self):
        directory = self.root / "cli"
        with redirect_stdout(StringIO()):
            main(["prepare", "--detection", str(self.source), "--image", str(self.image), "--out", str(directory)])
        self.assertEqual(json.loads((directory / "pending.json").read_text())["decision"], "PENDING")

    def test_cli_accept_requires_explicit_index(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            main(["decide", "--request", str(self.request), "--decision", "ACCEPT", "--reviewer", "test",
                  "--reason", "test", "--inspected-original", "--inspected-boxes", "--out", str(self.out)])
        self.assertEqual(caught.exception.code, 2)

    def test_invalid_output_status_cannot_release_candidate(self):
        from dataclasses import replace
        self.result = replace(self.result, status="INVALID_OUTPUT")
        self.write_source()
        request = prepare(self.source, self.image, self.root / "invalid_output")
        with self.assertRaises(ValueError):
            decide(request, request.with_name("accept.json"), "ACCEPT", "test", "test", 0, True, True)

    def test_malformed_json_and_schema(self):
        for data in (b'{', b'[]', b'{"decision":"ACCEPT"}', b'{"value":NaN}'):
            self.source.write_bytes(data)
            with self.assertRaises(ValueError):
                prepare(self.source, self.image, self.root / "malformed")

    def test_decisions_are_immutable_new_records(self):
        self.accept()
        with self.assertRaises(ValueError):
            decide(self.out, self.out.with_name("changed.json"), "REJECT", "test", "test")

    def test_review_output_stays_with_bound_evidence(self):
        with self.assertRaisesRegex(ValueError, "alongside"):
            decide(self.request, self.root / "detached.json", "REJECT", "test", "test")
