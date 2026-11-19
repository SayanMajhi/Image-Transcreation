"""Explicit downstream research execution, independent of planner/review decisions.

Each invocation creates a new run. Missing selections stop at the relevant boundary;
neither scores nor an old planner candidate can supply a selection implicitly.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time

from PIL import Image

from transcreation.config import (load_grounding_config, load_inpainting_config,
                                  load_planner_config, load_sam_config)
from transcreation.contracts import InpaintingInput, validate_localization_phrase
from transcreation.orchestration import _planner_idle
from transcreation.stages.ollama_planner import OllamaPlanner


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ResearchInput:
    source_image: str
    image_sha256: str
    source_culture: str
    target_culture: str
    objective: str
    preservation_instructions: str
    source_phrase: str
    generation_prompt: str
    research_assumptions: str
    output_dir: str
    execution_mode: str = "GUIDED_RESEARCH"
    scope: str = "RESEARCH_ONLY"
    detection_file: str | None = None
    detection_sha256: str | None = None
    prediction_index: int | None = None
    segmentation_file: str | None = None
    segmentation_sha256: str | None = None
    mask_index: int | None = None
    mask_sha256: str | None = None
    selection_note: str | None = None
    points_file: str | None = None
    points_sha256: str | None = None
    protected_points: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        if self.execution_mode != "GUIDED_RESEARCH" or self.scope != "RESEARCH_ONLY":
            raise ValueError("this route is independent RESEARCH_ONLY, never an approved planner edit")
        for key in ("source_image", "source_culture", "target_culture", "objective",
                    "preservation_instructions", "source_phrase", "generation_prompt",
                    "research_assumptions", "output_dir"):
            value = getattr(self, key)
            if not isinstance(value, str) or value.strip().lower() in ("", "null", "none", "n/a"):
                raise ValueError(f"{key} must be explicit meaningful text")
        validate_localization_phrase(self.source_phrase)
        if not isinstance(self.protected_points, (list, tuple)) or any(
                not isinstance(point, (list, tuple)) or len(point) != 2
                or any(type(v) is not int or v < 0 for v in point) for point in self.protected_points):
            raise ValueError("protected points must be original-image nonnegative integer XY pairs")
        for key in ("image_sha256", "detection_sha256", "segmentation_sha256", "mask_sha256", "points_sha256"):
            value = getattr(self, key)
            if value is not None and (not isinstance(value, str) or len(value) != 64
                                      or any(c not in "0123456789abcdef" for c in value)):
                raise ValueError(f"{key} must be SHA-256")
        if self.image_sha256 is None:
            raise ValueError("source hash is required")
        for kind in ("detection", "segmentation", "points"):
            if (getattr(self, kind+"_file") is None) != (getattr(self, kind+"_sha256") is None):
                raise ValueError(f"{kind} file and hash must be supplied together")
        for index in (self.prediction_index, self.mask_index):
            if index is not None and (type(index) is not int or index < 0):
                raise ValueError("selection indices must be explicit nonnegative integers")
        if self.prediction_index is not None and self.detection_file is None:
            raise ValueError("prediction selection needs a pinned detection file")
        if self.segmentation_file and (self.prediction_index is None or self.points_file):
            raise ValueError("saved SAM evidence requires its box index; new points require a new SAM run")
        if (self.mask_index is None) != (self.mask_sha256 is None):
            raise ValueError("select one mask with both index and hash")
        if self.mask_index is not None and self.segmentation_file is None:
            raise ValueError("mask selection requires pinned SAM evidence")
        if self.points_file and self.prediction_index is None:
            raise ValueError("point prompts require explicit source-box selection")
        if (self.prediction_index is not None or self.mask_index is not None) and (
                not isinstance(self.selection_note, str) or not self.selection_note.strip()):
            raise ValueError("explicit selections require an inspection/limitation note, not a score rule")


def run_guided_research(request: ResearchInput, config_dir: Path | None = None) -> dict:
    """Localize, segment or generate according to explicit artifact-bound selections.

    This never imports planner drafts as edit specifications or changes review records.
    Existing review commands remain available for genuine human judgments; this route
    only records operator research choices and does not certify their semantic quality.
    """
    from transcreation.stages.grounding import GroundingDetector, save_grounding_artifacts
    from transcreation.stages.segmentation import SamSegmenter, load_segmentation_input
    from transcreation.stages.inpainting import run_inpainting
    from scripts.review_grounding import _evidence
    from scripts.review_mask import _bundle

    config_dir = config_dir or Path(__file__).resolve().parents[2]/"configs"
    out = Path(request.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    result = {"execution_mode": "GUIDED_RESEARCH", "scope": "RESEARCH_ONLY",
              "human_approved": False, "automated_plan_success": False,
              "cultural_edit_authorized": False, "status": "FAILED", "events": []}
    start = time.perf_counter()

    def save(name, value):
        (out/name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf8")

    def event(stage, action, **details):
        result["events"].append({"stage": stage, "action": action,
                                 "seconds": time.perf_counter()-start, **details})

    def checked(path, expected):
        path = Path(path)
        if file_hash(path) != expected:
            raise ValueError(f"evidence SHA-256 mismatch: {path}")
        return path

    def stop(status, reason):
        result.update(status=status, reason=reason)
        return result

    try:
        save("request.json", asdict(request))
        image = checked(request.source_image, request.image_sha256)
        with Image.open(image) as source:
            dimensions = source.size
            source.verify()
        if any(not (x < dimensions[0] and y < dimensions[1]) for x, y in request.protected_points):
            raise ValueError("protected sample point lies outside the source image")
        (out/("source"+image.suffix)).write_bytes(image.read_bytes())  # original bytes, not a re-encoding
        if request.detection_file is None:
            _planner_idle(OllamaPlanner(load_planner_config(config_dir/"planner.yaml")))
            event("resources", "OLLAMA_IDLE_CONFIRMED")
            detector = GroundingDetector(load_grounding_config(config_dir/"grounding.yaml"))
            try:
                event("grounding", "DISPATCH", phrase=request.source_phrase)
                detection = detector.detect(image, request.source_phrase)
                save_grounding_artifacts(image, detection, out/"grounding")
            finally:
                detector.close()
                event("grounding", "RELEASED")
            if detection.status not in ("DETECTED", "NO_DETECTIONS"):
                raise ValueError(f"grounding failed: {detection.observations}")
            return stop("SOURCE_OBJECT_REQUIRES_REVIEW", "Inspect every predicted box; supply pinned detection, explicit index and selection note. No SAM or generation ran.")

        detection_file = checked(request.detection_file, request.detection_sha256)
        detection, _ = _evidence(image.read_bytes(), detection_file.read_bytes())
        canonical = lambda text: text.strip().casefold().rstrip(".")
        if canonical(detection.source_phrase) != canonical(request.source_phrase):
            raise ValueError("source phrase differs from recorded original-object query")
        event("grounding", "EVIDENCE_VERIFIED", sha256=request.detection_sha256)
        if detection.status != "DETECTED" or request.prediction_index is None:
            return stop("SOURCE_OBJECT_REQUIRES_REVIEW", "No detections or no explicit instance selection; no model score can select a box.")
        if request.prediction_index >= len(detection.detections):
            raise ValueError("prediction index does not exist")
        if request.segmentation_file is None:
            if request.points_file:
                checked(request.points_file, request.points_sha256)
            sam_input = load_segmentation_input(image, detection_file, request.prediction_index,
                            True, note=request.selection_note, expected_image_sha256=request.image_sha256,
                            points_file=Path(request.points_file) if request.points_file else None)
            _planner_idle(OllamaPlanner(load_planner_config(config_dir/"planner.yaml")))
            segmenter = SamSegmenter(load_sam_config(config_dir/"sam.yaml"))
            try:
                event("segmentation", "DISPATCH", prediction_index=request.prediction_index)
                segmented = segmenter.segment(sam_input, out/"segmentation")
            finally:
                segmenter.close()
                event("segmentation", "RELEASED")
            if segmented.status != "SEGMENTED":
                raise ValueError(f"segmentation failed: {segmented.observations}")
            return stop("MASK_REQUIRES_REVIEW", "Inspect all masks/overlays against protected objects; supply pinned SAM result, explicit candidate, mask hash and research selection note. No generation ran.")

        segmentation_file = checked(request.segmentation_file, request.segmentation_sha256)
        segmented, _ = _bundle(segmentation_file)
        if (segmented.request.image_sha256 != request.image_sha256
                or segmented.request.detection_sha256 != request.detection_sha256
                or segmented.request.prediction_index != request.prediction_index):
            raise ValueError("SAM provenance differs from selected source/box")
        event("segmentation", "EVIDENCE_VERIFIED", sha256=request.segmentation_sha256)
        if request.mask_index is None:
            return stop("MASK_REQUIRES_REVIEW", "An explicit mask index and hash are required. Never infer selection from SAM score.")
        masks = [mask for mask in segmented.masks if mask.index == request.mask_index]
        if len(masks) != 1 or masks[0].status != "VALID":
            raise ValueError("selected mask is absent, ambiguous or invalid")
        mask = checked(segmentation_file.parent/masks[0].filename, request.mask_sha256)
        # Operator-supplied protected samples are a veto, never proof of full mask quality.
        # They are separate from SAM point prompts and never modify model predictions.
        with Image.open(mask) as binary:
            violations = [[x, y] for x, y in request.protected_points if binary.getpixel((x, y)) != 0]
        result["mask_guard_check"] = {"protected_samples": list(request.protected_points),
                                     "included_protected_samples": violations,
                                     "meaning": "Sparse protection veto only; not pixel ground truth or complete boundary verification."}
        if violations:
            return stop("MASK_REQUIRES_REVIEW", "Selected mask includes explicitly protected sample pixels; no inpainting dispatched. Supply an inspected suitable mask, not a higher score.")
        inpainting = InpaintingInput(str(image), request.image_sha256, str(segmentation_file),
                         request.segmentation_sha256, str(mask), request.mask_sha256, request.mask_index,
                         request.generation_prompt, request.selection_note+"; "+request.research_assumptions,
                         "RESEARCH_ONLY")
        save("inpainting_input.json", asdict(inpainting))
        _planner_idle(OllamaPlanner(load_planner_config(config_dir/"planner.yaml")))
        event("inpainting", "DISPATCH_RESEARCH_ONLY", mask_index=request.mask_index)
        generated = run_inpainting(inpainting, load_inpainting_config(config_dir/"inpainting.yaml"), out/"inpainting")
        event("inpainting", "RELEASED", status=generated["status"])
        if generated["status"] != "COMPLETED":
            raise ValueError(f"inpainting failed: {generated['observations']}")
        # Reopen saved pixels independently of the generation implementation.
        import numpy as np
        checked(image, request.image_sha256)
        checked(segmentation_file, request.segmentation_sha256)
        checked(mask, request.mask_sha256)
        with Image.open(image) as source, Image.open(mask) as binary, Image.open(out/"inpainting/final.png") as final:
            if final.size != source.size or final.mode != "RGB":
                raise ValueError("saved final image has unexpected dimensions or mode")
            editable = np.asarray(binary) == 255
            changed = np.any(np.asarray(source.convert("RGB")) != np.asarray(final), axis=2)
            outside, inside = int((changed & ~editable).sum()), int((changed & editable).sum())
        if outside or not inside:
            raise ValueError("saved output changed protected pixels or generated no visible pixel change")
        result["pixel_verification"] = {"changed_inside_mask": inside, "changed_outside_mask": outside}
        result["final_image"] = "inpainting/final.png"
        return stop("GENERATION_COMPLETED", "Independent research generation only; no human approval or automated Qwen success is claimed.")
    except Exception as exc:
        return stop("FAILED", f"{type(exc).__name__}: {exc}")
    finally:
        result["total_seconds"] = time.perf_counter()-start
        result["artifact_sha256"] = {p.relative_to(out).as_posix(): file_hash(p)
                                     for p in out.rglob('*') if p.is_file()}
        save("research_result.json", result)
