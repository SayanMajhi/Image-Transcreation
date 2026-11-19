"""Human review of saved boxes only. Never grants image-edit authorization."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from transcreation.contracts import GroundingDetection, GroundingResult


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _invalid_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def _json(data: bytes) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8-sig"), parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _evidence(image_bytes: bytes, detection_bytes: bytes) -> tuple[GroundingResult, Image.Image]:
    try:
        data = _json(detection_bytes)
        data["detections"] = tuple(GroundingDetection(**{**item, "box": tuple(item["box"])})
                                   for item in data["detections"])
        result = GroundingResult(**data)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid saved detection schema: {exc}") from exc
    if digest(image_bytes) != result.image_sha256:
        raise ValueError("source image SHA-256 does not match detection evidence")
    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")
    if image.size != tuple(result.original_dimensions):
        raise ValueError("image dimensions do not match detection evidence")
    if any(not isinstance(value, str) or not value.strip()
           for value in (result.source_phrase, result.model_id, result.resolved_revision)):
        raise ValueError("saved detection must identify its phrase, model and revision")
    return result, image


def _metadata(result: GroundingResult) -> dict[str, Any]:
    return {"original_image_sha256": result.image_sha256,
            "original_dimensions": list(result.original_dimensions),
            "source_phrase": result.source_phrase, "model_id": result.model_id,
            "model_revision": result.resolved_revision, "prediction_count": len(result.detections)}


def _write(path: Path, record: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(record, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")


def prepare(detection: Path, image: Path, out: Path) -> Path:
    """Bind exact saved evidence and generate a zero-based preview; always PENDING."""
    image_bytes, detection_bytes = image.read_bytes(), detection.read_bytes()
    result, original = _evidence(image_bytes, detection_bytes)
    out.mkdir(parents=True, exist_ok=False)
    image_name = "original" + (image.suffix.lower() or ".img")
    (out / image_name).write_bytes(image_bytes)
    (out / "detection.json").write_bytes(detection_bytes)
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    for index, prediction in enumerate(result.detections):
        draw.rectangle(prediction.box, outline="red", width=3)
        draw.text((prediction.box[0] + 3, prediction.box[1] + 3),
                  f"index {index}: {prediction.label or '<empty label>'} {prediction.score:.3f}",
                  fill="red", stroke_width=1, stroke_fill="white")
    annotated.save(out / "annotated.png")
    record = {"schema_version": 1, "record_type": "grounding_box_human_review",
              **_metadata(result), "detection_json_sha256": digest(detection_bytes),
              "annotation_sha256": digest((out / "annotated.png").read_bytes()),
              "image_file": image_name, "detection_file": "detection.json", "annotation_file": "annotated.png",
              "prediction_indexing": "zero_based_detections_array", "decision": "PENDING",
              "selected_prediction_index": None, "selected_prediction": None, "candidate_kind": None,
              "reviewer": None, "explanation": "Awaiting explicit human review; no selection has been made.",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "reviewed_at_utc": None,
              "inspected_original": False, "inspected_boxes": False,
              "image_edit_authorized": False, "cultural_transformation_authorized": False}
    path = out / "pending.json"
    _write(path, record)
    return path


def _checked_evidence(record: dict[str, Any], folder: Path) -> GroundingResult:
    if record.get("record_type") != "grounding_box_human_review" or record.get("schema_version") != 1:
        raise ValueError("not a grounding human-review record")
    if record.get("image_edit_authorized") is not False or record.get("cultural_transformation_authorized") is not False:
        raise ValueError("a box review cannot grant editing authorization")
    if record.get("prediction_indexing") != "zero_based_detections_array":
        raise ValueError("unknown prediction indexing convention")
    contents = {}
    for key, hash_key in (("image_file", "original_image_sha256"),
                          ("detection_file", "detection_json_sha256"),
                          ("annotation_file", "annotation_sha256")):
        name = record.get(key)
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("review evidence must be a file alongside the review record")
        contents[key] = (folder / name).read_bytes()
        if digest(contents[key]) != record.get(hash_key):
            raise ValueError(f"{key} SHA-256 mismatch")
    result, _ = _evidence(contents["image_file"], contents["detection_file"])
    if any(record.get(key) != value for key, value in _metadata(result).items()):
        raise ValueError("review metadata does not match recorded predictions")
    return result


def _selected(result: GroundingResult, index: int | None) -> dict[str, Any]:
    if result.status != "DETECTED" or not result.detections:
        raise ValueError("ACCEPT requires a successful result containing detections")
    if type(index) is not int or not 0 <= index < len(result.detections):
        raise ValueError("ACCEPT requires an explicit valid zero-based prediction index")
    prediction = result.detections[index]
    prediction.validate(*result.original_dimensions)
    return {**asdict(prediction), "box": list(prediction.box)}


def read_candidate(path: Path) -> GroundingDetection:
    """Revalidate an ACCEPT record for a segmentation test, never for image editing."""
    record = _json(path.read_bytes())
    result = _checked_evidence(record, path.parent)
    if record.get("decision") != "ACCEPT" or record.get("candidate_kind") != "reviewed segmentation-test candidate":
        raise ValueError("only ACCEPT releases a reviewed segmentation-test candidate")
    if record.get("inspected_original") is not True or record.get("inspected_boxes") is not True:
        raise ValueError("acceptance requires human inspection of original and annotated boxes")
    if any(not isinstance(record.get(key), str) or not record[key].strip()
           for key in ("reviewer", "explanation", "reviewed_at_utc")):
        raise ValueError("acceptance requires reviewer, explanation and review timestamp")
    if datetime.fromisoformat(record["reviewed_at_utc"]).utcoffset() is None:
        raise ValueError("review timestamp requires a timezone")
    expected = _selected(result, record.get("selected_prediction_index"))
    if record.get("selected_prediction") != expected:
        raise ValueError("selected box/score/label differs from the indexed recorded prediction")
    request_name = record.get("source_request_file")
    if not isinstance(request_name, str) or Path(request_name).name != request_name:
        raise ValueError("source request must be alongside the review record")
    if digest((path.parent / request_name).read_bytes()) != record.get("source_request_sha256"):
        raise ValueError("source review request SHA-256 mismatch")
    return GroundingDetection(tuple(expected["box"]), expected["score"], expected["label"])


def decide(request: Path, out: Path, decision: str, reviewer: str, explanation: str,
           index: int | None = None, inspected_original: bool = False, inspected_boxes: bool = False) -> dict[str, Any]:
    """Record an explicit human declaration. Callers must not fabricate confirmations."""
    request_bytes = request.read_bytes()
    record = _json(request_bytes)
    result = _checked_evidence(record, request.parent)
    if (record.get("decision") != "PENDING" or record.get("selected_prediction") is not None
            or record.get("selected_prediction_index") is not None or record.get("candidate_kind") is not None):
        raise ValueError("start from an unselected PENDING request; existing decisions are immutable")
    if out.parent.resolve() != request.parent.resolve():
        raise ValueError("save the decision alongside its request to preserve portable evidence links")
    if decision not in ("ACCEPT", "REJECT", "NEEDS_REVIEW"):
        raise ValueError("choose ACCEPT, REJECT or NEEDS_REVIEW")
    if any(not isinstance(value, str) or not value.strip() for value in (reviewer, explanation)):
        raise ValueError("a human decision requires a reviewer name and explanation")
    selected = None
    if decision == "ACCEPT":
        if inspected_original is not True or inspected_boxes is not True:
            raise ValueError("inspect original and annotated boxes before accepting")
        selected = _selected(result, index)
    elif index is not None:
        raise ValueError("only ACCEPT selects a prediction; other decisions release no candidate")
    record.update(decision=decision, reviewer=reviewer.strip(), explanation=explanation.strip(),
                  reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                  inspected_original=inspected_original, inspected_boxes=inspected_boxes,
                  selected_prediction_index=index, selected_prediction=selected,
                  candidate_kind="reviewed segmentation-test candidate" if selected else None,
                  source_request_file=request.name, source_request_sha256=digest(request_bytes))
    # _selected validates original coordinates and copies the indexed prediction exactly.
    # No custom coordinates or score-based default selection are accepted.
    _write(out, record)
    return record


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="Create evidence copies, indexed preview and PENDING request")
    prepare_parser.add_argument("--detection", type=Path, required=True)
    prepare_parser.add_argument("--image", type=Path, required=True)
    prepare_parser.add_argument("--out", type=Path, required=True, help="New directory only")
    decision_parser = commands.add_parser("decide", help="Record a real human decision; never use for automated approval")
    decision_parser.add_argument("--request", type=Path, required=True)
    decision_parser.add_argument("--decision", choices=("ACCEPT", "REJECT", "NEEDS_REVIEW"), required=True)
    decision_parser.add_argument("--reviewer", required=True)
    decision_parser.add_argument("--reason", required=True)
    decision_parser.add_argument("--index", type=int, help="Required for ACCEPT: zero-based detections array index")
    decision_parser.add_argument("--inspected-original", action="store_true")
    decision_parser.add_argument("--inspected-boxes", action="store_true")
    decision_parser.add_argument("--out", type=Path, required=True, help="New JSON alongside the request")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            print(prepare(args.detection, args.image, args.out))
        else:
            record = decide(args.request, args.out, args.decision, args.reviewer, args.reason,
                            args.index, args.inspected_original, args.inspected_boxes)
            print(f"{record['decision']}; image editing remains unauthorized; saved {args.out}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
