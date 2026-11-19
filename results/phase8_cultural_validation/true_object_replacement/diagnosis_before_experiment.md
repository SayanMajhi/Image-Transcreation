# Source-removal and geometry feasibility assessment

Confirmed: the latest A/B raw 512 images already contain the hybrid/rear lobe; compositing alone cannot explain it. Prior Canny maps describe a researcher-drawn target, not extracted croissant edges. Canny provides contour cues, not physical depth. The drawn two-face guide does not ensure photographic volume. Nearly every SAM0 pixel changed in A/B (only 2/0 unchanged), so the main visible hybrid is newly synthesized rather than wholesale untouched source. There are also 341 warm-colored source edge pixels outside the tighter mask; these remain protected in A/B. Color thresholding is a diagnostic, not object ground truth.

Hypotheses: source-image conditioning and constrained reconstruction can bias toward croissant geometry; target edge drawings and SDXL texture synthesis were insufficient for a coherent replacement. These are not isolated causal tests.

Removal feasibility: the old complete rectangle [35,165,1225,795] covers the observed original pastry and shadow. Its 10px outer ring is 98.09% exact white, median RGB255. No warm heuristic foreground occurs outside it. White deterministic reconstruction inside this region is defensible for this isolated studio-like photograph; it would be unsuitable for a textured scene. Preserve all original pixels outside. Save the clean plate BEFORE placing any reference.

Reference chosen before output: complete upper folded pastry from Kaushalspeed's photograph. Lower pastry, leaf, chutney and table excluded. It has photographed thickness, folded rim, shading and irregular crust, unlike a drawn triangle. The crop is one intact body; orientation is inherited, with only uniform rescaling. It is not generated or Qwen-planned.

One preregistered experiment A: frozen request_A.json. No diffusion/LLM calls, no color tuning. Synthetic soft contact shadow is a declared illustration/compositing operation; physical light matching remains qualitative. A second correction is allowed only for a specific observed defect.
