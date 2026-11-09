# Phase 2 evidence

[Phase report](../../reports/phase2_vlm.md).

These are actual preserved outputs, extracted and hash-checked against the original archive, not links to old report assets.

| Evidence | Files |
| --- | --- |
| Initial diagnostic captions | [BLIP](experiments/blip.json), [Florence](experiments/florence.json), [SmolVLM](experiments/smolvlm_sanity.json) |
| Paired 11-image comparison | [Measurements](experiments/vlm_comparison/comparison.json), [Florence captions](experiments/vlm_comparison/florence.json), [SmolVLM captions](experiments/vlm_comparison/smolvlm.json), [input manifest](experiments/vlm_comparison/frozen_manifest.json) |
| Longer output did not finish | [256-token reruns](experiments/smol_extended/smol_extended.json) |
| Concise instruction diagnostic | [Paired outputs](experiments/smol_concise/concise_comparison.json) |
| Idol/task/crop failures | [Caption tasks](experiments/durga_comparison/comparison.json), [crop](experiments/durga_crop_diagnostic/caption_crop.json), [dense labels](experiments/durga_dense/regions.json), [grid observations](experiments/durga_regions/observations.json) |

The comparison retains actual times, memory and completion metadata. Florence's median was 663.77 ms versus SmolVLM's 5,617.28 ms under their recorded configurations. SmolVLM hit its initial ceiling on 5/11 images; increasing to 256 tokens completed none of those five. Qualitative cultural-object coverage motivated model selection despite hallucinations and omissions; no human-verified quality score establishes general superiority.

Original diagnostic figures are retained: [dense-region face labels](figures/durga_dense_annotated.png), [full grid view](figures/durga_regions_full.png), [top-left](figures/durga_regions_top_left.png), [top-right](figures/durga_regions_top_right.png), [bottom-left](figures/durga_regions_bottom_left.png), [bottom-right](figures/durga_regions_bottom_right.png). These are historical model diagnostics, not ground-truth labels.

Source-image identities/provenance remain in the frozen manifest and local `data/` collection. Not all dataset files are committed or licensed for unrestricted redistribution. Raw outputs may contain historical paths; [relocation provenance](../relocation_manifest.json) and [original text backup](../historical_text_provenance.zip) preserve context. No original caption or measurement was rewritten.
