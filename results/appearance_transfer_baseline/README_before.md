# Culture-Aware Image Transcreation

A Python research application for cultural image reinterpretation with explicit preservation constraints. All five model stages are implemented and have run on real photographs. **Project status: PARTIALLY COMPLETE.** V4 executed the complete bounded spaghetti research protocol, but both generated images failed the requested masala-coating/realism objective. Pixel preservation and all 412 regression tests passed.

Start with the [final project report](reports/final_project_report.md), [actual original/A/B comparison](results/phase7_integration/v4_completed/original_generated_comparison.png), and `results/final_project_review_v4_completed.zip`. Earlier [Phase 7 ramen findings](reports/phase7_integration.md) remain historical evidence.

## Architecture

```text
Automated: photograph -> SmolVLM -> Qwen -> deterministic validation -> review boundary
Guided RESEARCH_ONLY: explicit objective -> DINO -> selected box -> SAM/refined mask
                    -> SD inpainting -> original-resolution composite -> pixel checks
```

Models: SmolVLM-500M-Instruct, local Ollama Qwen2.5-3B, Grounding DINO Tiny, SAM ViT-Base and Stable Diffusion v1.5 Inpainting. Pinned settings are in `configs/`. Models run sequentially; diffusion uses FP16 and CPU model offloading on the tested 4 GB RTX 3050 Laptop GPU.

PROPOSE is an unapproved draft. REVIEW quarantines candidates; ABSTAIN stops. A separate research objective never promotes a rejected planner candidate or invents human approval. Mask hashes and hard compositing guarantee decoded source RGB outside the edit, not semantic mask correctness, food realism or cultural authenticity.

## Install and run

From the repository root, use Python 3.11 with a compatible CUDA Torch build and the [tested dependency versions](results/phase7_integration/v4_completed/environment.json):

```powershell
python -m pip install -e ".[inpainting]"
$env:PYTHONPATH = (Resolve-Path src).Path
python -B -m transcreation.cli run --help
python -B -m transcreation.cli run --input path/to/new_request.json
```

Configuration-driven modes are AUTOMATED_PLANNING, GROUNDING_TEST, RESEARCH_REPLAY and independent GUIDED_RESEARCH. See the [V4 request files and exact commands](reports/final_project_report.md). Use fresh output directories; existing evidence cannot be overwritten. Real stages require cached/downloaded pinned models and local Ollama as applicable. No weights or environment are included in the repository/package.

For the existing manually refined research-mask path:

```powershell
python -B -m scripts.inpaint --refined-input results/phase7_integration/v4_completed/reproduce_input_A.json --out outputs/v4_reproduction_A --max-attempts 1
```

This reproduces a recorded failed visual condition, not an approved cultural edit. Original SAM-mask inputs still use `--input`. Existing `caption`, `plan`, `ground`, `scripts.segment_sam` and review commands remain available with `--help`.

## Tests

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$env:HF_HUB_OFFLINE = "1"
python -B -m unittest discover -s tests -v
python -B results/phase7_integration/v4_completed/verify_outputs.py
```

Current full suite: **412 passed, zero failures/errors**. Unit/integration tests use mocked models; real inference is reported separately. Independent saved-pixel checks passed for both V4 generations.

## Structure and evidence

`src/transcreation/` contains application code and stages; `configs/` runtime settings; `scripts/` execution/review tools; `tests/` offline regressions; `data/` source inputs; `results/` actual evidence; `reports/` research summaries. Historical material is retained in `.local_archive/` and earlier result folders.

- [Phase 1](reports/phase1_research.md), [Phase 2](reports/phase2_vlm.md), [Phase 3](reports/phase3_llm.md), [Phase 4](reports/phase4_grounding.md), [Phase 5](reports/phase5_segmentation.md)
- [Phase 6 inpainting research](reports/phase6_working.md), [Phase 7 ramen findings](reports/phase7_integration.md)
- [Current final review](reports/final_project_report.md), [V4 source attribution](results/phase7_integration/v4_completed/ATTRIBUTION.md)

## Limitations

Qwen's real V4 proposal remained REVIEW with zero released candidates. Generated spaghetti has an unnatural red insert, weak sauce coverage and visible boundary artifacts. Original plate/background pixels are preserved exactly; that does not make the cultural adaptation credible. Historical human MATERIAL_UNRESOLVED decisions remain unchanged. No expert cultural certification, complete dish transformation or approved automated Qwen-to-diffusion result is claimed. Stop for mentor evaluation before any further experiment.
