"""Explicit research photo compositing. No model, planning or approval dispatch."""
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

METHOD = "REFERENCE_GUIDED_COMPOSITING"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_object(source, reference, selection, permitted, protected, *,
                   scope, target_width, position, background_rgb, shadows,
                   edge_radius=1.0, reference_box=None, patch_fade_sigma=0):
    """Erase the whole declared region before placing ONE aspect-preserved cutout.

    Background reconstruction is appropriate only for an inspected uniform scene.
    This function does not infer object identity, lighting, boundaries or permission.
    patch_fade_sigma (reference pixels, default 0 = historical behaviour) fades the
    outer border of a rectangular photo patch so a slightly off-white reference
    studio background does not end in a hard line on the reconstructed plate.
    """
    if scope != "RESEARCH_ONLY":
        raise ValueError("reference replacement is exclusively RESEARCH_ONLY")
    if source.mode != "RGB" or reference.mode != "RGB":
        raise ValueError("RGB photographs required")
    for layer, size in ((selection, reference.size), (permitted, source.size),
                        (protected, source.size)):
        if layer.mode != "L" or layer.size != size or not set(layer.tobytes()) <= {0, 255}:
            raise ValueError("dimension-matched binary masks required")
    region = np.asarray(permitted) == 255
    if not region.any() or not selection.getbbox() or np.any(region & (np.asarray(protected) > 0)):
        raise ValueError("empty selection/region or protected intersection")
    if (not isinstance(target_width, int) or target_width <= 0 or
            not np.isfinite(edge_radius) or not 0 <= edge_radius <= 4):
        raise ValueError("invalid scale or edge radius")
    if (isinstance(patch_fade_sigma, bool) or not isinstance(patch_fade_sigma, (int, float)) or
            not np.isfinite(patch_fade_sigma) or not 0 <= patch_fade_sigma <= 200):
        raise ValueError("invalid patch fade")
    if len(background_rgb) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in background_rgb):
        raise ValueError("invalid inspected background color")
    box = tuple(reference_box) if reference_box is not None else selection.getbbox()
    if (len(box) != 4 or not 0 <= box[0] < box[2] <= reference.width or
            not 0 <= box[1] < box[3] <= reference.height):
        raise ValueError("invalid reference crop")
    support = selection.getbbox()
    if not (box[0] <= support[0] and box[1] <= support[1] and box[2] >= support[2] and box[3] >= support[3]):
        raise ValueError("reference crop truncates selected object")
    size = (target_width, round((box[3]-box[1]) * target_width / (box[2]-box[0])))
    x, y = position
    if not all(isinstance(v, int) for v in (x, y)) or x < 0 or y < 0 or x+size[0] > source.width or y+size[1] > source.height:
        raise ValueError("target outside source canvas")
    # Inward feather excludes reference-background RGB rather than blending it in.
    binary = selection.crop(box)
    softened = np.asarray(binary.filter(ImageFilter.GaussianBlur(edge_radius)), dtype=np.float32)
    alpha_values = softened * (np.asarray(binary) > 0)
    if patch_fade_sigma > 0:
        # Zero-pad first: PIL blur clamps at image borders, which would hide the crop edge.
        pad = int(np.ceil(3 * patch_fade_sigma)) + 1
        padded = Image.new("L", (binary.width + 2*pad, binary.height + 2*pad))
        padded.paste(binary, (pad, pad))
        blurred = np.asarray(padded.filter(ImageFilter.GaussianBlur(patch_fade_sigma)), dtype=np.float32)
        fade = np.clip(2 * blurred[pad:-pad, pad:-pad] / 255 - 1, 0, 1)
        alpha_values = alpha_values * fade
    alpha = Image.fromarray(np.rint(alpha_values).astype(np.uint8))
    cutout = reference.crop(box).resize(size, Image.Resampling.LANCZOS)
    alpha = alpha.resize(size, Image.Resampling.LANCZOS)
    full_alpha = Image.new("L", source.size)
    full_alpha.paste(alpha, (x, y))
    if np.any((np.asarray(full_alpha) > 0) & ~region):
        raise ValueError("target footprint outside permitted region")
    clean = np.asarray(source).copy()
    clean[region] = background_rgb  # no source object survives beneath the cutout
    shadow_alpha = np.zeros(region.shape, dtype=np.float32)
    for shadow in shadows:
        opacity, radius = shadow["opacity"], shadow["blur"]
        if not 0 <= opacity <= 1 or not 0 <= radius <= 100:
            raise ValueError("invalid documented shadow")
        layer = Image.new("L", source.size)
        ImageDraw.Draw(layer).ellipse(shadow["ellipse"], fill=255)
        shadow_alpha = np.maximum(shadow_alpha, np.asarray(layer.filter(ImageFilter.GaussianBlur(radius))) / 255 * opacity)
    # Restrict even the soft shadow to the declared region.
    shadow_alpha *= region
    shadowed = np.rint(clean * (1-shadow_alpha[..., None])).clip(0,255).astype(np.uint8)
    result = Image.fromarray(shadowed)
    result.paste(cutout, (x, y), alpha)
    final = np.asarray(result).copy()
    final[~region] = np.asarray(source)[~region]
    return Image.fromarray(final), Image.fromarray(clean), full_alpha, Image.fromarray(np.rint(shadow_alpha*255).astype(np.uint8))


def run_request(request_path, output):
    """Source-bound standalone research command; output directory must be new."""
    started = perf_counter()
    request_path, output = Path(request_path), Path(output)
    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
    if output.exists():
        raise FileExistsError(output)
    if request["method"] != METHOD or request["scope"] != "RESEARCH_ONLY":
        raise ValueError("not a reference-only research request")
    images = {}
    for key in ("source", "reference", "selection", "permitted", "protected"):
        evidence = request[key]
        path = request_path.parent / evidence["path"]
        if sha256(path) != evidence["sha256"]:
            raise ValueError(f"{key} SHA-256 mismatch")
        with Image.open(path) as im:
            images[key] = im.copy()
    if not request.get("attribution") or not request.get("annotation_method"):
        raise ValueError("reference attribution and annotation provenance required")
    final, clean, alpha, shadow = replace_object(**images, scope=request["scope"], **request["parameters"])
    output.mkdir(parents=True)
    for name, im in (("final",final),("source_removed",clean),("placed_alpha",alpha),("shadow_alpha",shadow)):
        im.save(output / f"{name}.png")
    metadata = {"method": METHOD, "scope":"RESEARCH_ONLY", "model":None,
                "approval":False, "request_sha256":sha256(request_path),
                "dimensions":list(final.size), "elapsed_seconds":perf_counter()-started,
                "target_bbox":alpha.getbbox(), "source_content_retained_in_removed_region":False,
                "outputs":{p.name:sha256(p) for p in output.glob("*.png")}}
    (output / "execution.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    return metadata
