# Culture-Aware Image Transcreation

A Python research application for user-directed cultural image adaptation while preserving the original scene. It combines image understanding, validated planning, object localization, segmentation and localized inpainting.

**Current status: partially complete.** All model components and a resumable guided research CLI are implemented. The original SAM masks were unsafe. Separate manually refined research masks now support real local ramen generations with exact outside-mask preservation. The latest two conditions remove the text-like artifact but still fail to produce convincing masala seasoning and lose some noodle structure. No culturally verified end-to-end transformation is claimed. [Current results and limitations](reports/phase7_integration.md).

## Architecture

```text
Automated: photo -> SmolVLM -> Qwen -> deterministic validation -> review gates
Guided research: explicit objective -> DINO -> selected box -> SAM -> selected mask
                 -> protected-pixel checks -> SD inpainting -> exact masked composite
```

Models: SmolVLM-500M-Instruct; Qwen2.5-3B through local Ollama; Grounding DINO Tiny; SAM ViT-Base; Stable Diffusion v1.5 Inpainting. Pinned revisions and effective settings live in `configs/` and run metadata. Models execute sequentially on the tested 4 GB RTX 3050 Laptop GPU; diffusion uses FP16 and CPU offloading.

PROPOSE is an unapproved draft. REVIEW quarantines candidates; ABSTAIN terminates without editing. Reviewed grounding/mask selections permit only their stated research use. The independent GUIDED_RESEARCH route never promotes a blocked Qwen plan or invents human approval. Binary hard compositing preserves decoded source pixels outside the selected mask; it cannot protect objects wrongly included inside that mask.

## Install

From the repository root, with Python 3.11 and a CUDA-compatible PyTorch installation:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[inpainting]"
$env:PYTHONPATH = (Resolve-Path src).Path
```

Use the tested dependency versions in [environment.json](results/phase7_integration/final_demo/environment.json). Real planning requires local Ollama with `qwen2.5:3b`. Model stages need the pinned checkpoints cached or downloaded on first use; offline tests do not download weights. No environment or weights are committed.

## Run

The configuration-driven entry point accepts an image/hash, source/target cultures, objective/instructions, output directory and execution mode. Guided research additionally requires an original-object query, fixed generation prompt and explicit research assumptions. Later steps require pinned evidence and explicit box/mask indices; no highest-score selection occurs.

```powershell
.venv\Scripts\python.exe -B -m transcreation.cli run --help
.venv\Scripts\python.exe -B -m transcreation.cli run --input path/to/new_request.json
```

Use [automated_request.json](results/phase7_integration/final_demo/automated_request.json) or [localization_request.json](results/phase7_integration/final_demo/localization_request.json) as examples. Copy to a new request and set `output_dir` to a fresh path; existing runs are immutable. Run from the project root. `AUTOMATED_PLANNING`, `GROUNDING_TEST`, `RESEARCH_REPLAY` and separate `GUIDED_RESEARCH` are supported.

A guided run stops after detection until you supply a source-bound detection/hash and prediction index. SAM then stops until you supply a segmentation/hash, candidate index, mask hash and inspection/limitation note. Inspect all alternatives against protected objects. Supplied protected sample pixels veto masks before inpainting; passing samples is not full mask approval. Existing real ramen masks are unsuitable and must not be presented as accepted.

Existing commands remain available:

```powershell
python -B -m transcreation.cli caption --help
python -B -m transcreation.cli plan --help
python -B -m transcreation.cli ground --help
python -B -m scripts.segment_sam --help
python -B -m scripts.inpaint --help
python -B -m scripts.review_grounding --help
python -B -m scripts.review_mask --help
```

## Tests

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$env:HF_HUB_OFFLINE = "1"
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Current completion run: **412 passed, zero failures/errors**. The suite includes mocked stage handoffs, evidence tampering, review/quarantine boundaries, resource cleanup and saved-pixel checks. Real inference results are reported separately.

## Repository and reports

- `src/transcreation/`: application, contracts, validation and model stages.
- `configs/`: pinned model/runtime settings.
- `scripts/`: independent stage and review utilities; `tests/`: offline regressions.
- `data/`: source images; `results/`: actual experiments; `.local_archive/`: historical reviews.
- [Phase 1: architecture](reports/phase1_research.md)
- [Phase 2: captioning](reports/phase2_vlm.md)
- [Phase 3: planning](reports/phase3_llm.md)
- [Phase 4: localization](reports/phase4_grounding.md)
- [Phase 5: segmentation](reports/phase5_segmentation.md)
- [Phase 6: inpainting experiments](reports/phase6_working.md)
- [Phase 7: current integration review](reports/phase7_integration.md)

Earlier phase reports describe their recorded milestones; the Phase 7 report gives current project status. [Actual ramen evidence](results/phase7_integration/final_demo), [all six masks comparison](results/phase7_integration/final_demo/ramen_evaluation.png), latest review ZIP: `results/final_project_review_v3.zip`. [Actual refined-mask output and failure analysis](results/phase7_integration/visual_v3/original_v2_A_B_comparison.png).

## Remaining work

The conservative local mask now excludes the protected objects, but generation quality remains inadequate. A complete-dish scope and convincing masala-noodle appearance remain unestablished. Caption/LLM errors, semantic false detections, mask leakage and diffusion artifacts remain possible. No annotated ground truth or independent cultural evaluation supports accuracy or cultural-correctness claims. Historical human review remains MATERIAL_UNRESOLVED; no approval has been fabricated. The next permitted work is targeted mask/scope correction and independent evaluation, not unrestricted generation.

Separate manually refined research generation (exact source/mask/protection provenance is supplied in the JSON; choose a fresh output):

```powershell
python -B -m scripts.inpaint --refined-input results/phase7_integration/refined_demo/input.json --out outputs/ramen_refined_reproduction
```

This reproduces the recorded failed visual condition, not an approved cultural edit. Original SAM-mask requests continue using `--input`.
