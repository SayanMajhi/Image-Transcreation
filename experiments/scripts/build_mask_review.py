"""Build a review-only food mask package from explicitly selected SAM candidates."""
from pathlib import Path
import json
import hashlib
import sys

import numpy as np
from PIL import Image, ImageDraw


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_mask_review.py REVIEW_DIR")
    root = Path(sys.argv[1])
    source = Path("data/chole_puri.jpg")
    puri = root / "sam_puri_0/mask_0.png"
    curry = root / "sam_curry_0/mask_0.png"
    output = root / "candidate_review"
    output.mkdir()

    with Image.open(source) as im:
        original = im.convert("RGB")
    with Image.open(puri) as im:
        puri_mask = im.convert("L")
    with Image.open(curry) as im:
        curry_mask = im.convert("L")
    if puri_mask.size != original.size or curry_mask.size != original.size:
        raise ValueError("candidate masks must match the native source dimensions")
    combined = Image.fromarray(np.maximum(np.asarray(puri_mask), np.asarray(curry_mask)).astype("uint8"), "L")
    if set(combined.getdata()) - {0, 255}:
        raise ValueError("combined mask must be binary")

    original.save(output / "original.png")
    combined.save(output / "candidate_food_mask.png")
    red = Image.new("RGB", original.size, (255, 0, 0))
    overlay = Image.composite(red, original, combined.point(lambda p: 105 if p else 0))
    overlay.save(output / "red_mask_overlay.png")

    bbox = combined.getbbox()
    if bbox:
        margin = 120
        x0, y0, x1, y1 = bbox
        close = original.crop((max(0, x0-margin), max(0, y0-margin),
                               min(original.width, x1+margin), min(original.height, y1+margin)))
        close_mask = combined.crop((max(0, x0-margin), max(0, y0-margin),
                                    min(original.width, x1+margin), min(original.height, y1+margin)))
        close_overlay = Image.composite(Image.new("RGB", close.size, (255, 0, 0)), close,
                                        close_mask.point(lambda p: 120 if p else 0))
        close_overlay.save(output / "difficult_boundaries_closeup.png")

    protected = Image.fromarray(np.where(np.asarray(combined) == 0, 255, 0).astype("uint8"), "L")
    protected.save(output / "protected_region_mask.png")
    protected_view = Image.composite(Image.new("RGB", original.size, (0, 120, 255)), original,
                                     protected.point(lambda p: 75 if p else 0))
    protected_view.save(output / "protected_region_visualization.png")

    report = {
        "status": "PENDING_USER_REVIEW",
        "source_image": str(source),
        "source_sha256": sha(source),
        "dimensions": list(original.size),
        "target_culture": "Japan",
        "editable_regions": ["puri", "chickpea curry"],
        "protected_regions": ["plate", "table", "utensils", "background", "unrelated objects"],
        "selected_candidates": {
            "puri": {"sam_mask": str(puri), "sha256": sha(puri), "candidate_index": 0},
            "chickpea_curry": {"sam_mask": str(curry), "sha256": sha(curry), "candidate_index": 0},
        },
        "combined_mask_sha256": sha(output / "candidate_food_mask.png"),
        "editable_pixels": int((np.asarray(combined) == 255).sum()),
        "editable_percentage": float((np.asarray(combined) == 255).mean() * 100),
        "approval_recorded": False,
        "notes": [
            "SAM candidates are automatic research outputs, not manual verification.",
            "Candidate 0 selections are provisional and require visual user review.",
            "No diffusion or image editing was run.",
        ],
    }
    (output / "review_status.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
