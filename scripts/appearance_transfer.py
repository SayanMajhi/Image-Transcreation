"""Run the single frozen research baseline, verifying existing refined-mask provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time

from PIL import Image, features
from transcreation.stages.refined_inpainting import RefinedMaskInput, validate_refined_inputs
from transcreation.stages.appearance_transfer import SETTINGS, transfer_appearance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refined-input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    raw = Path(args.refined_input).read_bytes()
    request = RefinedMaskInput(**json.loads(raw))
    image, mask, _, _ = validate_refined_inputs(request)
    with Image.open(request.protected_mask_file) as im:
        protected = im.copy()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    # Preregister all numerical settings BEFORE transforming any pixels.
    (out / "frozen_settings.json").write_text(json.dumps(SETTINGS, indent=2))
    tick = time.perf_counter()
    result, alpha = transfer_appearance(image, mask, protected, scope=request.scope)
    transform_seconds = time.perf_counter() - tick
    result.save(out / "final.png")
    alpha.save(out / "alpha.png")
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    metadata = {"method": SETTINGS["method"], "scope": "RESEARCH_ONLY",
        "human_approved": False, "automated_edit_authorized": False,
        "input_sha256": hashlib.sha256(raw).hexdigest(), "request": json.loads(raw),
        "final_sha256": sha(out / "final.png"), "transform_seconds": transform_seconds,
        "process_seconds": time.perf_counter() - started, "device": "CPU", "cuda_memory": None,
        "python": platform.python_version(), "littlecms": features.version("littlecms2"),
        "new_model_calls": 0, "geometry_resampling": False,
        "note": "Frozen warm appearance cue, not recipe change or proof of cultural authenticity."}
    (out / "execution.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
