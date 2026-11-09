"""Independent box-prompted SAM research. No image editing or planner adapter."""
from dataclasses import asdict
import gc
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter
import torch

from transcreation.config import SamConfig
from transcreation.contracts import SamPoint, SegmentationInput, SegmentationMask, SegmentationResult


def load_segmentation_input(image: Path, detection: Path, index: int | None = None,
                            research_only: bool = False, review: Path | None = None,
                            note: str = "", expected_image_sha256: str | None = None,
                            points_file: Path | None = None) -> SegmentationInput:
    # Reuse the existing working-tree review utility, not an alternative approval policy.
    # The independent research command is run as `python -m scripts.segment_sam` from root.
    from scripts.review_grounding import _evidence, read_candidate

    image_bytes, detection_bytes = image.read_bytes(), detection.read_bytes()
    result, _ = _evidence(image_bytes, detection_bytes)
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    detection_hash = hashlib.sha256(detection_bytes).hexdigest()
    if expected_image_sha256 is not None and image_hash != expected_image_sha256:
        raise ValueError("explicit source image SHA-256 mismatch")
    if type(research_only) is not bool or research_only == (review is not None):
        raise ValueError("choose exactly one: explicit RESEARCH_ONLY or an accepted review file")
    review_hash = None
    if review is not None:
        candidate = read_candidate(review)
        review_bytes = review.read_bytes()
        record = json.loads(review_bytes)
        name = record["reviewer"].strip().upper().replace(" ", "_")
        if name in ("YOUR_NAME", "YOUR_REAL_NAME", "REVIEWER_NAME"):
            raise ValueError("reviewer is an unresolved placeholder; use RESEARCH_ONLY without inventing approval")
        if record["original_image_sha256"] != image_hash or record["detection_json_sha256"] != detection_hash:
            raise ValueError("review is bound to a different image/detection file")
        if index is not None and index != record["selected_prediction_index"]:
            raise ValueError("explicit index disagrees with accepted review")
        index = record["selected_prediction_index"]
        if candidate != result.detections[index]:
            raise ValueError("reviewed box does not match supplied detection")
        review_hash = hashlib.sha256(review_bytes).hexdigest()
    if result.status != "DETECTED" or type(index) is not int or not 0 <= index < len(result.detections):
        raise ValueError("supply an explicit valid zero-based prediction index from a successful detection")
    points, point_hash = (), None
    if points_file is not None:
        if not research_only:
            raise ValueError("point annotations are research-only and are not covered by an accepted box review")
        point_bytes = points_file.read_bytes()
        document = json.loads(point_bytes)
        if (not isinstance(document, dict) or document.get("annotation_status") != "RESEARCH_ONLY_REQUIRES_REVIEW"
                or document.get("coordinate_system") != "original_image_xy_pixels"
                or not isinstance(document.get("target_definition"), str) or not document["target_definition"].strip()
                or not isinstance(document.get("points"), list)):
            raise ValueError("invalid research point-prompt document")
        if (document.get("source_image_sha256") != image_hash or document.get("detection_json_sha256") != detection_hash
                or type(document.get("prediction_index")) is not int or document["prediction_index"] != index):
            raise ValueError("point prompts are bound to different source evidence or index")
        try:
            points = tuple(SamPoint(**point) for point in document["points"])
        except TypeError as exc:
            raise ValueError(f"invalid point schema: {exc}") from exc
        point_hash = hashlib.sha256(point_bytes).hexdigest()
    return SegmentationInput(str(image), image_hash, tuple(result.original_dimensions), str(detection),
                             detection_hash, index, result.detections[index], result.source_phrase,
                             result.model_id, result.resolved_revision,
                             "RESEARCH_ONLY" if research_only else "REVIEWED_SELECTION", note,
                             str(review) if review else None, review_hash,
                             points=points, point_prompt_file=str(points_file) if points_file else None,
                             point_prompt_sha256=point_hash)


def draw_point_prompts(original: Image.Image, box: tuple[float, float, float, float],
                       points: tuple[SamPoint, ...]) -> Image.Image:
    preview = original.copy()
    draw = ImageDraw.Draw(preview)
    draw.rectangle(box, outline="red", width=3)
    for index, point in enumerate(points):
        color = "lime" if point.label == 1 else "cyan"
        draw.ellipse((point.x - 5, point.y - 5, point.x + 5, point.y + 5), fill=color, outline="black", width=1)
        draw.text((point.x + 8, point.y - 10), f"p{index} label={point.label}", fill=color,
                  stroke_width=1, stroke_fill="black")
    return preview


def validate_binary_mask(mask: torch.Tensor, width: int, height: int) -> int:
    if not isinstance(mask, torch.Tensor) or mask.dtype != torch.bool:
        raise ValueError("restored SAM masks must be binary boolean tensors")
    if tuple(mask.shape) != (height, width):
        raise ValueError("mask dimensions do not match the exact original image")
    return int(mask.sum().item())


def _factories():
    from transformers import SamModel, SamProcessor
    return SamProcessor, SamModel


def _write_visuals(original: Image.Image, request: SegmentationInput, directory: Path,
                   masks: tuple[SegmentationMask, ...], primary: int | None) -> None:
    box_view = original.copy()
    ImageDraw.Draw(box_view).rectangle(request.selected_detection.box, outline="red", width=3)
    box_view.save(directory / "box.png")
    prompt_view = draw_point_prompts(original, request.selected_detection.box, request.points) if request.points else box_view
    for candidate in masks:
        with Image.open(directory / candidate.filename) as source:
            binary = source.convert("L")
        # This morphological edge band is visualization only; binary masks are unchanged.
        boundary = ImageChops.difference(binary.filter(ImageFilter.MaxFilter(3)), binary.filter(ImageFilter.MinFilter(3)))
        overlay = Image.composite(Image.new("RGB", original.size, "lime"), original,
                                  binary.point(lambda v: 90 if v else 0))
        overlay = Image.composite(Image.new("RGB", original.size, "red"), overlay, boundary)
        overlay.save(directory / f"overlay_{candidate.index}.png")
    width, height = original.size
    if primary is not None:
        with Image.open(directory / f"overlay_{primary}.png") as source:
            overlay = source.convert("RGB")
    else:
        overlay = original.copy()
    comparison = Image.new("RGB", (width * 3, height + 48), "white")
    for column, image in enumerate((original, prompt_view, overlay)):
        comparison.paste(image, (width * column, 48))
    draw = ImageDraw.Draw(comparison)
    prompt_title = f"source box index {request.prediction_index}" + (f" + {len(request.points)} research points" if request.points else "")
    for column, text in enumerate(("original", prompt_title,
                                   f"{request.selection_status}; mask {primary}; SAM score ranking only")):
        draw.text((width * column + 8, 12), text, fill="black")
    comparison.save(directory / "comparison.png")
    if masks:
        gallery = Image.new("RGB", (width * len(masks), height + 48), "white")
        draw = ImageDraw.Draw(gallery)
        for column, candidate in enumerate(masks):
            with Image.open(directory / f"overlay_{candidate.index}.png") as source:
                gallery.paste(source, (column * width, 48))
            draw.text((column * width + 8, 12),
                      f"mask {candidate.index}; SAM score {candidate.sam_score:.6f}; {candidate.status}", fill="black")
        gallery.save(directory / "candidate_gallery.png")


class SamSegmenter:
    def __init__(self, config: SamConfig):
        self.config = config
        self.processor = self.model = None
        self.device = None

    def close(self) -> None:
        self.processor = self.model = None
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
        self.device = None

    def _load(self, device: str) -> None:
        processor_factory, model_factory = _factories()
        self.device = device
        self.processor = processor_factory.from_pretrained(self.config.model_id, revision=self.config.revision)
        self.model = model_factory.from_pretrained(self.config.model_id, revision=self.config.revision,
                                                   use_safetensors=True, dtype=torch.float32)
        if self.model.config._commit_hash != self.config.revision:
            raise RuntimeError("SAM resolved revision does not match the pinned commit")
        self.model.to(device).eval()

    def segment(self, request: SegmentationInput, out: Path) -> SegmentationResult:
        if not isinstance(request, SegmentationInput):
            raise ValueError("SAM requires explicit segmentation input, never a planner output")
        checked = load_segmentation_input(Path(request.source_image), Path(request.detection_file),
                                           request.prediction_index, request.selection_status == "RESEARCH_ONLY",
                                           Path(request.review_file) if request.review_file else None,
                                           request.selection_note, request.image_sha256,
                                           Path(request.point_prompt_file) if request.point_prompt_file else None)
        if checked != request:
            raise ValueError("source/detection/review evidence changed after selection")
        image_bytes = Path(request.source_image).read_bytes()
        detection_bytes = Path(request.detection_file).read_bytes()
        if (hashlib.sha256(image_bytes).hexdigest() != request.image_sha256
                or hashlib.sha256(detection_bytes).hexdigest() != request.detection_sha256):
            raise ValueError("evidence changed before inference; refuse stale input")
        with Image.open(BytesIO(image_bytes)) as source:
            original = source.convert("RGB")
        out.mkdir(parents=True, exist_ok=False)
        image_filename = "original" + (Path(request.source_image).suffix.lower() or ".img")
        (out / image_filename).write_bytes(image_bytes)
        (out / "source_detection.json").write_bytes(detection_bytes)
        if request.point_prompt_file:
            point_bytes = Path(request.point_prompt_file).read_bytes()
            if hashlib.sha256(point_bytes).hexdigest() != request.point_prompt_sha256:
                raise ValueError("point prompt file changed before inference")
            (out / "points.json").write_bytes(point_bytes)
            # Save the exact point placement before model loading/forward, even on failure.
            draw_point_prompts(original, request.selected_detection.box, request.points).save(out / "points.png")
        if request.review_file:
            review = Path(request.review_file)
            evidence = json.loads(review.read_bytes())
            review_dir = out / "review_evidence"
            review_dir.mkdir()
            for name in {review.name, evidence["image_file"], evidence["detection_file"],
                         evidence["annotation_file"], evidence["source_request_file"]}:
                shutil.copyfile(review.parent / name, review_dir / name)
        started = time.perf_counter()
        device = self.config.device
        observations = [{"code": "RESEARCH_SCOPE", "message": "Segmentation test only; SAM scores are not measured accuracy and no image editing is authorized."}]
        if request.selection_status == "RESEARCH_ONLY":
            observations.append({"code": "NO_CONFIRMED_HUMAN_APPROVAL", "message": request.selection_note})
        timing, memory, shapes, candidates = {}, {}, {}, []
        processor_settings = None
        attention_backend = None
        resolved_revision = None
        inputs = outputs = restored = None
        status, primary = "ERROR", None
        if device == "cuda" and not torch.cuda.is_available() and self.config.cpu_fallback:
            observations.append({"code": "CUDA_UNAVAILABLE", "message": "Explicit CPU fallback"})
            device = "cpu"
        try:
            for attempt in range(2):
                attempt_start = time.perf_counter()
                try:
                    torch.manual_seed(self.config.seed)
                    if device == "cuda":
                        if not torch.cuda.is_available():
                            raise RuntimeError("CUDA unavailable and fallback disabled")
                        torch.cuda.reset_peak_memory_stats()
                    load_start = time.perf_counter()
                    if self.model is None or self.device != device:
                        self.close()
                        self._load(device)
                    timing["load_seconds"] = time.perf_counter() - load_start
                    resolved_revision = self.model.config._commit_hash
                    processor_settings = self.processor.image_processor.to_dict()
                    attention_backend = self.model.config._attn_implementation
                    if device == "cuda":
                        memory["load_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
                        torch.cuda.reset_peak_memory_stats()
                    preprocess = time.perf_counter()
                    point_kwargs = {}
                    if request.points:
                        point_kwargs = {"input_points": [[[point.x, point.y] for point in request.points]],
                                        "input_labels": [[point.label for point in request.points]]}
                    inputs = self.processor(images=original, input_boxes=[[list(request.selected_detection.box)]],
                                            return_tensors="pt", **point_kwargs)
                    if tuple(inputs["input_boxes"].shape) != (1, 1, 4):
                        raise ValueError("SAM processor must produce one image and one XYXY box")
                    if request.points:
                        if (tuple(inputs["input_points"].shape) != (1, 1, len(request.points), 2)
                                or tuple(inputs["input_labels"].shape) != (1, 1, len(request.points))
                                or inputs["input_labels"].tolist() != [[[point.label for point in request.points]]]):
                            raise ValueError("unexpected combined SAM point/label tensor dimensions or labels")
                        shapes.update(input_points=list(inputs["input_points"].shape),
                                      input_labels=list(inputs["input_labels"].shape),
                                      transformed_input_points=inputs["input_points"].tolist(),
                                      point_labels=inputs["input_labels"].tolist())
                    if inputs["original_sizes"].tolist() != [[original.height, original.width]]:
                        raise ValueError("SAM processor original_sizes mismatch")
                    original_sizes = inputs["original_sizes"].clone().cpu()
                    reshaped_sizes = inputs["reshaped_input_sizes"].clone().cpu()
                    shapes.update(input_boxes=list(inputs["input_boxes"].shape),
                                  transformed_input_boxes=inputs["input_boxes"].tolist(),
                                  original_sizes=original_sizes.tolist(), reshaped_input_sizes=reshaped_sizes.tolist())
                    inputs = inputs.to(device)
                    timing["preprocess_seconds"] = time.perf_counter() - preprocess
                    if device == "cuda":
                        torch.cuda.synchronize()
                    inference = time.perf_counter()
                    model_points = {key: inputs[key] for key in ("input_points", "input_labels")} if request.points else {}
                    with torch.inference_mode():
                        outputs = self.model(pixel_values=inputs["pixel_values"], input_boxes=inputs["input_boxes"],
                                             multimask_output=True, **model_points)
                    if device == "cuda":
                        torch.cuda.synchronize()
                    timing["inference_seconds"] = time.perf_counter() - inference
                    postprocess = time.perf_counter()
                    shapes.update(pred_masks=list(outputs.pred_masks.shape), iou_scores=list(outputs.iou_scores.shape))
                    if outputs.pred_masks.ndim != 5 or tuple(outputs.pred_masks.shape[:2]) != (1, 1):
                        raise ValueError("unexpected SAM pred_masks batch/box dimensions")
                    if tuple(outputs.iou_scores.shape) != tuple(outputs.pred_masks.shape[:3]):
                        raise ValueError("SAM score and mask counts disagree")
                    if not torch.isfinite(outputs.pred_masks).all() or not torch.isfinite(outputs.iou_scores).all():
                        raise ValueError("non-finite SAM mask logits or scores")
                    # Restore on CPU to reduce CUDA pressure; masks still use processor transforms.
                    restored = self.processor.image_processor.post_process_masks(
                        outputs.pred_masks.detach().cpu(), original_sizes, reshaped_sizes,
                        mask_threshold=self.config.mask_threshold, binarize=True, return_tensors="pt")
                    if len(restored) != 1 or restored[0].ndim != 4 or restored[0].shape[0] != 1:
                        raise ValueError("unexpected restored mask image/box dimensions")
                    scores = outputs.iou_scores.detach().cpu()[0, 0].tolist()
                    if restored[0].shape[1] != len(scores) or not scores:
                        raise ValueError("restored mask and score counts disagree or are empty")
                    shapes["restored_masks"] = list(restored[0].shape)
                    for index, (mask, score) in enumerate(zip(restored[0][0], scores)):
                        foreground = validate_binary_mask(mask, original.width, original.height)
                        filename = f"mask_{index}.png"
                        Image.fromarray(mask.to(torch.uint8).numpy() * 255).save(out / filename)
                        ys, xs = mask.nonzero(as_tuple=True)
                        bounds = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if foreground else None
                        candidates.append(SegmentationMask(index, filename, original.size, score, foreground, bounds,
                                                           "VALID" if foreground else "REJECTED_EMPTY"))
                        if not foreground:
                            observations.append({"code": "EMPTY_MASK_REJECTED", "mask_index": index})
                    valid = [candidate for candidate in candidates if candidate.status == "VALID"]
                    primary = max(valid, key=lambda candidate: candidate.sam_score).index if valid else None
                    status = "SEGMENTED" if len(valid) == len(candidates) else ("PARTIAL_INVALID" if valid else "INVALID_OUTPUT")
                    timing["postprocess_and_mask_save_seconds"] = time.perf_counter() - postprocess
                    break
                except torch.cuda.OutOfMemoryError as exc:
                    observations.append({"code": "CUDA_OOM", "message": str(exc), "attempt": attempt})
                    timing.setdefault("failed_attempts", []).append({"device": device, "seconds": time.perf_counter() - attempt_start})
                    if device == "cuda" and torch.cuda.is_available():
                        memory["failed_cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
                    inputs = outputs = restored = None
                    self.close()
                    if device != "cuda" or not self.config.cpu_fallback or attempt:
                        raise
                    device = "cpu"
                    observations.append({"code": "CPU_FALLBACK", "message": "Retrying same SAM checkpoint in float32 on CPU"})
        except (OSError, RuntimeError, ValueError, ImportError, KeyError, TypeError) as exc:
            observations.append({"code": "SAM_ERROR", "type": type(exc).__name__, "message": str(exc)})
            status, primary = "ERROR", None
        timing["stage_seconds"] = time.perf_counter() - started
        memory["effective_device"] = device
        memory["peak_allocated_cuda_bytes"] = torch.cuda.max_memory_allocated() if device == "cuda" and torch.cuda.is_available() else None
        visual_start = time.perf_counter()
        _write_visuals(original, request, out, tuple(candidates), primary)
        timing["visualization_seconds"] = time.perf_counter() - visual_start
        settings = {**asdict(self.config), "effective_device": device, "batch_size": 1,
                    "eval": True, "inference_mode": True, "postprocess_device": "cpu",
                    "attention_backend": attention_backend, "processor": processor_settings,
                    "api_shapes": shapes, "binary_values": [0, 255], "mask_box_upper_bounds": "exclusive",
                    "source_image_copy": image_filename, "source_detection_copy": "source_detection.json",
                    "visualization_selection": "highest finite SAM score among nonempty candidates; no human mask approval"}
        if request.point_prompt_file:
            settings.update(point_prompt_copy="points.json", point_preview="points.png",
                            point_annotation_status="RESEARCH_ONLY_REQUIRES_REVIEW")
        result = SegmentationResult(request, self.config.model_id, resolved_revision, status,
                                    tuple(candidates), primary, settings, timing, memory, tuple(observations))
        (out / "segmentation.json").write_text(json.dumps(asdict(result), indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return result
