# Culture-Aware Image Transcreation

A Python research project for changing selected objects in an image toward a requested cultural context while preserving the surrounding scene.

The project contains captioning, cultural planning, object detection, segmentation, reviewed research editing, and saved-result verification. A complete user-facing workflow is still being developed; image quality and cultural appropriateness require human review.

## Start here

- [Connected workflow instructions](docs/WORKFLOW.md): start, review, pause, and resume a new guided run.
- [Project map and presentation walkthrough](docs/PROJECT_MAP.md): where the code lives and how to explain it.
- [Results reading guide](results/README.md): connected case studies and historical evidence.
- [Tests reading guide](tests/README.md): checks grouped by pipeline stage.
- [Clutter review](docs/REPOSITORY_REVIEW.md): large folders, dependencies, and cleanup candidates.
- [Remaining implementation work](PIPELINE_FINALIZATION_PLAN.md): the intended complete workflow and acceptance checklist.
- [Six-case pilot](results/phase9_pilot/README.md): recorded technical results and visual limitations.
- [Report source and compilation instructions](mini-project-report/README.md): the presentation/report material.

## How the project works

The intended workflow is:

```text
Image + requested change
    -> caption -> user confirmation -> cultural plan -> user approval
    -> object boxes -> masks -> mask review -> editing -> final review
```

The new `scripts.workflow` coordinator connects these stages with explicit human review pauses and automatically generated handoff files. Its control flow is tested with synthetic adapters; live results must be evaluated separately. The earlier automated planning commands retain their review boundaries. The reference-compositing pilot is a separate guided method using selected photographs and placement settings.

| Step | Main implementation | Purpose |
| --- | --- | --- |
| Caption | `src/transcreation/stages/caption.py` | SmolVLM describes visible image content. |
| Plan | `src/transcreation/stages/ollama_planner.py`, `planning.py` | Qwen proposes changes; deterministic rules validate the proposal. |
| Locate | `src/transcreation/stages/grounding.py` | Grounding DINO finds boxes around the original object. |
| Segment | `src/transcreation/stages/segmentation.py` | SAM produces candidate object masks. |
| Edit | `src/transcreation/stages/inpainting.py` | Stable Diffusion inpaints a selected region and restores unmasked pixels. |
| Guided replacement | `src/transcreation/stages/reference_replacement.py` | Places a selected reference cutout with recorded settings. |
| Coordinate and record | `orchestration.py`, `guided_research.py`, `pilot.py` in `src/transcreation/` | Manage the distinct execution paths and their evidence. |

## Repository layout

```text
src/transcreation/       Core Python implementation
scripts/                Command-line tools for stages and reviews
configs/                Model and generation settings
data/                   Local input images
outputs/                Local generated run artifacts
results/                Retained research results and review evidence
experiments/scripts/    Scripts for specific experiments
tests/                  Automated checks and fixtures
docs/                   Repository navigation and explanation
mini-project-report/    Report source, figures, and viva notes
reports/                Supporting notes
```

The [project map](docs/PROJECT_MAP.md) also explains the supporting root folders and files.

## Inspect the command-line tools

Run from the repository root using the existing Python 3.11 environment:

```powershell
.venv\Scripts\python.exe -m transcreation.cli --help
.venv\Scripts\python.exe -m scripts.segment_sam --help
.venv\Scripts\python.exe -m scripts.inpaint --help
.venv\Scripts\python.exe -m scripts.pilot --help
```

Actual model execution also needs the relevant model weights, compatible packages, and Ollama for Qwen planning. Saved run paths may depend on the original workspace. See the reproduction instructions alongside each experiment before rerunning it.

## What the results establish

- The Phase 9 pilot records six technically completed guided replacements, with pixel preservation and replay checks. Five new cases still await human review in its recorded summary.
- The integration experiments demonstrate localized generation, but their recorded visual quality is mixed or unsuccessful.
- The [recent controlled diffusion report](results/phaseB_mask_review_20261120_01/controlled_diffusion/report.md) records new A/B/C runs failing before inference because the pinned model was unavailable; historical output is reported separately.
- The [full-scene illustration](results/submission_demo/full_scene_india_to_japan/README.md) is a supplementary guided image edit, outside the validated pipeline evaluation.

Technical completion, pixel preservation, and passing software tests do not by themselves establish realistic or culturally appropriate edits. Use each experiment's own report when presenting its outcome.
