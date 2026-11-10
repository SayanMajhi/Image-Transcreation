"""One-call experiment harness; delegates unchanged inference, aborts instead of retrying OOM."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
os.chdir(ROOT)

import torch
from transcreation.config import load_inpainting_config
from transcreation.contracts import InpaintingInput
from transcreation.stages import inpainting

HERE = Path(__file__).resolve().parent


def main():
    registration = json.loads((HERE / "preregistration.json").read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(HERE / "input.json") == registration["input_sha256"]
    assert sha(ROOT / "configs/inpainting.yaml") == registration["config_sha256"]
    assert json.loads((HERE / "tests.json").read_text())["returncode"] == 0
    snapshot = json.loads((HERE / "preservation_before.json").read_text())
    assert all(sha(ROOT / p) == value for p, value in snapshot.items())
    original_loader = inpainting.load_pipeline
    calls = []

    class Once:
        def __init__(self, pipeline):
            self.pipeline = pipeline

        def __getattr__(self, name):
            return getattr(self.pipeline, name)

        def __call__(self, **kwargs):
            if calls:
                raise RuntimeError("Only one generation call is permitted")
            calls.append({"prompt": kwargs["prompt"], "seed": kwargs["generator"].initial_seed()})
            try:
                return self.pipeline(**kwargs)
            except torch.cuda.OutOfMemoryError as exc:
                # The stage's existing OOM fallback must not create a second call in this iteration.
                raise RuntimeError(f"CUDA OOM; experiment stopped without retry: {exc}") from exc

    gpu_before = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                                capture_output=True, text=True).stdout
    start = time.perf_counter()
    request = InpaintingInput(**json.loads((HERE / "input.json").read_text()))
    config = load_inpainting_config(ROOT / "configs/inpainting.yaml")
    with patch.object(inpainting, "load_pipeline", side_effect=lambda cfg: Once(original_loader(cfg))):
        result = inpainting.run_inpainting(request, config, HERE / "run")
    metadata = {"generation_calls": len(calls), "calls": calls, "stage_call_wall_seconds": time.perf_counter()-start,
                "status": result["status"], "gpu_before": gpu_before, "retry_permitted": False,
                "implementation": "Unmodified stage/model loader/sampler; harness only enforces at most one call."}
    (HERE / "invocation.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    if result["status"] != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
