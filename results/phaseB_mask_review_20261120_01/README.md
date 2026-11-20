# Chole and puri experiment walkthrough

This guide connects the existing artifacts for this case. It does not imply that all steps ran automatically or that every generated result was accepted.

| Step | Open | What it shows |
| --- | --- | --- |
| 1. Input | [Original image](candidate_review/original.png) | The scene being edited. |
| 2. Object localization | [Puri detections](ground_puri/), [curry detections](ground_curry/) | Separate grounding outputs for the requested source objects. |
| 3. Segmentation | [Puri instance 0](sam_puri_0/), [instance 1](sam_puri_1/), [instance 2](sam_puri_2/), [curry](sam_curry_0/) | Candidate masks from the detector selections. |
| 4. Initial mask review | [Overlay](candidate_review/red_mask_overlay.png), [difficult boundaries](candidate_review/difficult_boundaries_closeup.png), [review record](candidate_review/review_status.json) | Which boundaries needed inspection. |
| 5. Mask correction | [Corrected combined overlay](corrected_review/corrected_combined_overlay.png), [difference](corrected_review/before_after_mask_difference.png), [correction report](corrected_review/correction_report.json) | The changes made to the editable regions. |
| 6. Earlier generation | [Prepared experiments](approved_puri_experiments/), [historical run A](approved_puri_experiments/run_A/) | Earlier request and output evidence. Consult the controlled report's provenance caveat before using this result. |
| 7. Controlled comparison | [Report](controlled_diffusion/report.md), [comparison sheet](controlled_diffusion/comparison_sheet.png), [technical validation](controlled_diffusion/technical_validation.json) | The outcomes of the planned A/B/C comparison and the separate historical result. |

The controlled report records new A/B/C failures before inference because the pinned SD 1.5 model was absent from cache and online retrieval failed. It reports the historical A separately: generation completed and the protected-pixel check passed, but its original corrected mask was labeled as a SAM candidate, so it is excluded from the new controlled set. New requests use the refined-mask route.

Visual and cultural assessments remain pending in that report. The curry replacement target must also be specified before its separate experiment. Use these as current limitations when explaining the case.
