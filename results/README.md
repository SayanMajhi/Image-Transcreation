# Results: read in this order

This folder contains several experiments and development iterations. They do not form one uninterrupted automatic run. Start with the two case studies below, then consult the component history when needed.

## 1. Current food-editing case: chole and puri

Open the [case walkthrough](phaseB_mask_review_20261120_01/README.md). It connects the original image, detections, masks, corrections, and generation attempts in one reading order.

**Recorded outcome:** a historical generated image exists and passed the reported protected-pixel check. New controlled A/B/C attempts failed before inference because the pinned model was unavailable; their visual quality cannot be evaluated. Human review of the generated image remains pending in the report.

## 2. Guided replacement: six-case pilot

Open the [pilot report](phase9_pilot/README.md), then view the [run_002 overview](phase9_pilot/run_002/overview.jpg) and [verification summary](phase9_pilot/run_002/verification_summary.json). The latter records no failures and no missing or tampered recorded files.

For each case in `run_002/CASE_01` through `CASE_06`, read `REVIEW.md` alongside `comparison.jpg` and `final.png`. Use `status.json` and the attempt folders for technical detail.

**Recorded outcome:** six technically completed reference replacements. The pilot summary records one historical human pass and five pending human reviews. References, masks, placement, scale, and shadows were selected by an operator. Pixel preservation and repeatability do not establish natural appearance or cultural appropriateness.

`run_001` is an earlier retained run; `dev_run_000_*` records development evidence. `phase9_repeatability` contains earlier pilot preparation and provenance used by the implementation. Start with the report and `run_002` for the presentation rather than opening every run.

## 3. Explain how the components were developed

| Read order | Folder | Question it answers |
| --- | --- | --- |
| 1 | [Research](phase1_research/README.md) | What was the initial research direction? |
| 2 | [Captioning](phase2_vlm/README.md) | What can the image captioner describe? |
| 3 | [Planning](phase3_llm/README.md) | How are proposed changes validated? |
| 4 | [Grounding](phase4_grounding/README.md) | Where is the original object? |
| 5 | [Segmentation](phase5_segmentation/README.md) | Which pixels belong to the selected region? |
| 6 | [Inpainting](phase6_inpainting/README.md) | Can the region be edited while preserving its surroundings? |
| 7 | [Integration](phase7_integration/README.md) | What happened when the stages were connected in research runs? |
| 8 | [Cultural validation](phase8_cultural_validation/README.md) | What evidence exists for visual and cultural quality? |
| 9 | [Pilot](phase9_pilot/README.md) | Does guided reference replacement repeat across cases? |

These are historical reports with their own scopes and dates. A later folder does not automatically supersede every earlier experiment. The integration README reports failed visual adaptation; the pilot evaluates a different editing method.

## 4. Supporting material

| Folder or file pattern | How to use it |
| --- | --- |
| `appearance_transfer_baseline/` | Alternative classical appearance-transfer experiment. Supporting comparison, outside the primary walkthrough. |
| [Supplementary full-scene illustration](submission_demo/full_scene_india_to_japan/README.md) | Presentation illustration made with guided image generation; excluded from pipeline benchmark claims. |
| `archive/` and `*_review.zip` | Packaged historical reviews. Usually unnecessary to open during the presentation. |
| `iteration*/`, `visual_v*/`, `*_before*` | Earlier attempts and reports retained to explain changes and failures. |
| `execution*.json`, `*.log`, hashes, manifests | Detailed evidence supporting a result. Open after the corresponding summary. |

See the [cleanup review](../docs/REPOSITORY_REVIEW.md) for what can be simplified and why the historical artifacts currently remain in place.
