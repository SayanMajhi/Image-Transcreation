"""Isolated diffusion research with exact, binary-mask-restricted final compositing."""
from dataclasses import asdict
from io import BytesIO
import gc
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw
import torch

from transcreation.config import InpaintingConfig
from transcreation.contracts import InpaintingInput


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_inputs(request: InpaintingInput):
    # Reuse the existing portable SAM integrity checks; no review implies edit permission.
    from scripts.review_mask import _bundle

    segmentation = Path(request.segmentation_file)
    if digest(segmentation.read_bytes()) != request.segmentation_sha256:
        raise ValueError("segmentation JSON SHA-256 mismatch")
    result, payload = _bundle(segmentation)
    candidates = [mask for mask in result.masks if mask.index == request.candidate_index]
    if len(candidates) != 1:
        raise ValueError("selected candidate index is absent or ambiguous")
    candidate = candidates[0]
    mask_path = segmentation.parent / candidate.filename
    if Path(request.mask_file).resolve() != mask_path.resolve():
        raise ValueError("selected mask must belong to the referenced SAM result")
    image_bytes = Path(request.source_image).read_bytes()
    if digest(image_bytes) != request.image_sha256 or request.image_sha256 != result.request.image_sha256:
        raise ValueError("source image SHA-256 mismatch")
    if digest(payload[candidate.filename]) != request.mask_sha256:
        raise ValueError("selected mask SHA-256 mismatch")
    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")
    with Image.open(BytesIO(payload[candidate.filename])) as source:
        mask = source.copy()
    validate_mask(image, mask)
    return image, mask, result, payload


def validate_mask(image: Image.Image, mask: Image.Image) -> None:
    if mask.mode != "L" or mask.size != image.size or not set(mask.tobytes()).issubset({0, 255}):
        raise ValueError("mask must be original-resolution grayscale binary 0/255")
    if mask.getbbox() is None:
        raise ValueError("editable mask cannot be empty")


def prepare_crop(image: Image.Image, mask: Image.Image, config: InpaintingConfig):
    validate_mask(image, mask)
    x0, y0, x1, y1 = mask.getbbox()
    margin = config.context_margin
    box = (max(0, x0 - margin), max(0, y0 - margin), min(image.width, x1 + margin), min(image.height, y1 + margin))
    cropped = image.crop(box)
    cropped_mask = mask.crop(box)
    width, height = cropped.size
    side = max(width, height)
    left, top = (side - width) // 2, (side - height) // 2
    right, bottom = side - width - left, side - height - top
    padded = Image.fromarray(np.pad(np.asarray(cropped), ((top, bottom), (left, right), (0, 0)), mode="edge"))
    padded_mask = Image.new("L", (side, side), 0)
    padded_mask.paste(cropped_mask, (left, top))
    size = (config.processing_size,) * 2
    geometry = {"crop_box_xyxy": list(box), "padding_ltrb": [left, top, right, bottom], "padded_side": side,
                "original_dimensions": list(image.size), "processing_size": config.processing_size,
                "image_resize": "LANCZOS", "mask_resize": "NEAREST", "padding": "edge RGB; zero mask"}
    return padded.resize(size, Image.Resampling.LANCZOS), padded_mask.resize(size, Image.Resampling.NEAREST), geometry


def restore_and_composite(image: Image.Image, mask: Image.Image, raw: Image.Image, geometry: dict):
    validate_mask(image, mask)
    if raw.mode != "RGB" or raw.size != (geometry["processing_size"],) * 2:
        raise ValueError("unexpected generated crop mode or dimensions")
    x0, y0, x1, y1 = geometry["crop_box_xyxy"]
    if any(type(v) is not int for v in (x0, y0, x1, y1)) or not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
        raise ValueError("invalid original-image crop coordinates")
    mx0,my0,mx1,my1=mask.getbbox()
    if not (x0 <= mx0 < mx1 <= x1 and y0 <= my0 < my1 <= y1):
        raise ValueError("crop must contain the entire original editable mask")
    left, top, right, bottom = geometry["padding_ltrb"]
    side = geometry["padded_side"]
    if any(type(v) is not int or v < 0 for v in (left, top, right, bottom)) or (side - left - right, side - top - bottom) != (x1-x0, y1-y0):
        raise ValueError("padding/crop dimensions disagree")
    square = raw.resize((side, side), Image.Resampling.LANCZOS)
    restored = square.crop((left, top, side-right, side-bottom))
    canvas = image.copy()
    canvas.paste(restored, (x0, y0))
    final = Image.composite(canvas, image, mask)  # use the ORIGINAL binary mask, never the processing mask
    original_pixels, final_pixels = np.asarray(image), np.asarray(final)
    changed = np.any(original_pixels != final_pixels, axis=2)
    editable = np.asarray(mask) == 255
    metrics = {"editable_pixels": int(editable.sum()), "changed_inside_mask": int((changed & editable).sum()),
               "changed_outside_mask": int((changed & ~editable).sum()), "dimensions": list(final.size)}
    if metrics["changed_outside_mask"]:
        raise ValueError("final image changed outside the original editable mask")
    region = canvas.convert("RGBA")
    region.putalpha(mask)
    return final, restored, region, metrics


def load_pipeline(config: InpaintingConfig):
    # Lazy import/download: offline tests replace this function and never load weights.
    from diffusers import StableDiffusionInpaintPipeline
    from huggingface_hub import snapshot_download

    folder = Path(snapshot_download(config.model_id, revision=config.revision,
                                   allow_patterns=["*.json", "tokenizer/*.txt", "*/*.fp16.safetensors"]))
    if folder.name != config.revision:
        raise ValueError("resolved checkpoint revision differs from requested pin")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(str(folder), torch_dtype=torch.float16,
                                                         variant="fp16", use_safetensors=True, local_files_only=True)
    if pipe.unet.config.in_channels != 9:
        raise ValueError("expected dedicated 9-channel inpainting UNet")
    for component in (pipe.unet, pipe.vae, pipe.text_encoder, pipe.safety_checker):
        if component is not None:
            component.eval()
    pipe.enable_model_cpu_offload(gpu_id=0)
    return pipe


def _visuals(image, mask, final, geometry, out):
    overlay = Image.composite(Image.new("RGB", image.size, "lime"), image, mask.point(lambda p: 90 if p else 0))
    comparison = Image.new("RGB", (image.width*3, image.height+40), "white")
    for col, (view, title) in enumerate([(image,"original"),(overlay,"original SAM mask"),(final,"RESEARCH_ONLY final; no cultural adaptation claim")]):
        comparison.paste(view, (image.width*col,40)); ImageDraw.Draw(comparison).text((image.width*col+8,12),title,fill="black")
    comparison.save(out/"comparison.png")
    box=geometry["crop_box_xyxy"]; width,height=image.crop(box).size
    detail=Image.new("RGB",(width*2,height+40),"white")
    for col,view in enumerate([image.crop(box),final.crop(box)]):
        detail.paste(view,(col*width,40)); ImageDraw.Draw(detail).text((col*width+8,12),"original" if col==0 else "final hard composite",fill="black")
    detail.save(out/"detail.png")


def run_inpainting(request: InpaintingInput, config: InpaintingConfig, out: Path) -> dict:
    image, mask, sam, payload = validate_inputs(request)
    out.mkdir(parents=True, exist_ok=False)
    evidence=out/"evidence"; evidence.mkdir()
    for name,data in payload.items():
        (evidence/name).write_bytes(data)
    image.save(out/"source_decoded.png")
    model_image, model_mask, geometry=prepare_crop(image,mask,config)
    model_image.save(out/"processing_image.png"); model_mask.save(out/"processing_mask.png")
    report={"status":"ERROR","scope":"RESEARCH_ONLY","request":asdict(request),"model_id":config.model_id,
            "resolved_revision":config.revision,"settings":{**asdict(config),"precision":"float16","batch_size":1,
            "variant":"fp16","use_safetensors":True,"negative_prompt":None,"generator_device":"cpu",
            "initial_offload":"model_cpu_offload","allowed_oom_fallback":"sequential_cpu_offload"},
            "source_sam":{"model_id":sam.model_id,"revision":sam.resolved_revision,"grounding_index":sam.request.prediction_index,
                          "grounding_box":list(sam.request.selected_detection.box),"detection_sha256":sam.request.detection_sha256,
                          "point_sha256":sam.request.point_prompt_sha256,"selection_status":sam.request.selection_status},
            "geometry":geometry,"attempts":[],"timing":{},"memory":{},"observations":[],
            "cultural_edit_authorized":False,"human_approved":False}
    pipe=None; start=time.perf_counter()
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("this FP16 offloaded experiment requires CUDA; no silent device/model change")
        report["memory"]["initial_allocated_bytes"]=torch.cuda.memory_allocated()
        report["memory"]["free_total_before"]=list(torch.cuda.mem_get_info())
        loading=time.perf_counter(); pipe=load_pipeline(config)
        report["timing"]["load_seconds"]=time.perf_counter()-loading
        report["settings"]["scheduler"]=type(pipe.scheduler).__name__
        report["settings"]["scheduler_config"]=dict(pipe.scheduler.config)
        validate_inputs(request)  # detect source changes while loading/downloading
        for attempt,offload in enumerate(("model_cpu_offload","sequential_cpu_offload")):
            torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); t=time.perf_counter()
            try:
                with torch.inference_mode():
                    result=pipe(prompt=request.prompt,image=model_image,mask_image=model_mask,height=512,width=512,
                                num_inference_steps=config.steps,guidance_scale=config.guidance_scale,strength=config.strength,
                                num_images_per_prompt=1,generator=torch.Generator(device="cpu").manual_seed(config.seed))
                torch.cuda.synchronize()
                report["attempts"].append({"offload":offload,"status":"COMPLETED","seconds":time.perf_counter()-t,
                                          "peak_allocated_cuda_bytes":torch.cuda.max_memory_allocated()})
                break
            except torch.cuda.OutOfMemoryError as exc:
                report["attempts"].append({"offload":offload,"status":"CUDA_OOM","seconds":time.perf_counter()-t,
                                          "peak_allocated_cuda_bytes":torch.cuda.max_memory_allocated(),"error":str(exc)})
                if attempt: raise
                pipe.remove_all_hooks(); pipe.to("cpu"); gc.collect(); torch.cuda.empty_cache()
                pipe.enable_sequential_cpu_offload(gpu_id=0)  # one retry, same prompt/seed/settings
        raw=result.images[0]
        raw.save(out/"raw_generated_crop.png")
        report["safety_checker_flags"]=result.nsfw_content_detected
        if type(getattr(pipe,"num_timesteps",None)) is int:
            report["settings"]["effective_denoising_steps"]=pipe.num_timesteps
        if result.nsfw_content_detected and any(result.nsfw_content_detected):
            raise ValueError("pipeline safety checker flagged the result; no usable final image claimed")
        validate_inputs(request)
        final,restored,region,metrics=restore_and_composite(image,mask,raw,geometry)
        final.save(out/"final.png"); restored.save(out/"restored_crop.png"); region.save(out/"generated_region.png")
        with Image.open(out/"final.png") as saved:
            if saved.size!=image.size or not np.array_equal(np.asarray(saved)[np.asarray(mask)==0],np.asarray(image)[np.asarray(mask)==0]):
                raise ValueError("saved final PNG failed outside-mask equality")
        _visuals(image,mask,final,geometry,out)
        report["status"]="COMPLETED"; report["metrics"]=metrics
        report["timing"]["inference_seconds"]=report["attempts"][-1]["seconds"]
        report["memory"]["peak_allocated_cuda_bytes"]=max(a["peak_allocated_cuda_bytes"] for a in report["attempts"])
    except Exception as exc:
        report["observations"].append({"code":"INPAINTING_FAILED","type":type(exc).__name__,"message":str(exc)})
    finally:
        if pipe is not None:
            del pipe
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        report["timing"]["stage_seconds"]=time.perf_counter()-start
        report["artifact_sha256"]={p.relative_to(out).as_posix():digest(p.read_bytes()) for p in out.rglob('*') if p.is_file()}
        (out/"inpainting.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    return report
