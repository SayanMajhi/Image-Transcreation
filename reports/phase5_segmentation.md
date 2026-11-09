# Phase 5: Segmentation and mask review

## Objective
Produce original-resolution object masks from an explicitly selected detection box, investigate point prompts and establish an auditable mask-review gate. No image editing is performed.

## Models and tools
`facebook/sam-vit-base`, revision `70c1a07f894ebb5b307fd9eaaee97b9dfc16068f`; Transformers 4.57.6 SamProcessor/SamModel, CUDA FP32, batch 1, seed 42, multimask output, threshold 0.0. Lazy loading, eval/inference_mode and explicit CPU fallback remain unchanged. Hardware: RTX 3050 Laptop GPU, 4 GB.

## Implementation summary
`SegmentationInput/Result` bind source image, detection hash/index/box, model settings and optional points. SAM's processor transforms original-image coordinates; postprocessing restores exact source resolution. Three candidate PNGs are retained, with binary 0/255 pixels, foreground counts, bounds and predicted SAM scores. A score can choose a visualization but never acceptance.

`scripts/review_mask.py` checks image/detection/segmentation/point/mask evidence, dimensions, binary values, counts, bounds and explicit indices. It supports ACCEPT_FOR_SEGMENTATION_TEST, REJECT and NEEDS_REVIEW. Named reviewer identity, reason and original/mask/overlay inspection declarations are required for a submitted decision. PENDING is a preparation state. Accepted masks authorize only a specified segmentation test; diffusion, editing and cultural-transformation permissions remain false.

## Experimental setup
Bicycle used grounding prediction 0. Lamp used prediction 2 from `A02_oil_lamp_020`, selected from saved visual evidence rather than a highest-score rule. Box-only and one fixed point-guided experiment per image used the same source bytes, boxes and model settings. All runs were RESEARCH_ONLY.

Bicycle target: physical frame, handlebars, saddle, rims, tires and visible spokes; exclude wall, road and wheel-opening background. Lamp diagnostic target: visible clay bowl/body only; exclude flame, unrelated tray, grains and background. This is not a complete-lamp replacement target.

Point coordinates were saved before inference. Bicycle positives: (680,653), (658,722), (550,913), (850,882); negatives: (830,625), (680,695), (505,750), (908,758). Lamp positives: (650,330), (760,418), (850,365); negatives: (769,310), (880,420). These are research annotations, not independent human approvals. No post-result prompt sweep or mask cleanup occurred.

## Actual candidate results
Each cell lists candidate 0 / 1 / 2 in output order.

| Run | SAM predicted scores | Foreground pixels | Forward seconds |
| --- | --- | --- | ---: |
| Bicycle box | .955328 / .943802 / .864693 | 110800 / 88076 / 72998 | 3.145877 |
| Bicycle box+points | .887634 / .816094 / .731331 | 97388 / 74911 / 26559 | 1.731765 |
| Lamp box | .964611 / .956918 / .947274 | 33862 / 30373 / 27917 | .983994 |
| Lamp box+points | .970741 / .962730 / .945954 | 32088 / 31757 / 27687 | 1.226203 |

Box-only peak allocated CUDA memory: 2,065,262,592 bytes; point-guided: 2,065,263,616 bytes, both approximately 1.92 GiB. Loading was recorded separately: bicycle/lamp box 8.458468/7.928846 seconds; point-guided 9.298340/9.032545 seconds. These are individual observations, not controlled performance rankings.

## Important findings and limitations
Qualitative inspection: box-only bicycle masks include background inside wheels and frame. Points trade background removal against lost spokes, rims and tire arcs; none reliably preserves the complete target. Candidate 2 satisfied all sampled point labels but still omitted important structure. Satisfying sparse points does not establish mask quality.

Lamp point-guided candidates 0 and 1 retain most visible bowl and exclude flame more consistently; candidate 2 has larger interior exclusions. The supporting base is outside the diagnostic target. All nine baseline/new mask-pair overlaps per image are saved as descriptive diagnostics. They are not ground-truth IoU/Dice. SAM predicted scores likewise are not measured accuracy.

## Human-review status and final implementation status
Oil-lamp candidates 0/1 have PENDING requests. Bicycle candidates 0/1/2 have PENDING requests within a NEEDS_REVIEW preparation case. That triage label is not a human verdict. No genuine mask acceptance is recorded. Hash checks protect integrity relative to recorded evidence; they do not authenticate a person's identity, prove attention or verify semantics.

Historical tests: 126 → 157 with box segmentation, 157 → 170 with points, 170 → 199 with mask review. Phase 5 remains **NEEDS FIXES / human review pending** for quality sign-off. Phase 6 has not started.

## Essential artifacts
- [Result index: masks, comparisons, point provenance and pending records](../results/phase5_segmentation/summary.md)
- [All baseline/new descriptive statistics](../results/phase5_segmentation/experiments/metadata/phase5_iteration2_assets/mask_statistics.json)
- [Lamp inspection case](../results/phase5_segmentation/experiments/mask_review/case_A_oil_lamp)
- [Bicycle inspection case](../results/phase5_segmentation/experiments/mask_review/case_B_bicycle)
- [SAM settings](../configs/sam.yaml)
- [Mask-review tests](../tests/test_mask_review.py)
