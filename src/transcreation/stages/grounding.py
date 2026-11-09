"""Independent research localization; no planner adapter or edit execution."""
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import time

from PIL import Image, ImageDraw
import torch

from transcreation.config import GroundingConfig
from transcreation.contracts import GroundingDetection, GroundingResult


def validate_phrase(phrase: str) -> str:
    if not isinstance(phrase, str) or phrase.strip().lower().strip(". ") in ("", "null", "none", "n/a", "na"):
        raise ValueError("provide a non-placeholder research localization phrase")
    if not any(ch.isalnum() for ch in phrase):
        raise ValueError("localization phrase must contain text")
    return phrase.strip().lower().rstrip(".") + "."


def _factories():
    from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
    return AutoProcessor, AutoModelForZeroShotObjectDetection


def validate_predictions(predictions: dict, width: int, height: int) -> tuple[tuple[GroundingDetection, ...], list[dict], dict]:
    boxes = predictions["boxes"].tolist()
    scores = predictions["scores"].tolist()
    labels = list(predictions["text_labels"])
    if not len(boxes) == len(scores) == len(labels):
        raise ValueError("prediction lengths disagree")
    valid, issues = [], []
    for index, (box, score, label) in enumerate(zip(boxes, scores, labels)):
        detection = GroundingDetection(tuple(box), score, label)
        try:
            detection.validate(width, height)
        except ValueError as exc:
            issues.append({"code": "INVALID_BOX_OR_SCORE", "index": index, "message": str(exc)})
        else:
            valid.append(detection)
    # JSON cannot represent NaN/Infinity. Retain their explicit spellings in the audit.
    safe_boxes = [[v if math.isfinite(v) else str(v) for v in box] for box in boxes]
    safe_scores = [v if math.isfinite(v) else str(v) for v in scores]
    return tuple(valid), issues, {"boxes": safe_boxes, "scores": safe_scores, "text_labels": labels}


class GroundingDetector:
    """Lazy pinned detector; retry once on CPU after CUDA OOM."""

    def __init__(self, config: GroundingConfig):
        self.config = config
        self.processor = self.model = None
        self.device = None

    def close(self) -> None:
        self.processor = self.model = None
        if self.device == "cuda":
            torch.cuda.empty_cache()
        self.device = None

    def _load(self, device: str) -> None:
        processor_factory, model_factory = _factories()
        self.device = device
        self.processor = processor_factory.from_pretrained(
            self.config.model_id, revision=self.config.revision, trust_remote_code=False)
        self.model = model_factory.from_pretrained(
            self.config.model_id, revision=self.config.revision, trust_remote_code=False,
            use_safetensors=True, dtype=torch.float32, disable_custom_kernels=True)
        if self.model.config._commit_hash != self.config.revision:
            raise RuntimeError("loaded checkpoint revision does not match pinned revision")
        self.model.to(device).eval()

    def detect(self, image_path: Path, phrase: str) -> GroundingResult:
        prompt = validate_phrase(phrase)
        image_bytes = image_path.read_bytes()
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.convert("RGB")
        width, height = image.size
        started = time.perf_counter()
        issues, timing, memory, raw, detections = [], {}, {}, {}, ()
        device = self.config.device
        status = "ERROR"
        inputs = outputs = predictions = None
        if device == "cuda" and not torch.cuda.is_available():
            issues.append({"code": "CUDA_UNAVAILABLE", "message": "CUDA is unavailable"})
            device = "cpu" if self.config.cpu_fallback else "cuda"
        try:
            if device == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("CUDA unavailable and CPU fallback disabled")
            for attempt in range(2):
                try:
                    torch.manual_seed(self.config.seed)
                    if device == "cuda":
                        torch.cuda.reset_peak_memory_stats()
                    load_start = time.perf_counter()
                    if self.model is None or self.device != device:
                        self.close()
                        self._load(device)
                    timing["load_seconds"] = time.perf_counter() - load_start
                    if device == "cuda":
                        memory["load_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
                        torch.cuda.reset_peak_memory_stats()
                    preprocess = time.perf_counter()
                    inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(device)
                    timing["preprocess_seconds"] = time.perf_counter() - preprocess
                    if device == "cuda":
                        torch.cuda.synchronize()
                    inference = time.perf_counter()
                    with torch.inference_mode():
                        outputs = self.model(**inputs)
                    if device == "cuda":
                        torch.cuda.synchronize()
                    timing["inference_seconds"] = time.perf_counter() - inference
                    postprocess = time.perf_counter()
                    predictions = self.processor.post_process_grounded_object_detection(
                        outputs, input_ids=inputs["input_ids"],
                        threshold=self.config.box_threshold, text_threshold=self.config.text_threshold,
                        target_sizes=[(height, width)])[0]
                    detections, rejected, raw = validate_predictions(predictions, width, height)
                    issues.extend(rejected)
                    status = "INVALID_OUTPUT" if rejected else ("DETECTED" if detections else "NO_DETECTIONS")
                    timing["postprocess_seconds"] = time.perf_counter() - postprocess
                    break
                except torch.cuda.OutOfMemoryError as exc:
                    issues.append({"code": "CUDA_OOM", "message": str(exc)})
                    inputs = outputs = predictions = None
                    self.close()
                    if device != "cuda" or not self.config.cpu_fallback or attempt:
                        raise
                    device = "cpu"
        except (OSError, RuntimeError, ValueError, ImportError, KeyError, TypeError) as exc:
            issues.append({"code": "GROUNDING_ERROR", "type": type(exc).__name__, "message": str(exc)})
            status, detections = "ERROR", ()
        timing["total_seconds"] = time.perf_counter() - started
        memory["inference_peak_allocated_bytes"] = torch.cuda.max_memory_allocated() if device == "cuda" and torch.cuda.is_available() else None
        memory["device"] = device
        settings = {**asdict(self.config), "effective_device": device, "normalized_prompt": prompt,
                    "batch_size": 1, "dtype": "float32", "disable_custom_kernels": True,
                    "inference_mode": True, "eval": True, "coordinate_format": "xyxy_original_pixels",
                    "postprocess_box_argument": "threshold", "target_sizes": [[height, width]],
                    "image_processor": self.processor.image_processor.to_dict() if self.processor else None}
        return GroundingResult(hashlib.sha256(image_bytes).hexdigest(), (width, height), phrase,
                               self.config.model_id, self.config.revision, status, detections,
                               settings, timing, memory, raw, tuple(issues))


def save_grounding_artifacts(image_path: Path, result: GroundingResult, directory: Path) -> None:
    """Create new artifacts only; the source image is never saved over."""
    directory.mkdir(parents=True, exist_ok=False)
    image_bytes = image_path.read_bytes()
    if hashlib.sha256(image_bytes).hexdigest() != result.image_sha256:
        raise ValueError("source image changed since detection")
    with Image.open(BytesIO(image_bytes)) as source:
        original = source.convert("RGB")
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    for index, detection in enumerate(result.detections, 1):
        draw.rectangle(detection.box, outline="red", width=max(2, original.width // 300))
        draw.text((detection.box[0] + 3, detection.box[1] + 3),
                  f"{index}: {detection.label} {detection.score:.3f}", fill="red",
                  stroke_width=1, stroke_fill="white")
    comparison = Image.new("RGB", (original.width * 2, original.height + 40), "white")
    comparison.paste(original, (0, 40))
    comparison.paste(annotated, (original.width, 40))
    title = ImageDraw.Draw(comparison)
    title.text((8, 10), "original", fill="black")
    title.text((original.width + 8, 10), f"{result.source_phrase}: {result.status} ({len(result.detections)} boxes)", fill="black")
    original.save(directory / "original.png")
    annotated.save(directory / "annotated.png")
    comparison.save(directory / "comparison.png")
    (directory / "detection.json").write_text(
        json.dumps(asdict(result), indent=2, allow_nan=False) + "\n", encoding="utf-8")
