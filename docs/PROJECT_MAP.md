# Project map

Use this guide to navigate the repository and explain the implementation during a presentation.

For a continuous experiment story, start with the [results guide](../results/README.md). For checks grouped by purpose, use the [test guide](../tests/README.md). The [cleanup review](REPOSITORY_REVIEW.md) records which material is historical and why paths are retained.

## Core code

| File or folder | What to explain |
| --- | --- |
| [cli.py](../src/transcreation/cli.py) | Main command-line entry point: caption, plan, ground, and run. |
| [config.py](../src/transcreation/config.py) | Loads and validates model settings. |
| [contracts.py](../src/transcreation/contracts.py) | Defines the structured inputs and outputs passed between stages. |
| [pipeline.py](../src/transcreation/pipeline.py) | Prepares and runs captioning; despite its name, this file is not the complete editor. |
| [orchestration.py](../src/transcreation/orchestration.py) | Coordinates planning, reviewed grounding, and validation of saved research evidence. |
| [guided_research.py](../src/transcreation/guided_research.py) | Runs a prepared research specification through localization, segmentation, and inpainting. |
| [workflow.py](../src/transcreation/workflow.py) | New connected session coordinator with review pauses, automatic prompts, sequential edits, and verification. Use [the workflow guide](WORKFLOW.md) to run it. |
| [stages/](../src/transcreation/stages/) | Model implementations and alternative editing methods. |
| [pilot.py](../src/transcreation/pilot.py) | Validates, runs, verifies, and packages the reference-replacement pilot. |

## Supporting folders

| Location | Role |
| --- | --- |
| [scripts/](../scripts/) | Thin command-line tools plus review and evaluation utilities. These call the implementation in `src/`. |
| [configs/](../configs/) | Caption, planner, detector, SAM, and inpainting settings. |
| [data/](../data/) | Input images stored locally; most contents are excluded from Git. |
| [outputs/](../outputs/) | Local captions, plans, detections, masks, and generated images; most contents are excluded from Git. |
| [results/](../results/) | Retained experiments, reports, review records, and evidence. Numbered phases describe research history. |
| [experiments/scripts/](../experiments/scripts/) | Preparation, execution, and reporting for particular experiments. |
| [tests/](../tests/) | Checks for validation, review boundaries, stage behavior, and artifact integrity. |
| [mini-project-report/](../mini-project-report/) | Report package and viva notes; follow its README for compilation. |
| [reports/](../reports/) | Supporting research notes. |
| [captioning/](../captioning/), [chapters/](../chapters/) | Additional existing material; start with `src/` for implementation and `mini-project-report/` for the report. |
| [combine_masks.py](../combine_masks.py) | Root-level utility used in the current mask-combination workflow. |
| [pyproject.toml](../pyproject.toml) | Package metadata, dependencies, and the `transcreate` command registration. |
| [PIPELINE_FINALIZATION_PLAN.md](../PIPELINE_FINALIZATION_PLAN.md) | Remaining work toward the complete intended workflow. |

`.venv`, `.python311`, `.idea`, `__pycache__`, and package metadata folders support the local environment. `.local_archive` and `results/archive` contain retained local material. They are not the starting point for explaining the algorithms.

## Presentation walkthrough

1. **State the objective.** Change a selected culturally associated object while preserving the rest of the image.
2. **Open the root README.** Show the intended workflow and distinguish it from the execution paths currently implemented.
3. **Show `src/transcreation/stages/`.** Explain captioning, planning, grounding, segmentation, and editing in that order.
4. **Show one saved example.** Open its original image, boxes, mask, generated image, and metadata. Explain any manual selection involved.
5. **Show the pilot results.** Use [Phase 9](../results/phase9_pilot/README.md) to explain technical repeatability and the pending visual reviews.
6. **Explain current limitations.** Use the experiment report for the displayed image. The recent [controlled diffusion report](../results/phaseB_mask_review_20261120_01/controlled_diffusion/report.md) includes failed runs and a separate historical result.
7. **Finish with remaining work.** Open the finalization plan: user input, review flow, approved-plan-to-prompt conversion, multiple-object handling, and visual quality.

## Choosing evidence

| What you want to show | Start here |
| --- | --- |
| Captioning experiments | [Phase 2](../results/phase2_vlm/README.md) |
| Planning experiments | [Phase 3](../results/phase3_llm/README.md) |
| Object detection | [Phase 4](../results/phase4_grounding/README.md) |
| Segmentation | [Phase 5](../results/phase5_segmentation/README.md) |
| Inpainting | [Phase 6](../results/phase6_inpainting/README.md) |
| Integration and recorded visual failures | [Phase 7](../results/phase7_integration/README.md) |
| Cultural evaluation | [Phase 8](../results/phase8_cultural_validation/README.md) |
| Repeatability pilot | [Phase 9](../results/phase9_pilot/README.md) |
| Report claims and their sources | [Evidence map](../mini-project-report/evidence-and-review.md) |

## Where future files belong

Put reusable implementation in `src/transcreation/`, command wrappers in `scripts/`, and model settings in `configs/`. Put experiment-specific scripts in `experiments/scripts/`. Keep local working outputs in `outputs/` and documented research evidence in a clearly named `results/` folder. Use `docs/` for repository guides.

Existing paths are retained because run records, scripts, and artifact hashes may refer to them. This navigation cleanup does not change model behavior or complete the missing workflow stages.
