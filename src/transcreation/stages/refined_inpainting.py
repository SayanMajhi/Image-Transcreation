"""Source-bound polygon masks for isolated research; never predicted SAM masks.

Annotations record operator geometry, not human approval or ground-truth segmentation.
The existing diffusion implementation is shared without altering its model settings.
"""
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from transcreation.contracts import InpaintingInput
from transcreation.stages.inpainting import digest, validate_mask, _run_inpainting


ORIGIN = "RESEARCH_MASK_MANUALLY_REFINED"


@dataclass(frozen=True, kw_only=True)
class RefinedMaskInput(InpaintingInput):
    annotation_file: str
    annotation_sha256: str
    protected_mask_file: str
    protected_mask_sha256: str
    mask_origin: str
    negative_prompt: str | None = None

    def __post_init__(self):
        super().__post_init__()
        if self.negative_prompt is not None and (not isinstance(self.negative_prompt,str)
                or self.negative_prompt.strip().lower() in ("", "null", "none", "n/a")):
            raise ValueError("an explicit research negative prompt must be meaningful text or null")
        if self.mask_origin != ORIGIN:
            raise ValueError("derived mask must declare its actual manually refined research origin")
        for name in ("annotation_file", "protected_mask_file"):
            if not isinstance(getattr(self,name), str) or not getattr(self,name).strip():
                raise ValueError(f"{name} is required")
        for name in ("annotation_sha256", "protected_mask_sha256"):
            value = getattr(self,name)
            if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be SHA-256")


def rasterize_annotations(document: dict, size: tuple[int, int]):
    """Rasterize recorded original-coordinate polygons, subtracting all exclusions."""
    def layer(key):
        polygons = document.get(key)
        if not isinstance(polygons,list) or not polygons:
            raise ValueError(f"explicit {key} are required")
        result = Image.new("L",size,0)
        draw = ImageDraw.Draw(result)
        for polygon in polygons:
            points = polygon.get("points") if isinstance(polygon,dict) else None
            if (not isinstance(polygon,dict) or set(polygon)!={"label","points"}
                    or not isinstance(polygon["label"],str) or not polygon["label"].strip()
                    or not isinstance(points,list) or len(points)<3):
                raise ValueError("polygons require a label and at least three original-image XY points")
            if any(not isinstance(p,list) or len(p)!=2 or any(type(v) is not int for v in p)
                   or not (0<=p[0]<size[0] and 0<=p[1]<size[1]) for p in points):
                raise ValueError("polygon coordinates must be original-image integers within bounds")
            draw.polygon([tuple(p) for p in points],fill=255)
        return result
    editable, protected = layer("editable_polygons"), layer("protected_polygons")
    refined = Image.fromarray(np.where((np.asarray(editable)==255)&(np.asarray(protected)==0),255,0).astype('uint8'))
    return refined, protected


def validate_refined_inputs(request: RefinedMaskInput):
    from scripts.review_mask import _bundle

    if type(request) is not RefinedMaskInput:
        raise ValueError("refined research input is required; no planner or review record accepted")
    def read(path, expected):
        raw = Path(path).read_bytes()
        if digest(raw)!=expected:
            raise ValueError(f"SHA-256 mismatch: {path}")
        return raw
    segmentation = Path(request.segmentation_file)
    read(segmentation,request.segmentation_sha256)
    sam, payload = _bundle(segmentation)
    references = [m for m in sam.masks if m.index==request.candidate_index and m.status=="VALID"]
    if len(references)!=1:
        raise ValueError("explicit original SAM reference index is missing or ambiguous")
    if sam.request.image_sha256 != request.image_sha256:
        raise ValueError("SAM reference belongs to a different source image")
    source_bytes = read(request.source_image,request.image_sha256)
    with Image.open(BytesIO(source_bytes)) as source:
        image = source.convert("RGB")
    if image.size != sam.request.original_dimensions:
        raise ValueError("SAM/source dimensions differ")
    document_bytes = read(request.annotation_file,request.annotation_sha256)
    document = json.loads(document_bytes)
    expected_keys = {"scope","mask_origin","annotation_method","operator","human_approved",
                     "cultural_edit_authorized","source_image_sha256","original_dimensions",
                     "sam_result_sha256","sam_reference_index","sam_reference_mask_sha256",
                     "target_definition","boundary_reason","editable_polygons","protected_polygons"}
    if not isinstance(document,dict) or set(document)!=expected_keys:
        raise ValueError("missing or unexpected annotation fields; no approval/permission extensions accepted")
    if any(not isinstance(document[key],str) or not document[key].strip()
           for key in ("target_definition","boundary_reason")):
        raise ValueError("describe the research target and conservative boundary reasoning")
    if (document.get("scope")!="RESEARCH_ONLY" or document.get("mask_origin")!=ORIGIN
            or document.get("annotation_method")!="operator_polygon_trace_with_protected_exclusions"
            or not isinstance(document.get("operator"),str) or not document["operator"].strip()
            or document.get("human_approved") is not False or document.get("cultural_edit_authorized") is not False):
        raise ValueError("annotation must declare manual research provenance without approval claims")
    if (document.get("source_image_sha256")!=request.image_sha256
            or document.get("original_dimensions")!=list(image.size)
            or document.get("sam_result_sha256")!=request.segmentation_sha256
            or type(document.get("sam_reference_index")) is not int
            or document.get("sam_reference_index")!=request.candidate_index
            or document.get("sam_reference_mask_sha256")!=digest(payload[references[0].filename])):
        raise ValueError("annotation source/SAM binding conflicts with original evidence")
    expected_mask, expected_protected = rasterize_annotations(document,image.size)
    mask_bytes = read(request.mask_file,request.mask_sha256)
    protected_bytes = read(request.protected_mask_file,request.protected_mask_sha256)
    with Image.open(BytesIO(mask_bytes)) as source:
        if source.format!="PNG": raise ValueError("refined mask must be PNG")
        mask=source.copy()
    with Image.open(BytesIO(protected_bytes)) as source:
        if source.format!="PNG": raise ValueError("protected mask must be PNG")
        protected=source.copy()
    validate_mask(image,mask); validate_mask(image,protected)
    if np.any((np.asarray(mask)==255)&(np.asarray(protected)==255)):
        raise ValueError("refined mask intersects a full-region protected exclusion")
    if mask.tobytes()!=expected_mask.tobytes() or protected.tobytes()!=expected_protected.tobytes():
        raise ValueError("saved masks disagree with recorded polygon geometry")
    if digest(mask_bytes)==digest(payload[references[0].filename]):
        raise ValueError("derived mask must not masquerade as an unchanged SAM prediction")
    for name,data in {"refined_mask.png":mask_bytes,"protected_exclusions.png":protected_bytes,
                      "refinement_annotations.json":document_bytes}.items():
        if name in payload:
            raise ValueError("derived evidence filename conflicts with original SAM bundle")
        payload[name]=data
    return image,mask,sam,payload


def run_refined_inpainting(request, config, out, *, max_attempts=2):
    return _run_inpainting(request,config,out,validate_refined_inputs,mask_origin=ORIGIN,
                           negative_prompt=request.negative_prompt,max_attempts=max_attempts)
