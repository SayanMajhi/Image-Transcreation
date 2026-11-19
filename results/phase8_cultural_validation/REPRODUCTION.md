# Phase 8 review bundle

**Technical fallback feasibility demonstrated; cultural success PENDING_HUMAN_EVALUATION.** No overall cultural PASS or approved automatic edit is claimed. Both generated candidates, including the known seed42 failure, are included. Seed43 is a provisional samosa-like replacement with realism/boundary concerns. Six-case pilot not started.

Read `reports/cultural_transcreation_validation.md`. Inspect `results/phase8_cultural_validation/case1/comparison.png` and native close-ups. Source: Croissant, Petr Kratochvil, CC0; exact source/credit and all region/condition PNGs are supplied.

## Recorded environment

Python 3.11.9, Torch 2.15.0+cu132, Transformers 4.57.6, Diffusers 0.35.2, Accelerate 1.11.0, Pillow 13.0.0, NumPy 2.4.6, OpenCV-headless 5.0.0.93. The local RTX 3050 Laptop has 4 GB VRAM; tested fallback uses FP16 and sequential CPU offload. T4 and FLUX execution are NOT established. Use an appropriate CUDA Torch build; the recorded dependency versions and exact model pins/checksums are evidence, not a promise that every platform reproduces identical GPU pixels.

From the extracted package/repository root:

```powershell
python -m pip install -e ".[cultural-validation]"
$env:PYTHONPATH = (Resolve-Path src).Path
python -B results/phase8_cultural_validation/fetch_fallback_weights.py
$env:HF_HUB_OFFLINE = "1"
python -B -m scripts.instruction_edit --input results/phase8_cultural_validation/case1/reproduce_request_seed_42.json --config results/phase8_cultural_validation/case1/editor_config.json --out outputs/phase8_reproduction_seed42
python -B -m scripts.instruction_edit --input results/phase8_cultural_validation/case1/reproduce_request_seed_43.json --config results/phase8_cultural_validation/case1/editor_config.json --out outputs/phase8_reproduction_seed43
python -B results/phase8_cultural_validation/verify_outputs.py
python -B -m unittest discover -s tests -v
```

Weight fetch verifies pinned safetensor SHA-256s and supports the same bounded range repair used in this run. Weights remain outside this review ZIP. Use fresh output directories. No paid service is used. The original runtime request JSONs are unchanged; reproduce_request copies normalize only Windows path separators. Hashes, prompts, seed and geometry stay identical. Full source/SAM bundles are included for audit; old Windows path strings in those immutable records do not grant permission or alter source identity.

The verification script reopens INCLUDED outputs. For fresh generations, apply the same original/mask/protected RGB comparisons to their saved PNGs. No third live generation was performed simply to assert bitwise reproducibility under the two-candidate budget. Offline extracted-package tests and saved-artifact integrity can be reproduced without any weights.

## Human evaluation

Only distribute `results/phase8_cultural_validation/human_evaluation/reviewer_materials/` to three independent actual reviewers, including target-culture familiarity. Keep the admin blinding key, labeled report, model metadata and assistant assessments hidden until responses are complete. The form is header-only; no invented identities, ratings or acceptance records exist. Actual cultural ratings remain pending. Historical ramen decisions are not approvals for this case.

## Scope and omissions

All old application/model/review behavior is preserved. New work is an isolated instruction editor/CLI, 20 focused tests and an optional dependency extra. No new SD1.5 calls or prompt tuning occurred. Historical spaghetti comparison figures are explicitly unmatched-source negative evidence; the classical croissant baseline is matched-source but cannot replace object identity.

This bundle contains current case inputs, raw/final outputs, masks/control prototype, human forms, measured runtime, tests, exact model metadata, relevant implementation and checksums. It excludes pretrained weights, caches, environments, credentials, PDF reader wheels, full third-party papers/HTML pages and unrelated old ZIPs. Literature/source URLs and read-document hashes are retained for provenance. Historical research remains unchanged locally.
