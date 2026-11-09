# Phase 4 evidence

[Phase report](../../reports/phase4_grounding.md).

## Actual experiments

- [Baseline detections and original-versus-annotated figures](experiments/baseline/): bicycle, lamp and vessels; every box, score and raw prediction remains in detection JSON.
- [Eight declared query/threshold conditions, bicycle replay and airplane negative control](experiments/threshold_query/).
- [Exact protocol](experiments/threshold_query/experiment_plan.json) and [condition measurements](experiments/threshold_query/run_summary.json).
- [Original-model/environment metadata and source provenance](experiments/metadata/phase4_grounding_assets/).
- [Replay equality checks](experiments/metadata/phase4_iteration2_assets/baseline_reproducibility.json).
- [Visual assessments, unfilled human worksheets and settings](experiments/metadata/phase4_iteration2_assets/).
- [Box-review source bundles and actual decisions](experiments/box_review/).

## Comparisons and negative result

| Query | Detections at .30 / .20 box threshold |
| --- | --- |
| oil lamp | 1 / 8 |
| diya | 5 / 13 |
| incense burner | 5 / 8 |
| clay incense burner | 7 / 8 |

Text threshold stayed .25. Counts are predictions, not recall. Lower thresholds admitted duplicates and unrelated regions. Comparison figures: [oil lamp](figures/threshold_comparison_oil_lamp.png), [diya](figures/threshold_comparison_diya.png), [incense burner](figures/threshold_comparison_incense_burner.png), [clay incense burner](figures/threshold_comparison_clay_incense_burner.png).

[Airplane negative control](experiments/threshold_query/N01_airplane_negative/detection.json) falsely labeled the bicycle with confidence .419180. [Its annotated comparison](experiments/threshold_query/N01_airplane_negative/comparison.png) is preserved without correction. Numeric validity does not establish semantic correctness.

## Review status and integrity

The bicycle `accepted.json` contains `YOUR_NAME`; it is not confirmed named-human approval. It remains unchanged and the segmentation gate rejects placeholder identities. Other prepared boxes remain pending. Vessel queries do not establish cultural object identity.

Model `IDEA-Research/grounding-dino-tiny`, revision `a2bb814dd30d776dcf7e30523b00659f4f141c71`, is recorded with settings in every run. All predictions and review-source bytes are unchanged. [Relocation manifest](../relocation_manifest.json) maps old paths recorded inside immutable JSON; no old `reports/` assets are required for inspection or current commands.

Twelve byte-identical image copies were archived after SHA-256 comparison. Shared original PNGs and the identical bicycle replay annotation/comparison are available in the baseline bundles; each condition retains its own predictions, settings, timings and nonduplicate annotated evidence. Hash-bound box-review and SAM bundles retain all locally required files.

Bicycle: [Basile Morin](https://commons.wikimedia.org/wiki/File:Parked_bicycle_with_graffitied_building_facade_and_doors_in_Amsterdam.jpg), CC BY-SA 4.0. Lamps: [Benoy](https://commons.wikimedia.org/wiki/File:Diwali_Oil_lamps_Darjeeling.jpg), CC BY-SA 3.0. Original Durga photo is user-supplied with unspecified redistribution rights.
