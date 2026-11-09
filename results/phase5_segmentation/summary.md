# Phase 5 evidence

[Phase report](../../reports/phase5_segmentation.md).

## Actual experiment bundles

| Condition | Bicycle | Oil lamp |
| --- | --- | --- |
| Box only | [All three masks and metadata](experiments/box_only/A_bicycle/) | [All three masks and metadata](experiments/box_only/B_oil_lamp/) |
| Box + fixed points | [All three masks and point provenance](experiments/box_points/A_bicycle/) | [All three masks and point provenance](experiments/box_points/B_oil_lamp/) |
| Prepared mask review | [Three PENDING requests; NEEDS_REVIEW triage](experiments/mask_review/case_B_bicycle/) | [Candidates 0/1 PENDING](experiments/mask_review/case_A_oil_lamp/) |

Every segmentation bundle retains original source bytes, selected detection JSON, exact mask PNGs, overlays, box preview and metadata. Point-guided bundles also retain point JSON and preview. Research status, selected indices, model revision, predicted SAM scores, foreground counts and runtime/memory remain unchanged. Redundant candidate-gallery images were archived; individual overlays and the comparisons remain available.

## Reproducibility and comparisons

- [Preregistered point protocol](experiments/metadata/phase5_iteration2_assets/experiment_plan.json)
- [Pre-inference point documents and previews](experiments/point_protocol/prompts/)
- [All baseline/new mask-pair counts and descriptive overlap](experiments/metadata/phase5_iteration2_assets/mask_statistics.json)
- [Bicycle all-candidate comparison](figures/A_bicycle_all_candidates_comparison.png), [binary masks](figures/A_bicycle_binary_comparison.png), [thin-structure detail](figures/A_bicycle_detail_comparison.png)
- [Lamp all-candidate comparison](figures/B_oil_lamp_all_candidates_comparison.png), [binary masks](figures/B_oil_lamp_binary_comparison.png), [boundary detail](figures/B_oil_lamp_detail_comparison.png)
- [Model settings, checkpoint configuration and exact command evidence](experiments/metadata/)

SAM checkpoint `facebook/sam-vit-base`, revision `70c1a07f894ebb5b307fd9eaaee97b9dfc16068f`; CUDA FP32. Peak allocated CUDA was approximately 1.92 GiB. Scores are predicted quality, not measured ground-truth IoU. Mask overlap compares predictions, not independent labels.

## Limits and review status

No bicycle candidate reliably preserves wheel rims/spokes/openings without background leakage or missing structures. Lamp candidates 0 and 1 are plausible for the visible clay bowl/body diagnostic; they do not constitute complete lamp replacement. All real runs remain RESEARCH_ONLY; no named human has approved a mask. PENDING requests remain non-releasable.

Portable review bundles validate locally without following old JSON path strings. [Relocation mapping](../relocation_manifest.json) preserves those historical references; [text provenance](../historical_text_provenance.zip) preserves original iteration explanations and code snapshots. No image editing or Phase 6 implementation exists.
