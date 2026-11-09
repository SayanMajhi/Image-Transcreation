"""Fixed eight-condition missed-object study, negative control and baseline replay."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import time

import torch

from transcreation.config import load_grounding_config
from transcreation.stages.grounding import GroundingDetector, save_grounding_artifacts

ROOT = Path(__file__).resolve().parents[1]
# These conditions are declared before inference; do not extend after viewing results.
CONDITIONS = [
    ("R01_bicycle_replay", "reproducibility", "data/vlm_collection/scene_06.jpg", "bicycle", 0.30),
    ("A01_oil_lamp_030", "matrix", "data/vlm_collection/scene_02.jpg", "oil lamp", 0.30),
    ("A02_oil_lamp_020", "matrix", "data/vlm_collection/scene_02.jpg", "oil lamp", 0.20),
    ("A03_diya_030", "matrix", "data/vlm_collection/scene_02.jpg", "diya", 0.30),
    ("A04_diya_020", "matrix", "data/vlm_collection/scene_02.jpg", "diya", 0.20),
    ("B01_incense_burner_030", "matrix", "data/sample_images/durga.jpg", "incense burner", 0.30),
    ("B02_incense_burner_020", "matrix", "data/sample_images/durga.jpg", "incense burner", 0.20),
    ("B03_clay_incense_burner_030", "matrix", "data/sample_images/durga.jpg", "clay incense burner", 0.30),
    ("B04_clay_incense_burner_020", "matrix", "data/sample_images/durga.jpg", "clay incense burner", 0.20),
    ("N01_airplane_negative", "negative_control", "data/vlm_collection/scene_06.jpg", "airplane", 0.30),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New run directory only")
    args = parser.parse_args()
    config = load_grounding_config(ROOT / "configs/grounding.yaml")
    assert config.box_threshold == 0.30 and config.text_threshold == 0.25
    assert config.device == "cuda" and torch.cuda.is_available(), "study requires the baseline CUDA environment"
    assert version("transformers") == "4.57.6"
    args.out.mkdir(parents=True, exist_ok=False)
    plan = {"declared_at_utc": datetime.now(timezone.utc).isoformat(), "base_config": asdict(config),
            "conditions": [dict(zip(("id", "role", "input", "phrase", "box_threshold"), row)) for row in CONDITIONS],
            "negative_control_pre_inference_inspection": "Original bicycle image inspected before inference: parked bicycle, building facade, doors, graffiti and pavement. No recognizable airplane or plausible aircraft object is visibly present; abstract graffiti is not verified to depict every possible symbol.",
            "hypotheses": ["A lower box threshold may recover weaker repeated-object candidates, but can admit unrelated regions or duplicates.", "Alternative wording may change localization scores and extents; neither more detections nor culturally specific wording proves correctness.", "The negative query is expected to return no detections; any returned box must remain visible in the record."],
            "matrix_count": 8, "negative_control_count": 1, "unchanged_positive_baseline_replay_count": 1,
            "strategy": "One lazy-loaded model reused sequentially; baseline replay is an acceptance check, not an additional threshold/query variation."}
    (args.out / "experiment_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    detector = GroundingDetector(config)
    model_identity = None
    summaries = []
    try:
        for condition, role, source, phrase, threshold in CONDITIONS:
            reused = detector.model is not None
            detector.config = replace(config, box_threshold=threshold)
            result = detector.detect(ROOT / source, phrase)
            artifact_start = time.perf_counter()
            directory = args.out / condition
            save_grounding_artifacts(ROOT / source, result, directory)
            rejected = []
            for issue in result.observations:
                if issue.get("code") == "INVALID_BOX_OR_SCORE":
                    index = issue["index"]
                    rejected.append({"raw_index": index, "issue": issue,
                                     **{name: values[index] for name, values in result.raw_predictions.items()}})
            validation = {"status": result.status, "valid_predictions": [asdict(d) for d in result.detections],
                          "invalid_predictions": rejected, "observations": result.observations}
            (directory / "validation.json").write_text(json.dumps(validation, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            summaries.append({"id": condition, "role": role, "input": source, "phrase": phrase,
                              "normalized_prompt": result.settings["normalized_prompt"],
                              "box_threshold": threshold, "text_threshold": config.text_threshold,
                              "raw_returned_count": len(result.raw_predictions.get("boxes", [])),
                              "valid_count": len(result.detections), "invalid_count": len(rejected),
                              "status": result.status, "model_reused": reused,
                              "timing": result.timing, "memory": result.memory,
                              "artifact_seconds": time.perf_counter() - artifact_start})
            (args.out / "run_summary.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
            print(f"{condition}: {result.status}, {len(result.detections)} valid, {len(rejected)} invalid; inference {result.timing.get('inference_seconds', 0):.3f}s; reused={reused}", flush=True)
            if result.status == "ERROR" or result.memory["device"] != "cuda":
                raise RuntimeError("study stopped: condition failed or changed device; inspect saved audit")
            if model_identity is None:
                model_identity = id(detector.model)
            assert id(detector.model) == model_identity, "model unexpectedly reloaded"
    finally:
        detector.close()


if __name__ == "__main__":
    main()
