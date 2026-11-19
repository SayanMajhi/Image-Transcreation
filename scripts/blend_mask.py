"""One fixed mask-constrained Gaussian blending experiment; CPU only, no model imports."""
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

RADIUS = 5


def constrained_blend(original: Image.Image, hard: Image.Image, mask: Image.Image):
    """Return RGB result and the exact 8-bit alpha coefficients (divide by 255)."""
    if original.mode != "RGB" or hard.mode != "RGB" or original.size != hard.size:
        raise ValueError("original and hard composite must be matching RGB images")
    if mask.mode != "L" or mask.size != original.size or not set(mask.tobytes()).issubset({0, 255}):
        raise ValueError("mask must be matching grayscale binary 0/255")
    if mask.getbbox() is None:
        raise ValueError("editable mask cannot be empty")
    source = np.asarray(original)
    generated = np.asarray(hard)
    editable = np.asarray(mask) == 255
    if not np.array_equal(source[~editable], generated[~editable]):
        raise ValueError("hard composite changes pixels outside the original mask")
    softened = np.asarray(mask.filter(ImageFilter.GaussianBlur(radius=RADIUS)), dtype=np.float64) / 255.0
    alpha = editable.astype(np.float64) * softened
    if np.any(alpha[~editable] != 0):
        raise ValueError("FAILED: alpha footprint extends outside the original mask")
    mixed = alpha[..., None] * generated.astype(np.float64) + (1.0-alpha[..., None]) * source.astype(np.float64)
    rgb = np.clip(np.rint(mixed), 0, 255).astype(np.uint8)  # nearest, ties to even
    rgb[~editable] = source[~editable]
    if not np.array_equal(rgb[~editable], source[~editable]):
        raise ValueError("FAILED: output changes pixels outside the original mask")
    # Pillow's blurred uint8 values make this PNG an exact encoding of the applied coefficients.
    alpha_bytes = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    return Image.fromarray(rgb), Image.fromarray(alpha_bytes)


def run_blend(source_image: Path, mask_file: Path, hard_image: Path, expected_hashes: dict[str, str], out: Path) -> dict:
    paths = {"source_image": source_image, "mask_file": mask_file, "hard_image": hard_image}
    if set(expected_hashes) != set(paths):
        raise ValueError("pin all three input SHA-256 values")
    inputs = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()}
    if hashes != expected_hashes:
        raise ValueError("input SHA-256 mismatch")
    with Image.open(BytesIO(inputs["source_image"])) as image:
        original = image.convert("RGB")
    with Image.open(BytesIO(inputs["hard_image"])) as image:
        hard = image.convert("RGB")
    with Image.open(BytesIO(inputs["mask_file"])) as image:
        mask = image.copy()  # never coerce a nonbinary or RGB mask into validity
    start = time.perf_counter()
    final, alpha = constrained_blend(original, hard, mask)
    seconds = time.perf_counter()-start
    out.mkdir(parents=True, exist_ok=False)
    (out / ("original"+source_image.suffix.lower())).write_bytes(inputs["source_image"])
    (out / "original_mask.png").write_bytes(inputs["mask_file"])
    (out / "iteration2_final.png").write_bytes(inputs["hard_image"])
    alpha.save(out / "alpha.png")
    final.save(out / "final.png")
    source, generated = np.asarray(original), np.asarray(hard)
    with Image.open(out / "final.png") as saved:
        actual = np.asarray(saved)
    editable = np.asarray(mask) == 255
    weights = np.asarray(alpha)
    changed = np.any(actual != source, axis=2)
    differs = np.any(actual != generated, axis=2)
    metrics = {"image_dimensions": list(original.size), "mask_dimensions": list(mask.size),
               "editable_pixels": int(editable.sum()), "nonzero_alpha_pixels": int(np.count_nonzero(weights)),
               "nonzero_alpha_outside_mask": int(np.count_nonzero(weights[~editable])),
               "partial_alpha_pixels": int(np.count_nonzero((weights > 0) & (weights < 255))),
               "full_alpha_pixels": int(np.count_nonzero(weights == 255)),
               "changed_inside_mask": int((changed & editable).sum()), "changed_outside_mask": int((changed & ~editable).sum()),
               "max_outside_channel_difference": int(np.abs(actual.astype(np.int16)-source.astype(np.int16))[~editable].max(initial=0)),
               "different_from_hard_pixels": int(differs.sum()), "different_from_hard_outside": int((differs & ~editable).sum())}
    if metrics["nonzero_alpha_outside_mask"] or metrics["changed_outside_mask"]:
        raise ValueError("FAILED: saved alpha/output escaped the original mask")
    result = {"status": "COMPLETED", "scope": "RESEARCH_ONLY", "human_approved": False, "cultural_edit_authorized": False,
              "method": "M * GaussianBlur(M, radius=5), then alpha*hard + (1-alpha)*original",
              "radius_original_pixels": RADIUS, "implementation": "Pillow GaussianBlur on uint8 L mask; normalize blurred values to float64 [0,1]",
              "alpha_encoding": "alpha.png L uint8; actual applied alpha = pixel / 255",
              "rounding": "numpy.rint ties-to-even; clip [0,255]; uint8", "input_sha256": hashes,
              "metrics": metrics, "timing": {"blend_seconds": seconds}, "model_inference_calls": 0,
              "libraries_present": {name: name in sys.modules for name in ("torch", "transformers", "diffusers")},
              "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}}
    (out / "blending.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Pinned three-source RESEARCH_ONLY request")
    parser.add_argument("--out", type=Path, required=True, help="New directory only")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.input.read_text(encoding="utf-8"))
        if request["scope"] != "RESEARCH_ONLY":
            raise ValueError("explicit isolated research scope required")
        result = run_blend(Path(request["source_image"]), Path(request["mask_file"]), Path(request["hard_image"]), request["sha256"], args.out)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
