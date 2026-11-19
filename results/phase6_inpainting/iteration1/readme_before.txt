# Culture-Aware Image Transcreation

An undergraduate research project investigating culturally contextual image adaptation while preserving the original scene's activity, people and relationships.

The project implements independent captioning, planning, localization, segmentation and review stages. **It does not yet perform image editing or complete end-to-end transcreation.** Phase 6 diffusion inpainting has not started.

## Implemented pipeline

```text
Image -> SmolVLM caption -> Qwen cultural draft -> deterministic validation
Independent research: Grounding DINO box -> explicit selection -> SAM masks -> mask review
```

- **SmolVLM-500M:** captioning with completion/truncation metadata.
- **Qwen2.5-3B / Ollama:** structured cultural suggestions, with raw/final audit records.
- **Validation:** PROPOSE remains conditional; REVIEW quarantines candidates; ABSTAIN requests no change. None authorizes editing.
- **Grounding DINO Tiny:** original-pixel bounding boxes and explicit box-review records.
- **SAM ViT-Base:** box and optional positive/negative point prompts; all three candidate masks retained.
- **Mask review:** hash-bound selection for a specified segmentation test only. No genuine human-approved mask is recorded.

Python 3.11, PyTorch, Transformers 4.57.6, Pillow and PyYAML. Recorded experiments used an RTX 3050 Laptop GPU with 4 GB VRAM. Run model stages sequentially.

## Structure

```text
configs/                   model/runtime settings, including sam.yaml
src/transcreation/         working application, contracts and validation
scripts/                   independent SAM, evaluation and review commands
tests/                     offline regression tests and fixtures
data/                      source images; mostly local and Git-ignored
outputs/                   new generated runs; Git-ignored
reports/                   exactly five final phase reports
results/phase2_vlm/         actual caption/comparison evidence
results/phase3_llm/         actual raw/validated planner trials
results/phase4_grounding/   detections, comparisons and box reviews
results/phase5_segmentation/ masks, point protocols and mask reviews
.local_archive/            historical development records and cleanup audits
```

[Relocation manifest](results/relocation_manifest.json) maps recorded old paths to current evidence. Saved model JSON remains byte-identical. Historical iteration documents and ZIPs are archived; the active reading path uses reports and results.

## Install

From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

Use a CUDA-compatible PyTorch build for GPU work. Pinned Hugging Face weights download on first uncached use. Planning requires local Ollama with `qwen2.5:3b` installed. Dataset inputs are not all committed; result bundles and manifests record their identity and provenance.

## Run

Commands are independent stages. Use fresh output paths; the planner reads a typed planning input, not the whole caption audit JSON.

```powershell
.\.venv\Scripts\python.exe -B -m transcreation.cli caption --image data/sample_images/durga.jpg --out outputs/caption_new.json
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/plan_new.json
.\.venv\Scripts\python.exe -B -m transcreation.cli ground --image data/vlm_collection/scene_06.jpg --phrase bicycle --out outputs/grounding_new
.\.venv\Scripts\python.exe -B -m scripts.segment_sam --image data/vlm_collection/scene_06.jpg --detection results/phase4_grounding/experiments/threshold_query/R01_bicycle_replay/detection.json --prediction-index 0 --research-only --note "Explicit bicycle segmentation test" --out outputs/sam_new
```

SAM accepts optional source-bound `--points` JSON. `transcreate caption|plan|ground` is also available after installation. Use each command's `--help` for options.

Prepare review evidence without inference:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.review_grounding prepare --image data/vlm_collection/scene_06.jpg --detection results/phase4_grounding/experiments/threshold_query/R01_bicycle_replay/detection.json --out outputs/box_review_new
.\.venv\Scripts\python.exe -B -m scripts.review_mask prepare --segmentation results/phase5_segmentation/experiments/box_points/B_oil_lamp/segmentation.json --candidates 0 1 --target "Visible clay bowl only; exclude flame" --experiment "Controlled segmentation test; no editing" --out outputs/mask_review_new
```

Preparation creates PENDING requests. A real reviewer must inspect the original, mask and overlay before submitting a named decision through `scripts.review_mask decide`. Acceptance is restricted to a segmentation experiment and does not authorize cultural editing.

## Tests

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
$env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

The offline suite uses mocks/synthetic fixtures and does not download model weights.

## Reports and experimental results

| Phase | Final report | Actual evidence |
| --- | --- | --- |
| 1 | [Research and architecture](reports/phase1_research.md) | Architecture; separate original Phase 1 experiment evidence unavailable |
| 2 | [VLM selection](reports/phase2_vlm.md) | [Captions and measurements](results/phase2_vlm/summary.md) |
| 3 | [Cultural planning](reports/phase3_llm.md) | [Raw/final plans and failures](results/phase3_llm/summary.md) |
| 4 | [Localization](reports/phase4_grounding.md) | [Detections, negative control and review](results/phase4_grounding/summary.md) |
| 5 | [Segmentation](reports/phase5_segmentation.md) | [Masks, points and pending review](results/phase5_segmentation/summary.md) |

## Limitations

Captions can hallucinate or truncate; text checks cannot prove cultural correctness. Grounding mislabeled a bicycle as an airplane in a negative control. SAM still loses bicycle spokes/rims or includes background. Lamp review is bowl-only and PENDING. No independent box/mask ground truth supports accuracy claims.

Historical text/provenance has a [nonignored preservation copy](results/historical_text_provenance.zip), but no independent external backup is verified. Original images retain attribution/license restrictions; see result summaries. Inspect evidence and obtain mentor review before Phase 6.
