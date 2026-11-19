# Phase 4: Object localization

## Objective
Find image regions matching an explicit research phrase and return validated boxes in original-image pixels. Determine whether boxes are reliable enough for controlled segmentation tests.

## Models and tools
`IDEA-Research/grounding-dino-tiny`, revision `a2bb814dd30d776dcf7e30523b00659f4f141c71`. Transformers 4.57.6, AutoProcessor and AutoModelForZeroShotObjectDetection; lazy loading, eval/inference_mode, batch 1, CUDA FP32, seed 42. Actual hardware was RTX 3050 Laptop GPU, 4 GB, not a confirmed Ti model. Default thresholds remain box 0.30, text 0.25. Installed postprocessing takes `threshold` and target image height/width. CPU fallback is explicit.

## Implementation summary
`stages/grounding.py` validates source phrases and finite, ordered, in-bounds XYXY coordinates and scores. It retains multiple valid detections, reports no-detection/error states and saves raw predictions plus annotated copies. Geometry validation cannot establish object identity.

`scripts/review_grounding.py` prepares hash-bound evidence and supports explicit ACCEPT, REJECT or NEEDS_REVIEW. An accepted box is only a segmentation-test candidate, never an editing authorization. There is no highest-score automatic selection.

## Experimental setup and measured results
Baseline sources were a parked bicycle (1280×966), Diwali lamps (1280×842) and Durga Puja (980×692). The same settings were used initially.

| Baseline | Returned detections | Scores | Qualitative observation |
| --- | ---: | --- | --- |
| bicycle | 1 | 0.943281 | Plausible bicycle box |
| oil lamp | 1 | 0.314222 | Central lamp found; other visible lamps missed |
| incense burner | 5 | approximately 0.372–0.424 | Plausible vessels; apparent edge vessel missed; identities unverified |

The bicycle forward pass took 1.598710 seconds after 12.574197 seconds loading; peak allocated inference CUDA memory was 1,824,719,360 bytes. Other measured run times/memory remain in each detection JSON.

Exactly eight query/threshold conditions were preregistered, with text threshold fixed at 0.25:

| Image/query | Box 0.30 count | Box 0.20 count |
| --- | ---: | ---: |
| lamps / oil lamp | 1 | 8 |
| lamps / diya | 5 | 13 |
| vessels / incense burner | 5 | 8 |
| vessels / clay incense burner | 7 | 8 |

Ten calls included these eight, an airplane negative control on the bicycle photograph, and a bicycle replay. The replay reproduced the bicycle box and score exactly. The negative control incorrectly labeled the bicycle airplane with score **0.419180** at default thresholds. Its prediction was retained.

## Findings and failure cases
Visual inspection showed that lower thresholds recovered some plausible objects but added duplicate, fruit/coin, broad-scene and idol-region detections. More boxes did not mean better detection. These counts are model outputs, not recall or accuracy; no independently annotated ground truth exists. Experimental vessel queries do not verify culturally specific names.

For later SAM use, the bicycle and an explicitly inspected central lamp box were plausible research prompts. Repeated objects, merged extents and false labels still require explicit instance selection. Confidence cannot substitute for human inspection.

## Review status and final implementation status
Baseline offline tests reached 95; box-review tests raised the historical count to 126. The saved bicycle ACCEPT has reviewer `YOUR_NAME`: it is preserved but is not treated as confirmed named-human approval. The later SAM input gate rejects placeholder identities. No policy was changed during cleanup.

Independent localization and review utilities work; planner integration and automatic semantic verification are not implemented. [Essential results and exact trial paths](summary.md), [settings](../../configs/grounding.yaml), [all threshold measurements](.), [box-review cases](experiments/box_review).

Original images retain their source bytes. Bicycle: Basile Morin, CC BY-SA 4.0; lamps: Benoy, CC BY-SA 3.0; source credits are in the original review packages. Durga image was user-supplied; redistribution rights remain unspecified.
