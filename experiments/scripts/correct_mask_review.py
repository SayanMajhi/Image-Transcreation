"""Apply the explicitly requested, bounded food-mask corrections for review."""
from pathlib import Path
import hashlib
import json
import sys

import cv2
import numpy as np
from PIL import Image


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlay(image: Image.Image, mask: np.ndarray, color: tuple[int, int, int], alpha: int) -> Image.Image:
    layer = Image.new("RGB", image.size, color)
    return Image.composite(layer, image, Image.fromarray((mask * alpha).astype("uint8")))


def remove_small_components(mask: np.ndarray, minimum: int) -> tuple[np.ndarray, list[dict]]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype("uint8"), 8)
    result = mask.copy()
    removed = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if area < minimum:
            result[labels == index] = False
            removed.append({"component": index, "area": area,
                            "bbox_xyxy": [int(stats[index, 0]), int(stats[index, 1]),
                                           int(stats[index, 0] + stats[index, 2]),
                                           int(stats[index, 1] + stats[index, 3])]})
    return result, removed


def fill_enclosed_holes(mask: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    inverse = (~mask).astype("uint8")
    count, labels, stats, _ = cv2.connectedComponentsWithStats(inverse, 8)
    result = mask.copy()
    filled = []
    height, width = mask.shape
    for index in range(1, count):
        x, y, w, h, area = map(int, stats[index])
        if x > 0 and y > 0 and x + w < width and y + h < height:
            result[labels == index] = True
            filled.append({"component": index, "area": area,
                           "bbox_xyxy": [x, y, x + w, y + h]})
    return result, filled


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: correct_mask_review.py REVIEW_DIR")
    root = Path(sys.argv[1])
    source = Path("data/chole_puri.jpg")
    before = root / "candidate_review"
    output = root / "corrected_review"
    output.mkdir()
    image = Image.open(source).convert("RGB")
    puri_before = np.asarray(Image.open(root / "sam_puri_0/mask_0.png").convert("L")) == 255
    curry_before = np.asarray(Image.open(root / "sam_curry_0/mask_0.png").convert("L")) == 255
    puri_after, removed_puri = remove_small_components(puri_before, minimum=1000)
    curry_after, filled_curry = fill_enclosed_holes(curry_before)
    combined_before = puri_before | curry_before
    combined_after = puri_after | curry_after
    for name, mask in (("puri", puri_after), ("curry", curry_after), ("combined", combined_after)):
        Image.fromarray((mask * 255).astype("uint8"), "L").save(output / f"{name}_mask.png")
    overlay(image, puri_after, (255, 0, 0), 105).save(output / "corrected_puri_overlay.png")
    overlay(image, curry_after, (255, 0, 0), 105).save(output / "corrected_curry_overlay.png")
    overlay(image, combined_after, (255, 0, 0), 105).save(output / "corrected_combined_overlay.png")
    diff = np.zeros((*combined_after.shape, 3), dtype="uint8")
    diff[(combined_before == 1) & (combined_after == 0)] = (0, 0, 255)
    diff[(combined_before == 0) & (combined_after == 1)] = (0, 255, 0)
    Image.fromarray(diff).save(output / "before_after_mask_difference.png")
    report = {
        "status": "PENDING_USER_REVIEW",
        "source": str(source), "source_sha256": sha(source), "dimensions": list(image.size),
        "before_directory": str(before),
        "preserved_candidate_masks": [
            str(root / "sam_puri_0/mask_0.png"), str(root / "sam_curry_0/mask_0.png")],
        "corrections": {
            "removed_puri_components": removed_puri,
            "filled_curry_enclosed_holes": filled_curry,
            "minimum_removed_component_area": 1000,
            "orange_sauce_and_upper_left_food": "not separately edited; no unrestricted morphology applied",
        },
        "pixel_counts": {
            "puri_before": int(puri_before.sum()), "puri_after": int(puri_after.sum()),
            "curry_before": int(curry_before.sum()), "curry_after": int(curry_after.sum()),
            "combined_before": int(combined_before.sum()), "combined_after": int(combined_after.sum()),
            "removed_combined": int((combined_before & ~combined_after).sum()),
            "added_combined": int((~combined_before & combined_after).sum()),
        },
        "hashes": {name: sha(output / f"{name}_mask.png") for name in ("puri", "curry", "combined")},
        "approval_recorded": False,
    }
    (output / "correction_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
