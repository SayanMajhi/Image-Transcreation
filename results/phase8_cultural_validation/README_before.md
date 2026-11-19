# Culture-Aware Image Transcreation

A Python research project for localized, user-directed cultural image reinterpretation with explicit evidence and review boundaries.

**Final assessment:** engineering and pixel preservation work; convincing generative food transcreation was not achieved. A deterministic baseline preserves texture better but provides warm recoloring, not a verified recipe transformation. The real automated example remains **REVIEW with zero released candidates**.

Read the [final report](reports/final_project_report.md), inspect the [original / SD A / SD B / baseline comparison](results/appearance_transfer_baseline/original_diffusion_baseline.png), and review `results/final_project_submission.zip`.

## Architecture

```text
Automated: photograph -> SmolVLM -> Qwen -> deterministic validator -> human review boundary
Guided RESEARCH_ONLY: explicit scope -> DINO -> SAM/refined mask -> provenance checks
                     -> SD inpainting OR classical appearance baseline -> pixel verification
```

All five models ran on real inputs in prior experiments: SmolVLM-500M, Ollama Qwen2.5-3B, Grounding DINO Tiny, SAM ViT-Base and SD v1.5 Inpainting. Pins/settings are in `configs/` and the final report. Code: `src/transcreation/`; commands: `scripts/`; offline tests: `tests/`; evidence: `results/`. Historical phase findings remain in `reports/` and archives.

PROPOSE is an unapproved draft. REVIEW/ABSTAIN cannot dispatch edits. Guided research uses a separate explicit scope and never promotes rejected plans or invents approvals. The appearance baseline is an isolated RESEARCH_ONLY command; no model or validation policy changed.

## Setup

Use Python 3.11. Model experiments used Windows and a 4 GB RTX 3050 Laptop GPU. Install the compatible CUDA Torch build first, then:

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -e ".[inpainting]"
$env:PYTHONPATH = (Resolve-Path src).Path
```

Model stages need pinned weights and local Ollama `qwen2.5:3b`; weights are not distributed. Models run sequentially; diffusion uses FP16 and CPU offloading. The deterministic baseline needs no downloaded weights or running Ollama. Tested versions are in `results/phase7_integration/v4_completed/environment.json`; baseline metadata records Pillow/LittleCMS versions.

## Execute

From the repository root, using a fresh output directory:

```powershell
python -B -m transcreation.cli run --help
python -B -m transcreation.cli run --input path/to/request.json
python -B -m scripts.appearance_transfer --refined-input results/phase7_integration/v4_completed/reproduce_input_A.json --out outputs/appearance_reproduction
```

The last command verifies source/SAM/annotation/mask hashes and runs one frozen classical treatment. It reuses a research provenance request; the old diffusion prompt is ignored. It cannot authorize an automated edit. Existing stage/review commands remain available via `--help`. No further diffusion tuning is recommended from these findings.

## Tests and results

```powershell
$env:HF_HUB_OFFLINE = "1"
python -B -m unittest discover -s tests -v
python -B results/appearance_transfer_baseline/verify_saved.py
```

**420 passed, zero failures** (412 existing + 8 focused baseline tests). Offline synthetic/mocked tests are separate from historical real inference. The baseline has zero outside-mask/protected-region changes. Inspect the [result](results/appearance_transfer_baseline/run/final.png), [native close-up](results/appearance_transfer_baseline/noodles_native.png) and [pixel verification](results/appearance_transfer_baseline/pixel_verification.json).

## Limitations

The baseline preserves geometry but produces mainly yellow/orange warming, not convincing reddish-brown masala sauce. Mask exclusions leave uneven transitions. Exact locality does not prove semantic segmentation or cultural authenticity. SD food experiments distorted texture and produced implausible inserts. Historical MATERIAL_UNRESOLVED reviews remain unchanged. No approved automated Qwen-to-image success is claimed. Research is finalized for evaluation with these negative findings; no new model experiments occurred during stabilization.
