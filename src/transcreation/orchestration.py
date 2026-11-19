"""Fail-closed planning coordination and read-only research-chain replay.

An accepted edit-intent review permits grounding only, stopping for box review.
Existing segmentation-test reviews never authorize cultural image edits.
"""
from dataclasses import asdict, dataclass
from enum import StrEnum
import gc
import hashlib
from io import BytesIO
import json
from pathlib import Path
import time
from typing import Any

from PIL import Image

from transcreation.config import load_config, load_planner_config
from transcreation.contracts import CaptionStatus, PlanningDecision, PlanningInput, VerifiedObject, validate_localization_phrase
from transcreation.pipeline import create_captioner
from transcreation.stages.ollama_planner import OllamaPlanner, OllamaPlannerError
from transcreation.stages.planning import parse_model_draft, validate_planning_result


class PipelineState(StrEnum):
    CAPTION_COMPLETED = "CAPTION_COMPLETED"
    PLAN_REQUIRES_REVIEW = "PLAN_REQUIRES_REVIEW"
    NO_EDIT_JUSTIFIED = "NO_EDIT_JUSTIFIED"
    EDIT_PROPOSAL_READY = "EDIT_PROPOSAL_READY"
    EDIT_INTENT_REQUIRES_REVIEW = "EDIT_INTENT_REQUIRES_REVIEW"
    EDIT_INTENT_REJECTED = "EDIT_INTENT_REJECTED"
    SOURCE_OBJECT_REQUIRES_REVIEW = "SOURCE_OBJECT_REQUIRES_REVIEW"
    MASK_REQUIRES_REVIEW = "MASK_REQUIRES_REVIEW"
    RESEARCH_REPLAY_VALIDATED = "RESEARCH_REPLAY_VALIDATED"
    FAILED = "FAILED"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("expected a pinned SHA-256")


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


@dataclass(frozen=True)
class ReplayChain:
    source_phrase: str
    detection_file: str
    detection_sha256: str
    fixed_generation_prompt: str
    prediction_index: int | None = None
    segmentation_file: str | None = None
    segmentation_sha256: str | None = None
    mask_index: int | None = None
    mask_sha256: str | None = None
    box_review_file: str | None = None
    box_review_sha256: str | None = None
    mask_review_file: str | None = None
    mask_review_sha256: str | None = None
    inpainting_file: str | None = None
    inpainting_sha256: str | None = None

    def __post_init__(self):
        validate_localization_phrase(self.source_phrase)
        if not isinstance(self.fixed_generation_prompt, str) or not self.fixed_generation_prompt.strip():
            raise ValueError("replay requires a fixed independent research prompt")
        for name in ("detection", "segmentation", "box_review", "mask_review", "inpainting"):
            path, digest = getattr(self, name+"_file"), getattr(self, name+"_sha256")
            if (path is None) != (digest is None):
                raise ValueError(f"{name} reference requires both path and hash")
            if digest is not None:
                _hash(digest)
        if not self.detection_file:
            raise ValueError("replay requires an existing detection reference")
        for index in (self.prediction_index, self.mask_index):
            if index is not None and (type(index) is not int or index < 0):
                raise ValueError("selection index must be an explicit nonnegative integer")
        if self.mask_sha256 is not None:
            _hash(self.mask_sha256)


@dataclass(frozen=True)
class IntentReference:
    review_file: str
    review_sha256: str

    def __post_init__(self):
        _hash(self.review_sha256)
        if not isinstance(self.review_file, str) or not self.review_file.strip():
            raise ValueError("an explicit edit-intent review file is required")


@dataclass(frozen=True)
class PipelineInput:
    source_image: str
    image_sha256: str
    target_culture: str
    output_dir: str
    execution_mode: str
    source_culture: str | None = None
    user_instructions: str | None = None
    verified_objects: tuple[VerifiedObject, ...] = ()
    replay: ReplayChain | None = None
    edit_intent: IntentReference | None = None

    def __post_init__(self):
        _hash(self.image_sha256)
        for value in (self.source_image, self.target_culture, self.output_dir):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("image, target culture and output directory are required")
        if self.execution_mode not in ("AUTOMATED_PLANNING", "RESEARCH_REPLAY", "GROUNDING_TEST"):
            raise ValueError("choose AUTOMATED_PLANNING, RESEARCH_REPLAY or GROUNDING_TEST")
        if ((self.execution_mode == "RESEARCH_REPLAY" and not isinstance(self.replay, ReplayChain))
                or (self.execution_mode != "RESEARCH_REPLAY" and self.replay is not None)):
            raise ValueError("only explicit research replay accepts a replay chain")
        if self.edit_intent is not None and (self.execution_mode != "GROUNDING_TEST" or not isinstance(self.edit_intent, IntentReference)):
            raise ValueError("only GROUNDING_TEST accepts an edit-intent reference")
        # Reuse existing validation for user context; never infer verified objects from captions.
        PlanningInput("input validation only", CaptionStatus.UNKNOWN,
                      self.target_culture, self.source_culture, self.user_instructions, self.verified_objects)


@dataclass(frozen=True)
class PipelineResult:
    execution_mode: str
    state: PipelineState
    completed_stages: tuple[str, ...]
    stopped_at: str
    reason: str
    artifact_ids: dict[str, dict]
    transitions: tuple[dict, ...]
    required_reviews: tuple[str, ...] = ()
    errors: tuple[dict, ...] = ()
    image_generation_permitted: bool = False
    replay_validated: bool = False


def validate_planner_audit(request: PlanningInput, record: dict):
    """Recheck untouched raw response with the existing policy, never normalize a saved final into an edit."""
    if record.get("validation", {}).get("status") != "valid":
        problem = record.get("validation", {})
        raise OllamaPlannerError(problem.get("code", "invalid_planner_audit"), problem.get("message", "planner failed"))
    if _json(record.get("input")) != _json(asdict(request)):
        raise ValueError("planner input does not match the caption/user context")
    raw = json.loads(record["response"]["message"]["content"])
    if raw != record["raw_planning_result"]:
        raise ValueError("raw planner response/audit mismatch")
    draft, parse_issues = parse_model_draft(raw)
    result, issues = validate_planning_result(request, draft, parse_issues)
    if _json(asdict(result)) != _json(record["planning_result"]):
        raise ValueError("saved final plan does not match existing deterministic validation")
    return result, issues


def _planner_idle(planner):
    """Do not silently evict unrelated Ollama models or assume an unload request succeeded."""
    models = planner.api("/api/ps").get("models")
    if not isinstance(models, list) or any(not isinstance(item, dict) for item in models):
        raise ValueError("invalid Ollama residency response")
    names = [item.get("name", item.get("model")) for item in models]
    if any(name != planner.config.model for name in names):
        raise RuntimeError("an unrelated Ollama model is resident; cannot ensure sequential GPU use")
    if names:
        planner.unload()
        if planner.api("/api/ps").get("models") != []:
            raise RuntimeError("Qwen is still resident after unload")


def _release_captioner(captioner):
    if captioner is not None:
        captioner.model = None
        captioner.processor = None
    gc.collect()
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {"cuda_allocated_bytes_after": torch.cuda.memory_allocated() if torch.cuda.is_available() else None}


def run_pipeline(request: PipelineInput, config_dir: Path | None = None, *, grounding_factory=None) -> PipelineResult:
    """Create one immutable run directory. No generation-permission route exists in this milestone."""
    out = Path(request.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    config_dir = config_dir or Path(__file__).resolve().parents[2]/"configs"
    artifacts, events, completed, errors = {}, [], [], []
    stage = "source"
    start = time.perf_counter()

    def event(name, action, **details):
        events.append({"stage": name, "action": action, "seconds": time.perf_counter()-start, **details})

    def save(name, value):
        data = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n").encode("utf-8")
        (out/name).write_bytes(data)
        artifacts[name] = {"id": _sha(data), "sha256": _sha(data), "path": name}

    def reference(label, path, digest):
        data = Path(path).read_bytes()
        if _sha(data) != digest:
            raise ValueError(f"{label} SHA-256 mismatch")
        target = out/"evidence"/label/Path(path).name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        artifacts[label] = {"id": digest, "sha256": digest, "path": target.relative_to(out).as_posix()}
        return data

    def finish(state, stopped_at, reason, reviews=(), replay_validated=False):
        event(stopped_at, "STOP", state=state, reason=reason, generation_permitted=False)
        result = PipelineResult(request.execution_mode, state, tuple(completed), stopped_at, reason,
                                artifacts, tuple(events), tuple(reviews), tuple(errors), False, replay_validated)
        (out/"pipeline_result.json").write_text(json.dumps(asdict(result), indent=2, allow_nan=False), encoding="utf-8")
        return result

    try:
        save("pipeline_input.json", asdict(request))
        data = reference("source", request.source_image, request.image_sha256)
        with Image.open(BytesIO(data)) as source:
            image = source.convert("RGB")
        completed.append("source"); event(stage, "HASH_AND_IMAGE_VALIDATED")
        if request.execution_mode == "GROUNDING_TEST":
            from scripts.review_edit_intent import verify
            from scripts.review_grounding import prepare as prepare_boxes
            from transcreation.config import load_grounding_config
            from transcreation.stages.grounding import GroundingDetector, save_grounding_artifacts

            stage = "edit_intent_review"
            intent = request.edit_intent
            if intent is None:
                return finish(PipelineState.EDIT_INTENT_REQUIRES_REVIEW, stage, "Missing explicit edit-intent review; no localization permitted.")
            reference("edit_intent", intent.review_file, intent.review_sha256)
            record = verify(Path(intent.review_file))
            if (record["original_image_sha256"] != request.image_sha256
                    or record["source_culture"] != request.source_culture or record["target_culture"] != request.target_culture
                    or record["user_instructions"] != request.user_instructions
                    or _json(record["verified_objects"]) != _json([asdict(v) for v in request.verified_objects])):
                raise ValueError("continuation context differs from the reviewed image or plan")
            if record["decision"] == "REJECT":
                return finish(PipelineState.EDIT_INTENT_REJECTED, stage, "Reviewer rejected this edit intent; localization blocked.")
            if record["decision"] != "ACCEPT_FOR_GROUNDING_TEST":
                return finish(PipelineState.EDIT_INTENT_REQUIRES_REVIEW, stage, "Explicit acceptance is absent; localization blocked.")
            synthetic = record["evidence_scope"] == "SYNTHETIC_TEST_ONLY"
            if synthetic and grounding_factory is None:
                return finish(PipelineState.EDIT_INTENT_REQUIRES_REVIEW, stage, "Synthetic approvals cannot dispatch live models; offline mock required.")
            if grounding_factory is not None and not synthetic:
                raise ValueError("mock grounding injection is only permitted for synthetic test evidence")
            # Snapshot the full review bundle so the handoff remains independently auditable.
            from scripts.review_edit_intent import _proposal, _local
            binding, review_payload = _proposal(_local(Path(intent.review_file).parent, record["run_file"]),
                                          Path(request.source_image), record["candidate_index"], schema_version=record["schema_version"])
            if any(record.get(key) != value for key, value in binding.items()):
                raise ValueError("planning evidence changed during continuation")
            for name, raw in review_payload.items():
                target = out/"evidence"/"edit_intent"/"evidence"/name
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            pending = Path(intent.review_file).parent/record["pending_file"]
            pending_bytes = pending.read_bytes()
            if _sha(pending_bytes) != record["pending_sha256"]:
                raise ValueError("pending review changed during continuation")
            review_folder = out/"evidence"/"edit_intent"
            (review_folder/record["pending_file"]).write_bytes(pending_bytes)
            (review_folder/record["image_file"]).write_bytes(data)
            verify(review_folder/Path(intent.review_file).name)
            completed.append(stage); event(stage, "ACCEPTED_FOR_GROUNDING_ONLY", evidence_scope=record["evidence_scope"])
            if not synthetic:
                stage = "resource_preflight"
                _planner_idle(OllamaPlanner(load_planner_config(config_dir/"planner.yaml")))
                event(stage, "QWEN_NOT_RESIDENT")
            stage = "grounding"
            detector = None
            try:
                if (_sha(Path(intent.review_file).read_bytes()) != intent.review_sha256
                        or verify(Path(intent.review_file)) != record
                        or _sha(Path(request.source_image).read_bytes()) != request.image_sha256):
                    raise ValueError("review or source changed before grounding dispatch")
                detector = (grounding_factory or GroundingDetector)(load_grounding_config(config_dir/"grounding.yaml"))
                phrase = record["candidate"]["localization_phrase"]
                event(stage, "DISPATCH", source_phrase=phrase, execution="SYNTHETIC_MOCK" if synthetic else "LIVE")
                detected = detector.detect(Path(request.source_image), phrase)
                if detected.source_phrase != phrase or detected.image_sha256 != request.image_sha256:
                    raise ValueError("grounding output differs from reviewed source phrase or image")
                save_grounding_artifacts(Path(request.source_image), detected, out/"grounding")
                for name in ("detection.json", "comparison.png"):
                    raw = (out/"grounding"/name).read_bytes()
                    artifacts["grounding/"+name] = {"id": _sha(raw), "sha256": _sha(raw), "path": "grounding/"+name}
            finally:
                if detector is not None:
                    detector.close(); event(stage, "MODEL_RELEASED")
            if detected.status not in ("DETECTED", "NO_DETECTIONS"):
                raise ValueError(f"grounding failed: {detected.status}; {detected.observations}")
            completed.append(stage); event(stage, "COMPLETED", count=len(detected.detections))
            pending_boxes = prepare_boxes(out/"grounding"/"detection.json", Path(request.source_image), out/"box_review")
            reference("box_review", pending_boxes, _sha(pending_boxes.read_bytes()))
            return finish(PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, "box_review",
                          "All boxes retained; explicit box review required. No SAM or diffusion dispatched.", ("BOX_REVIEW_PENDING",))
        if request.execution_mode == "AUTOMATED_PLANNING":
            planner, captioner = None, None
            try:
                stage = "resource_preflight"
                planner = OllamaPlanner(load_planner_config(config_dir/"planner.yaml"))
                _planner_idle(planner); event(stage, "QWEN_NOT_RESIDENT")
                stage = "caption"
                try:
                    captioner = create_captioner(load_config(config_dir/"models.yaml"))
                    caption = captioner.caption(image)
                    if caption.image_dimensions is not None and tuple(caption.image_dimensions) != image.size:
                        raise ValueError("caption dimensions differ from the original image")
                    save("caption.json", {**asdict(caption), "input_sha256": request.image_sha256})
                    completed.append("caption"); event(stage, "CAPTION_COMPLETED")
                finally:
                    memory = _release_captioner(captioner); captioner = None
                    event("caption", "MODEL_REFERENCES_RELEASED", **memory)
                planning = PlanningInput.from_caption(caption, request.target_culture, source_culture=request.source_culture,
                                                      user_instructions=request.user_instructions, verified_objects=request.verified_objects)
                if _sha(Path(request.source_image).read_bytes()) != request.image_sha256:
                    raise ValueError("source image changed during captioning")
                save("planning_input.json", asdict(planning))
                stage = "planning"
                record = planner.record_plan(planning)
                save("planner_audit.json", record)
                plan, issues = validate_planner_audit(planning, record)
                if _sha(Path(request.source_image).read_bytes()) != request.image_sha256:
                    raise ValueError("source image changed during planning")
                save("validated_plan.json", {"planning_result": asdict(plan), "issues": issues})
                completed.extend(("planning", "deterministic_validation")); event(stage, "VALIDATED", decision=plan.decision)
            except Exception as exc:
                errors.append({"stage": stage, "type": type(exc).__name__, "message": str(exc)})
                raise
            finally:
                if planner is not None:
                    # record_plan already unloads normally. On unexpected errors unload explicitly,
                    # then confirm service residency before declaring cleanup successful.
                    try:
                        if not isinstance(getattr(planner, "last_record", None), dict) or planner.last_record.get("unload", {}).get("status") != "sent":
                            planner.unload()
                        _planner_idle(planner); event("planning", "QWEN_UNLOAD_CONFIRMED")
                    except Exception:
                        stage = "resource_cleanup"
                        raise
            if plan.decision == PlanningDecision.REVIEW:
                return finish(PipelineState.PLAN_REQUIRES_REVIEW, "planning_review", "Validated REVIEW; no draft or quarantined candidate is executable.", plan.verification_requirements)
            if plan.decision == PlanningDecision.ABSTAIN:
                return finish(PipelineState.NO_EDIT_JUSTIFIED, "planning", "Validated ABSTAIN; terminate without editing.")
            return finish(PipelineState.EDIT_PROPOSAL_READY, "edit_intent_review",
                          "PROPOSE is only a draft. No existing record authorizes edit intent or cultural generation; localization was not invoked.",
                          ("Explicit edit-intent review required", *plan.verification_requirements))

        # RESEARCH_REPLAY validates files only. It does not run or approve the downstream stages.
        chain = request.replay
        from scripts.review_grounding import _evidence
        from scripts.review_mask import _bundle, _check, read_candidate
        stage = "grounding_evidence"
        raw = reference("grounding", chain.detection_file, chain.detection_sha256)
        grounding, _ = _evidence(data, raw)
        canonical = lambda text: text.strip().casefold().rstrip(".").strip()
        if canonical(grounding.source_phrase) != canonical(chain.source_phrase):
            return finish(PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, stage, "Requested source phrase does not match the recorded source query; replacements cannot substitute for originals.")
        completed.append(stage); event(stage, "EXISTING_ARTIFACT_VALIDATED", count=len(grounding.detections))
        if grounding.status != "DETECTED" or chain.prediction_index is None:
            return finish(PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, "box_selection", "No detection or no explicit instance selection; never choose highest score.")
        if chain.prediction_index >= len(grounding.detections):
            raise ValueError("selected grounding index does not exist")
        reviews = []
        if chain.box_review_file:
            stage = "box_review"
            raw = reference("box_review", chain.box_review_file, chain.box_review_sha256)
            try:
                from transcreation.stages.segmentation import load_segmentation_input
                load_segmentation_input(Path(request.source_image), Path(chain.detection_file), chain.prediction_index,
                                        False, Path(chain.box_review_file), "Read-only review binding check")
            except ValueError as exc:
                return finish(PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, stage, str(exc))
        else:
            reviews.append("BOX_REVIEW_MISSING")
        if not chain.segmentation_file or chain.mask_index is None or not chain.mask_sha256:
            return finish(PipelineState.MASK_REQUIRES_REVIEW, "mask_selection", "A bound SAM result and explicit mask index/hash are required.", reviews)
        stage = "segmentation_evidence"
        reference("segmentation", chain.segmentation_file, chain.segmentation_sha256)
        segmentation, payload = _bundle(Path(chain.segmentation_file))
        bound = segmentation.request
        if (bound.image_sha256 != request.image_sha256 or bound.detection_sha256 != chain.detection_sha256
                or bound.prediction_index != chain.prediction_index or bound.selected_detection != grounding.detections[chain.prediction_index]
                or canonical(bound.source_phrase) != canonical(chain.source_phrase)):
            raise ValueError("SAM result is bound to a different source/detection/selection")
        selected = [mask for mask in segmentation.masks if mask.index == chain.mask_index]
        if len(selected) != 1 or _sha(payload[selected[0].filename]) != chain.mask_sha256:
            raise ValueError("selected mask does not belong to this SAM result/hash")
        bundle = out/"evidence"/"sam_bundle"; bundle.mkdir()
        for name, content in payload.items():
            (bundle/name).write_bytes(content)
        artifacts["selected_mask"] = {"id": chain.mask_sha256, "sha256": chain.mask_sha256,
                                      "path": (bundle/selected[0].filename).relative_to(out).as_posix()}
        completed.append(stage); event(stage, "EXISTING_ARTIFACT_VALIDATED", selection_status=bound.selection_status)
        if chain.mask_review_file:
            stage = "mask_review"
            raw = reference("mask_review", chain.mask_review_file, chain.mask_review_sha256)
            record = json.loads(raw); _check(record, Path(chain.mask_review_file).parent)
            if record.get("decision") not in ("PENDING", "REJECT", "NEEDS_REVIEW", "ACCEPT_FOR_SEGMENTATION_TEST"):
                raise ValueError("unknown mask-review decision")
            if record["segmentation_json_sha256"] != chain.segmentation_sha256 or record["candidate_index"] != chain.mask_index:
                raise ValueError("mask review is bound to a different result/selection")
            if record["decision"] == "ACCEPT_FOR_SEGMENTATION_TEST":
                read_candidate(Path(chain.mask_review_file))
            else:
                reviews.append("MASK_REVIEW_"+record["decision"])
        else:
            reviews.append("MASK_REVIEW_MISSING")
        if chain.inpainting_file:
            stage = "inpainting_evidence"
            raw = reference("inpainting", chain.inpainting_file, chain.inpainting_sha256)
            saved = json.loads(raw)
            if saved.get("status") != "COMPLETED":
                raise ValueError(f"saved inpainting failed: {saved.get('observations')}")
            previous = saved["request"]
            if (saved.get("scope") != "RESEARCH_ONLY" or previous["scope"] != "RESEARCH_ONLY"
                    or saved.get("human_approved") is not False or saved.get("cultural_edit_authorized") is not False
                    or previous["image_sha256"] != request.image_sha256
                    or previous["segmentation_sha256"] != chain.segmentation_sha256
                    or previous["candidate_index"] != chain.mask_index or previous["mask_sha256"] != chain.mask_sha256
                    or previous["prompt"] != chain.fixed_generation_prompt):
                raise ValueError("saved generation is not bound to the requested independent research chain")
            sam_provenance = {"model_id": segmentation.model_id, "revision": segmentation.resolved_revision,
                              "grounding_index": bound.prediction_index, "grounding_box": list(bound.selected_detection.box),
                              "detection_sha256": bound.detection_sha256, "point_sha256": bound.point_prompt_sha256,
                              "selection_status": bound.selection_status}
            if any(saved.get("source_sam", {}).get(key) != value for key, value in sam_provenance.items()):
                raise ValueError("generation SAM provenance mismatch")
            for name, digest in saved["artifact_sha256"].items():
                p = (Path(chain.inpainting_file).parent/name).resolve()
                if not p.is_relative_to(Path(chain.inpainting_file).parent.resolve()) or _sha(p.read_bytes()) != digest:
                    raise ValueError("saved inpainting artifact hash mismatch")
            final = Path(chain.inpainting_file).parent/"final.png"
            import numpy as np
            with Image.open(final) as generated:
                rgb = np.asarray(generated.convert("RGB"))
            with Image.open(BytesIO(payload[selected[0].filename])) as mask:
                editable = np.asarray(mask) == 255
            if rgb.shape != np.asarray(image).shape or not np.array_equal(rgb[~editable], np.asarray(image)[~editable]):
                raise ValueError("saved output changes pixels outside the selected original mask")
            reference("existing_final_image", str(final), saved["artifact_sha256"]["final.png"])
            completed.append(stage); event(stage, "EXISTING_OUTPUT_VERIFIED_NOT_GENERATED")
        if "BOX_REVIEW_MISSING" in reviews:
            return finish(PipelineState.SOURCE_OBJECT_REQUIRES_REVIEW, "box_review", "Research chain integrity verified; missing box review prevents approved execution.", reviews, True)
        if reviews:
            return finish(PipelineState.MASK_REQUIRES_REVIEW, "mask_review", "Research chain integrity verified; mask is not accepted. No models executed.", reviews, True)
        return finish(PipelineState.RESEARCH_REPLAY_VALIDATED, "generation_authorization",
                      "Existing research chain validated only. Segmentation-test acceptances are not cultural edit authorization; no generation permitted.",
                      ("EDIT_AUTHORIZATION_NOT_IMPLEMENTED", "INPAINTING_CONTRACT_IS_RESEARCH_ONLY"), True)
    except Exception as exc:
        error = {"stage": stage, "type": type(exc).__name__, "code": getattr(exc, "code", type(exc).__name__), "message": str(exc)}
        errors.append(error); event(stage, "FAILED", error=error)
        return finish(PipelineState.FAILED, stage, str(exc))
