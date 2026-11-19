"""Review saved SAM masks for controlled segmentation tests, never for editing."""
import argparse
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from scripts.review_grounding import digest, _json, _evidence, _write
from transcreation.contracts import GroundingDetection, SamPoint, SegmentationInput, SegmentationMask, SegmentationResult

ACCEPT = "ACCEPT_FOR_SEGMENTATION_TEST"
KIND = "reviewed mask for controlled segmentation test"


def _local(folder: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError("review evidence must be a local file alongside its segmentation result")
    return folder / name


def _parse_result(raw: bytes) -> SegmentationResult:
    try:
        data = _json(raw)
        request = data["request"]
        request["original_dimensions"] = tuple(request["original_dimensions"])
        request["selected_detection"] = GroundingDetection(**{**request["selected_detection"],
                                                               "box": tuple(request["selected_detection"]["box"])})
        request["points"] = tuple(SamPoint(**point) for point in request.get("points", []))
        data["request"] = SegmentationInput(**request)
        data["masks"] = tuple(SegmentationMask(**{**mask, "dimensions": tuple(mask["dimensions"]),
                                                   "mask_box": tuple(mask["mask_box"]) if mask["mask_box"] else None})
                              for mask in data["masks"])
        result = SegmentationResult(**data)
        if not isinstance(result.settings, dict):
            raise ValueError("segmentation settings must be a JSON object")
        return result
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid saved segmentation contract: {exc}") from exc


def _bundle(path: Path) -> tuple[SegmentationResult, dict[str, bytes]]:
    """Validate portable saved artifacts without following old project paths."""
    raw = path.read_bytes()
    result = _parse_result(raw)
    if (result.status != "SEGMENTED" or not isinstance(result.resolved_revision, str) or not result.resolved_revision.strip()
            or not isinstance(result.model_id, str) or not result.model_id.strip()):
        raise ValueError("review requires a successfully completed segmentation result")
    request, settings = result.request, result.settings
    if result.model_id != settings.get("model_id") or result.resolved_revision != settings.get("revision"):
        raise ValueError("SAM model/revision metadata is inconsistent")
    payload = {path.name: raw}

    def read(name: str) -> bytes:
        data = _local(path.parent, name).read_bytes()
        payload[name] = data
        return data

    image_bytes = read(settings["source_image_copy"])
    detection_bytes = read(settings["source_detection_copy"])
    grounding, original = _evidence(image_bytes, detection_bytes)
    if digest(image_bytes) != request.image_sha256 or digest(detection_bytes) != request.detection_sha256:
        raise ValueError("source image/detection hash mismatch")
    if original.size != request.original_dimensions:
        raise ValueError("source image dimensions differ from segmentation input")
    if (grounding.status != "DETECTED" or not 0 <= request.prediction_index < len(grounding.detections)
            or grounding.detections[request.prediction_index] != request.selected_detection
            or grounding.model_id != request.grounding_model_id or grounding.resolved_revision != request.grounding_revision
            or grounding.source_phrase != request.source_phrase):
        raise ValueError("source grounding prediction/provenance does not match segmentation")
    if request.point_prompt_file:
        point_bytes = read(settings["point_prompt_copy"])
        document = _json(point_bytes)
        if (digest(point_bytes) != request.point_prompt_sha256
                or document.get("annotation_status") != "RESEARCH_ONLY_REQUIRES_REVIEW"
                or document.get("coordinate_system") != "original_image_xy_pixels"
                or document.get("source_image_sha256") != request.image_sha256
                or document.get("detection_json_sha256") != request.detection_sha256
                or type(document.get("prediction_index")) is not int
                or document["prediction_index"] != request.prediction_index
                or tuple(SamPoint(**point) for point in document["points"]) != request.points):
            raise ValueError("point document hash or provenance mismatch")
        with Image.open(BytesIO(read(settings["point_preview"]))) as image:
            image.load()
            if image.size != request.original_dimensions:
                raise ValueError("point preview dimensions are inconsistent")
    indices = [mask.index for mask in result.masks]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate SAM candidate indices are ambiguous")
    for mask in result.masks:
        binary = read(mask.filename)
        with Image.open(BytesIO(binary)) as image:
            if image.format != "PNG" or image.mode != "L" or image.size != request.original_dimensions:
                raise ValueError("mask must be an original-resolution grayscale PNG")
            if not set(image.tobytes()).issubset({0, 255}):
                raise ValueError("mask PNG values must be 0 or 255")
            if (mask.status != "VALID" or mask.dimensions != image.size or not mask.foreground_pixels
                    or image.histogram()[255] != mask.foreground_pixels or image.getbbox() != mask.mask_box):
                raise ValueError("mask dimensions/foreground count/bounds disagree with segmentation record")
        overlay = read(f"overlay_{mask.index}.png")
        with Image.open(BytesIO(overlay)) as image:
            image.load()
            if image.size != request.original_dimensions or image.mode not in ("RGB", "RGBA"):
                raise ValueError("overlay dimensions or color mode are inconsistent")
    with Image.open(BytesIO(read("box.png"))) as image:
        image.load()
        if image.size != request.original_dimensions:
            raise ValueError("box preview dimensions are inconsistent")
    return result, payload


def _candidate(result: SegmentationResult, index: int | None) -> SegmentationMask:
    if type(index) is not int:
        raise ValueError("supply one explicit integer SAM candidate index")
    matches = [mask for mask in result.masks if mask.index == index]
    if len(matches) != 1:
        raise ValueError("SAM candidate index does not exist or is ambiguous")
    return matches[0]


def _snapshot(result: SegmentationResult, payload: dict[str, bytes], segmentation_file: str,
              index: int, target: str, experiment: str) -> dict[str, Any]:
    if any(not isinstance(value, str) or not value.strip() for value in (target, experiment)):
        raise ValueError("specify the target and controlled segmentation experiment")
    mask = _candidate(result, index)
    request = result.request
    return {"segmentation_file": segmentation_file, "source_image_sha256": request.image_sha256,
            "detection_json_sha256": request.detection_sha256,
            "segmentation_json_sha256": digest(payload[segmentation_file]),
            "candidate_index": index, "mask_file": mask.filename, "mask_file_sha256": digest(payload[mask.filename]),
            "overlay_file": f"overlay_{index}.png", "overlay_sha256": digest(payload[f"overlay_{index}.png"]),
            "grounding_prediction_index": request.prediction_index, "grounding_box": list(request.selected_detection.box),
            "sam_model_id": result.model_id, "sam_revision": result.resolved_revision,
            "prompt_type": "BOX_PLUS_POINTS" if request.points else "BOX_ONLY",
            "source_selection_status": request.selection_status, "point_document_sha256": request.point_prompt_sha256,
            "mask_dimensions": list(mask.dimensions), "foreground_pixels": mask.foreground_pixels,
            "mask_bounds": list(mask.mask_box), "sam_score": mask.sam_score,
            "target_definition": target, "controlled_experiment": experiment,
            "evidence_hashes": {name: digest(data) for name, data in payload.items()}}


def _check(record: dict[str, Any], folder: Path) -> tuple[SegmentationResult, dict[str, bytes], dict[str, Any]]:
    if record.get("record_type") != "sam_mask_human_review" or record.get("schema_version") != 1:
        raise ValueError("not a SAM mask-review record")
    if any(record.get(field) is not False for field in
           ("image_edit_authorized", "diffusion_authorized", "cultural_transformation_authorized")):
        raise ValueError("mask review cannot authorize editing, diffusion or cultural transformation")
    result, payload = _bundle(_local(folder, record["segmentation_file"]))
    snapshot = _snapshot(result, payload, record["segmentation_file"], record["candidate_index"],
                         record["target_definition"], record["controlled_experiment"])
    if any(record.get(key) != value for key, value in snapshot.items()):
        raise ValueError("review snapshot/hash differs from bound segmentation evidence")
    return result, payload, snapshot


def prepare(segmentation: Path, out: Path, indices: tuple[int, ...], target: str, experiment: str,
            case_status: str = "PENDING", case_note: str = "") -> list[Path]:
    result, payload = _bundle(segmentation)
    if not indices or any(type(index) is not int for index in indices) or len(set(indices)) != len(indices):
        raise ValueError("explicitly list distinct candidate indices for inspection")
    snapshots = [_snapshot(result, payload, segmentation.name, index, target, experiment) for index in indices]
    if case_status not in ("PENDING", "NEEDS_REVIEW"):
        raise ValueError("preparation status can only be PENDING or NEEDS_REVIEW")
    out.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        (out / name).write_bytes(data)
    requests = []
    created = datetime.now(timezone.utc).isoformat()
    for snapshot in snapshots:
        record = {"schema_version": 1, "record_type": "sam_mask_human_review", **snapshot,
                  "decision": "PENDING", "selected_mask_index": None, "selected_mask_sha256": None,
                  "candidate_kind": None, "reviewer": None, "reason": "Awaiting actual human inspection and decision.",
                  "created_at_utc": created, "reviewed_at_utc": None,
                  "inspected_original": False, "inspected_mask": False, "inspected_overlay": False,
                  "image_edit_authorized": False, "diffusion_authorized": False, "cultural_transformation_authorized": False}
        path = out / f"pending_{snapshot['candidate_index']}.json"
        _write(path, record)
        requests.append(path)
    _write(out / "case.json", {"record_type": "mask_review_case_manifest", "preparation_status": case_status,
                               "status_origin": "preparation triage, not a human decision", "case_note": case_note,
                               "human_decision": "PENDING", "target_definition": target,
                               "controlled_experiment": experiment, "candidate_indices": list(indices),
                               "requests": [path.name for path in requests]})
    width, height = result.request.original_dimensions
    canvas = Image.new("RGB", (width * (len(indices) + 1), height * 2 + 80), "white")
    images = [(result.settings["source_image_copy"], 0, 0, "original"), ("box.png", 0, 1, "unchanged source box")]
    for column, index in enumerate(indices, 1):
        images.extend([(f"overlay_{index}.png", column, 0, f"candidate {index} overlay; PENDING"),
                       (_candidate(result, index).filename, column, 1, f"candidate {index} binary mask; PENDING")])
    draw = ImageDraw.Draw(canvas)
    for name, column, row, title in images:
        with Image.open(BytesIO(payload[name])) as source:
            canvas.paste(source.convert("RGB"), (column * width, 40 + row * (height + 40)))
        draw.text((column * width + 8, 12 + row * (height + 40)), title, fill="black")
    canvas.save(out / "comparison_candidates.png")
    return requests


def _human(name: str, reason: str, declarations: tuple[bool, bool, bool]) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("supply an actual reviewer identity")
    normalized = "_".join(name.strip().upper().split()).replace("-", "_")
    if normalized in {"YOUR_NAME", "YOURNAME", "YOUR_REAL_NAME", "REVIEWER_NAME", "REVIEWER", "NAME",
                      "YOUR_FULL_NAME", "YOUR_NAME_HERE", "FULL_NAME", "UNKNOWN", "PENDING", "TODO", "N/A", "NONE", "NULL"} or "<" in name or ">" in name:
        raise ValueError("placeholder reviewer identities are not accepted")
    if not isinstance(reason, str) or not reason.strip() or any(value is not True for value in declarations):
        raise ValueError("supply a reason and declare inspection of the original, mask and overlay")


def decide(request: Path, out: Path, decision: str, reviewer: str, reason: str, index: int | None = None,
           inspected_original: bool = False, inspected_mask: bool = False, inspected_overlay: bool = False) -> dict[str, Any]:
    raw = request.read_bytes()
    record = _json(raw)
    _check(record, request.parent)
    if record.get("decision") != "PENDING" or record.get("selected_mask_index") is not None or record.get("candidate_kind") is not None:
        raise ValueError("start from an unselected PENDING request; never edit existing decisions")
    if out.parent.resolve() != request.parent.resolve():
        raise ValueError("save the new decision alongside its bound evidence")
    if decision not in (ACCEPT, "REJECT", "NEEDS_REVIEW"):
        raise ValueError("unknown mask-review decision")
    _human(reviewer, reason, (inspected_original, inspected_mask, inspected_overlay))
    if decision == ACCEPT:
        if type(index) is not int or index != record["candidate_index"]:
            raise ValueError("explicitly select this request's exact candidate index")
    elif index is not None:
        raise ValueError("nonacceptance does not select a mask")
    record.update(decision=decision, reviewer=reviewer.strip(), reason=reason.strip(),
                  reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                  inspected_original=inspected_original, inspected_mask=inspected_mask, inspected_overlay=inspected_overlay,
                  selected_mask_index=index, selected_mask_sha256=record["mask_file_sha256"] if decision == ACCEPT else None,
                  candidate_kind=KIND if decision == ACCEPT else None,
                  source_request_file=request.name, source_request_sha256=digest(raw))
    _write(out, record)
    return record


def read_candidate(path: Path) -> Image.Image:
    """Return verified binary-mask pixels for the stated controlled test only."""
    record = _json(path.read_bytes())
    _, payload, snapshot = _check(record, path.parent)
    if record.get("decision") != ACCEPT or record.get("candidate_kind") != KIND:
        raise ValueError("only explicit ACCEPT_FOR_SEGMENTATION_TEST releases one research mask")
    _human(record.get("reviewer"), record.get("reason"),
           (record.get("inspected_original"), record.get("inspected_mask"), record.get("inspected_overlay")))
    if (type(record.get("selected_mask_index")) is not int or record["selected_mask_index"] != record["candidate_index"]
            or record.get("selected_mask_sha256") != record["mask_file_sha256"]):
        raise ValueError("accepted selection does not match the bound candidate")
    timestamp = record.get("reviewed_at_utc")
    if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp).utcoffset() is None:
        raise ValueError("a timezone-aware human review timestamp is required")
    parent_bytes = _local(path.parent, record["source_request_file"]).read_bytes()
    parent = _json(parent_bytes)
    if (digest(parent_bytes) != record.get("source_request_sha256") or parent.get("decision") != "PENDING"
            or any(parent.get(key) != value for key, value in snapshot.items())):
        raise ValueError("source request audit hash or experiment scope changed")
    with Image.open(BytesIO(payload[record["mask_file"]])) as image:
        return image.copy()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ready = commands.add_parser("prepare", help="Copy existing evidence and create only PENDING human requests")
    ready.add_argument("--segmentation", type=Path, required=True)
    ready.add_argument("--candidates", type=int, nargs="+", required=True)
    ready.add_argument("--target", required=True)
    ready.add_argument("--experiment", required=True)
    ready.add_argument("--case-status", choices=("PENDING", "NEEDS_REVIEW"), default="PENDING")
    ready.add_argument("--case-note", default="")
    ready.add_argument("--out", type=Path, required=True)
    submit = commands.add_parser("decide", help="Record a real human decision; not automated approval")
    submit.add_argument("--request", type=Path, required=True)
    submit.add_argument("--decision", choices=(ACCEPT, "REJECT", "NEEDS_REVIEW"), required=True)
    submit.add_argument("--reviewer", required=True)
    submit.add_argument("--reason", required=True)
    submit.add_argument("--index", type=int)
    for flag in ("original", "mask", "overlay"):
        submit.add_argument(f"--inspected-{flag}", action="store_true")
    submit.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            for path in prepare(args.segmentation, args.out, tuple(args.candidates), args.target, args.experiment,
                                args.case_status, args.case_note):
                print(path)
        else:
            record = decide(args.request, args.out, args.decision, args.reviewer, args.reason, args.index,
                            args.inspected_original, args.inspected_mask, args.inspected_overlay)
            print(f"{record['decision']}; no editing/diffusion authorization; saved {args.out}")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
