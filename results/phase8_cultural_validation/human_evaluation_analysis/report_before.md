# Phase 8 — Cultural Transcreation Validation

## 1. Research question and current status

Can a structurally conditioned **object replacement**, rather than food recoloring, produce a recognizable target-culture snack while preserving the photograph's semantic function and protected scene?

**Technical feasibility: demonstrated for the SDXL+Canny fallback on the local GPU. Cultural success: PENDING_HUMAN_EVALUATION.** Two fixed seeds were generated, with no hidden retries or tuning. Seed 42 fails the single-snack/plain-scene specification. Seed 43 is a more plausible samosa-like pastry but remains visually borderline. Neither is certified a cultural-transcreation success. The six-case pilot was not started.

## 2. Research foundation and previous failures

[Khanuja et al., EMNLP 2024](https://aclanthology.org/2024.emnlp-main.573/) studies image transcreation with human evaluation of culturally meaningful edits and meaning preservation. It motivates testing an actual object replacement, not merely a country's colors. [Khanuja et al., NAACL 2025](https://aclanthology.org/2025.naacl-long.359/) separates cultural relevance, semantic equivalence and visual similarity and discusses automatic metrics' limitations. We retain these dimensions but require real human ratings; our pilot threshold is project-specific, not either paper's benchmark standard. Both full PDFs were downloaded; the initial evaluation reading informed the frozen protocol, and a subsequent limitations check reinforced the restrictions on nation-level claims and metric interpretation.

Earlier ramen and spaghetti SD1.5 runs achieved exact pixel locality but failed coherent food adaptation through text-like marks, implausible inserts, texture changes and mask-boundary seams. The classical baseline retained geometry but mainly warmed color. Hypotheses motivating Phase 8: insufficient editing capability, restrictive geometry and a mismatch between surface modification and object replacement. These were not independently isolated causal factors. No old SD1.5 prompt tuning was repeated, and historical human MATERIAL_UNRESOLVED decisions remain unchanged.

## 3. Backend selection and hardware

Primary candidate: [FLUX.1 Kontext dev](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev), revision `24e9dedc4ef646698dc8eb4e18ae2cec3c9fea0d`. [QuantStack GGUF](https://huggingface.co/QuantStack/FLUX.1-Kontext-dev-GGUF) revision `2d083027732f81e5548620b57ac47da22d30aa5a` lists Q4_K_M, 6,931,817,760 bytes, expected SHA-256 `ebd4e92c44c47f104ad64e4353692f37addf06eb99420c9b459334d871c8b750`. This checksum is repository metadata, **not a downloaded/verified FLUX file**. Original noncommercial terms remain applicable. Anonymous access to the official model component index returned HTTP 401; acceptance/authenticated access is needed. No credentials, license acceptance or paid service use was invented.

Local observations: RTX 3050 Laptop GPU, 4,096 MiB VRAM, 16,003,864 KiB system RAM, initially 3,809,720 KiB free RAM. No local ComfyUI service or installed GGUF package was detected. A T4 connection was requested but none was provided to this session. FLUX loading/inference and T4 compatibility are **NOT ESTABLISHED**, not proven universally incompatible. No FLUX weights were downloaded. A documented single-file Diffusers GGUF code path is present but only mocked/contract-tested, not runtime certified. [GGUF semantics](https://huggingface.co/docs/diffusers/quantization/gguf), [official ComfyUI workflow](https://docs.comfy.org/tutorials/flux/flux-1-kontext-dev).

The explicitly permitted fallback was used:

| Component | Repository / pinned revision | Actual execution |
| --- | --- | --- |
| SDXL inpainting | `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` / `115134f363124c53c7d878647567d04daf26e41e` | Yes, FP16 safetensors |
| Canny ControlNet | `diffusers/controlnet-canny-sdxl-1.0` / `eb115a19a10d14909256db740ed109532ab1483c` | Yes, FP16 safetensors |

This is **not equivalent to FLUX Kontext**. The installed Diffusers 0.35.2 `StableDiffusionXLControlNetInpaintPipeline` supports image, mask and control-image inputs. All five required fallback weight files were checked against official pinned LFS SHA-256 metadata. A normal large-file transfer appeared stalled; bounded HTTP-range recovery reused completed files and verified the same pins. These were download repairs, not hidden model generations. [Checksums](../results/phase8_cultural_validation/weight_checksums.json), [environment](../results/phase8_cultural_validation/environment.json), [FLUX feasibility record](../results/phase8_cultural_validation/flux_candidate.json).

## 4. Source, target and license provenance

**Selected before generation:** one croissant photographed on white, reinterpreted as one golden triangular fried samosa. Source cultural frame: French-associated croissant; target: Indian snack context. This does not imply exclusive national ownership or establish the photograph's geographic origin. Function before/after: isolated handheld-snack product photograph, not a claim of breakfast-menu equivalence.

Source: **Croissant-Petr Kratochvil.jpg**, **Petr Kratochvil**, **CC0 1.0**, [Commons record](https://commons.wikimedia.org/wiki/File:Croissant-Petr_Kratochvil.jpg), [original Public Domain Pictures source](https://www.publicdomainpictures.net/en/view-image.php?image=12541&picture=croissant). Original JPEG **1280 × 853**, SHA-256 `06d784865dd559ff33ff54a9d66759c478f74c75a5fdf121a30c6313463fc3b8`. Modified images are identified as research derivatives; credit/link retained, no endorsement implied.

[France's tourism agency](https://www.france.fr/en/article/croissants-france-favorite-snack/) supports the French croissant association. [Chhatarpur district, Government of Madhya Pradesh](https://chhatarpur.nic.in/en/culinary-delight/samosa/) describes samosas as a local snack with a crisp fried shell and savory filling. We do not claim that an exterior image proves ingredients, taste or authenticity.

The Khanuja [dataset card](https://huggingface.co/datasets/cmu-lti/machine-translation-for-vision) declares MIT, but per-photo original attribution/redistribution evidence was not established for a selected dataset image; none was reused. Rejected source candidates and reasons were recorded before generation, not discarded after seeing outputs. [Selection log](../results/phase8_cultural_validation/selection_log.json), [frozen edit specification](../results/phase8_cultural_validation/case1/edit_specification.json), [original](../results/phase8_cultural_validation/case1/source.jpg).

## 5. Existing pipeline and automated planning

The unchanged SmolVLM → Qwen → deterministic-validator coordinator ran once on this source. Actual caption:

> A croissant, a type of pastry, is shown on a white background. The croissant is golden brown and flaky, with a slightly curved shape.

Qwen raw decision: **PROPOSE**. It mistakenly used the future samosa as the original-object description and falsely claimed user verification. No verified-object record was fabricated: the request correctly contained none. Final decision: **REVIEW, zero released candidates**. Issues: `UNVERIFIED_SOURCE_OBJECT`, `USER_CONSTRAINTS_UNRESOLVED`, `EDIT_UNCERTAINTY_UNRESOLVED`. The summary's false verification claim is an additional qualitative finding, not a newly invented validator issue code. [Complete caption/raw/final audit](../results/phase8_cultural_validation/case1/automated).

Guided research used the separate frozen researcher specification, not a promoted or manually repaired candidate. The new editor accepts a hash-bound RESEARCH_ONLY specification, region/protected masks, control condition, crop mapping and explicit prompt/seed. It rejects automated/approval modes; existing SD1.5 requests delegate to the unchanged implementation. No model-stage or review policy was weakened.

## 6. Localization, segmentation and editable region

One real DINO query `croissant` returned `[63.5688,207.6206,1174.2004,732.7499]`, score .897396. Inspection confirmed it encloses the pastry and white margins. One real box-prompt SAM run produced 343,864 / 342,250 / 184,885 foreground pixels. Raw SAM scores were 1.01194 / .99604 / .79615; these are uncalibrated predictions, **not measured IoU or probabilities**. No score-based acceptance occurred. Candidates 0/1 outline the old pastry; 2 omits portions. [DINO evidence](../results/phase8_cultural_validation/case1/localization/grounding), [SAM candidates](../results/phase8_cultural_validation/case1/sam/segmentation).

A tight croissant mask would constrain the target to a crescent silhouette. Instead, the explicitly declared replacement rectangle is `[35,165,1225,795]` in original-image XYXY coordinates, exclusive max: **749,700 pixels**, 68.6639% of the photograph, not an object-coverage score. It includes the original pastry, shadow and nearby white surface necessary to erase the old silhouette. The entire exterior is protected; there are no visible plate, utensils or people. This is operator-defined region provenance, not a SAM prediction or human-approved segmentation.

The Canny condition uses a researcher-drawn target triangle/fold prototype at original coordinates, not source Canny edges that would preserve the crescent. Vertices: `(650,215),(300,735),(1010,735)`; fold `(650,215)→(660,690)`; Canny thresholds 100/200. It specifies desired geometry, not cultural ground truth or a reference photograph. Enlarging authority over an actual protected object was unnecessary in this isolated source. The region, source/SAM references and target guide were frozen before inference. [Region mapping](../results/phase8_cultural_validation/case1/region_provenance.json), [overlay](../results/phase8_cultural_validation/case1/region_overlay.png), [target guide](../results/phase8_cultural_validation/case1/control_canny.png).

## 7. Preregistered experiment

Exactly **two** new editor calls, seeds **42 and 43**, identical conditions otherwise. No technical generation retry, source substitution, prompt adjustment, mask change or additional seed. [Preregistration](../results/phase8_cultural_validation/preregistration.json), [configuration](../results/phase8_cultural_validation/case1/editor_config.json).

- FP16, no weight quantization; batch 1; sequential CPU offload, maximal attention slicing, VAE tiling.
- Processing **512 × 512** because of local resource constraints; not native SDXL training resolution, a quality limitation.
- Source crop `[3,133,1257,827]`, padding `[0,280,0,280]`, square 1254 before resizing; no aspect-ratio stretching.
- Checkpoint-default **EulerDiscreteScheduler**, 24 requested / **23 effective** steps, strength .99, guidance 5.0, ControlNet scale .5.
- Original-resolution hard compositing via the existing utility; no hidden cleanup/blending.

Positive prompt:

> Photorealistic product photograph of one triangular Indian samosa, crisp golden brown fried pastry shell, folded sealed edges, subtle blistered texture, resting on a plain white surface, soft natural contact shadow, same camera viewpoint and lighting.

Negative prompt:

> croissant, crescent pastry, laminated pastry layers, text, watermark, extra objects, duplicate food, distorted pastry

Both installed CLIP tokenizer contexts were checked before generation; the positive prompt fit. Full raw crops, processing images/masks/control conditions, native composites and execution logs remain available. FLUX has no native binary-mask input in this adapter; its eventual locality would likewise come from compositing, not text compliance.

## 8. Actual images and visual findings

![Original, both SDXL outputs, matched classical baseline](../results/phase8_cultural_validation/case1/comparison.png)

**Seed 42 — visual FAIL.** The old croissant becomes a triangular pastry-like shape, but the model adds a lime slice, red spice, herbs and a board. These are unrequested semantic changes inside the editable rectangle. The pastry is smooth/flat and a background rectangle is visible. Exact exterior preservation does not excuse these failures.

**Seed 43 — provisional samosa-like object; NEEDS_REVIEW.** No lime/spice/board scene was added. The output is recognizably a golden triangular folded pastry to the assistant, rather than a recolored croissant. It is unusually broad/flat, with weak sealed-edge/filling cues, an overly smooth surface and faint composite/tint boundaries. It could be read as a generic triangular snack. Independent target-culture identification and photographic-realism judgments remain unavailable. This is a promising change in object geometry, **not a claimed cultural PASS**.

Both full scenes, raw outputs and native object/boundary close-ups were actually inspected. No VLM score substitutes for human validation. [Seed 42](../results/phase8_cultural_validation/case1/seed42/final.png), [seed 43](../results/phase8_cultural_validation/case1/seed43/final.png), [native object comparison](../results/phase8_cultural_validation/case1/object_native.png), [boundary comparison](../results/phase8_cultural_validation/case1/boundary_native.png).

## 9. Independent preservation checks

Independent code reopened original, region/protected masks and saved outputs without importing the editor/compositor. All images retain **1280 × 853** dimensions and the original JPEG hash. The masks are binary, nonempty, correctly mapped and have zero overlap. No source or original SAM evidence was overwritten.

| Output | Changed inside | Changed outside | Protected differences | Max exterior RGB-channel difference |
| --- | ---: | ---: | ---: | ---: |
| SDXL seed 42 | 748,804 | 0 | 0 | 0 |
| SDXL seed 43 | 637,409 | 0 | 0 | 0 |
| Matched appearance baseline | 749,700 | 0 | 0 | 0 |

Changes to initially near-white pixels **inside** the permitted region were also recorded; they are not automatically protected-region violations or cultural scores. Semantic damage inside the region is assessed separately above. [Full independent verification/hashes](../results/phase8_cultural_validation/independent_verification.json).

## 10. Human evaluation

Status: **PENDING_HUMAN_EVALUATION; zero actual reviewers/ratings**. A blinded packet contains numbered candidate images and the original, with the seed/backend key kept in a separate admin folder. Reviewers first identify the apparent target object, then receive the intended samosa adaptation for ratings. Only the reviewer-materials folder should be shared with the panel, not this labeled report or admin key.

Three independent people are sought, including familiarity with Indian food contexts. Each rates cultural relevance, scene meaning/function preservation, photographic realism and unrelated-scene preservation on 1–5, and explains defects, stereotypes and major factual/cultural concerns. Identity/familiarity/inspection declarations must be supplied genuinely. No template response is counted as a rating, and the assistant is not an evaluator in this panel.

Preregistered pilot PASS: no critical preservation violation; target recognizable; at least 2 of 3 reviewers give **all four dimensions ≥4**; no unresolved major factual/cultural objection from any reviewer. This is a project-specific criterion, not a published standard. [Protocol](../results/phase8_cultural_validation/human_protocol_preregistration.json), [reviewer instructions/blank form](../results/phase8_cultural_validation/human_evaluation/reviewer_materials), [actual response status](../results/phase8_cultural_validation/human_evaluation/status.json).

## 11. Baselines and pilot status

The existing deterministic appearance transfer was run once, unchanged, on the **same croissant and permitted region**. It retained the croissant and warmed food/background inside the region; it cannot accomplish this Type B identity change. Runtime .249 s CPU. Its locality passed, but it is not a successful cultural replacement. Human preference has not been measured.

Historical SD1.5 results are retained as **unmatched-source negative evidence** (ramen/spaghetti), not a controlled SDXL head-to-head comparison. No new SD1.5 experiment was run, respecting the instruction to stop that tuning. [Historical unmatched-source comparisons](../results/phase8_cultural_validation/baseline_comparison). Differences here also involve source complexity, target task, mask and structural conditioning; improvement cannot be attributed solely to the editing model.

**Six-case pilot: not started; 0/6 generated or human-approved.** The initial case lacks a clear accepted visual result and genuine human validation; seed 42 has a known semantic failure and seed 43 is borderline. Do not expand to Type C or claim repeatability/generalization. Outstanding work is actual panel review and mentor judgment on this bounded feasibility evidence, not another automatic tuning loop.

## 12. Tests, resource use and failure handling

Baseline: **420 passed**. Final suite: **440 passed, zero failures/errors**. Twenty new synthetic/mocked tests cover hashes, model identity, source/control/crop mapping, invalid masks, protected pixels, research-only isolation, no automatic approval escalation, SD1.5 delegation, absent-model failure, bad output dimensions, output provenance, cleanup and refusing overwrite. They do not download weights or certify real-model cultural quality. [Final test log](../results/phase8_cultural_validation/tests_final.json).

An initial focused-test failure exposed reuse of SD1.5's fixed-size configuration with a synthetic small crop. It was corrected by passing only geometry attributes to the shared utility, leaving the old contract unchanged. The failed test log is preserved. No real generation failed technically or was retried. A metadata-only effective-step observation was added between runs; model-facing settings remained frozen.

| Condition | Load s | Inference s | Internal process s | External wall s | Peak allocated CUDA |
| --- | ---: | ---: | ---: | ---: | ---: |
| seed 42 | 8.667 | 116.553 | 127.694 | 134.809 | .627 GiB |
| seed 43 | 8.211 | 115.436 | 126.025 | 133.576 | .627 GiB |

The low GPU peak reflects sequential submodule offload, not total model size. Seed 43 observed process-tree peak RSS was **7.555 GiB** with two-second sampling; this is an observation, not a continuous allocator peak. Seed 42 RAM observations cover only an interval after loading. All runs used the local RTX 3050, not a T4. Python 3.11.9, Torch 2.15.0+cu132, Transformers 4.57.6, Diffusers .35.2, Accelerate 1.11.0. OpenCV-headless 5.0.0.93 was added for Canny without upgrading the ML stack. A pure Python PDF reader wheel was used for local literature reading, not installed as an application dependency.

## 13. Reproduction and implementation boundaries

From the repository root, with the recorded CUDA-compatible environment:

```powershell
python -m pip install -e ".[cultural-validation]"
$env:PYTHONPATH = (Resolve-Path src).Path
python -B results/phase8_cultural_validation/fetch_fallback_weights.py
$env:HF_HUB_OFFLINE = "1"
python -B -m scripts.instruction_edit --input results/phase8_cultural_validation/case1/reproduce_request_seed_42.json --config results/phase8_cultural_validation/case1/editor_config.json --out outputs/phase8_reproduction_seed42
python -B -m scripts.instruction_edit --input results/phase8_cultural_validation/case1/reproduce_request_seed_43.json --config results/phase8_cultural_validation/case1/editor_config.json --out outputs/phase8_reproduction_seed43
python -B results/phase8_cultural_validation/verify_outputs.py
python -B -m unittest discover -s tests -v
```

Use fresh directories. The verifier checks the included saved outputs; for fresh reproductions, independently reopen their PNGs and apply the same mask/protected RGB comparisons. Repeated GPU generation is not promised bit-identical across software/hardware; fixed conditions and recorded hashes make this run traceable. No additional model inference is part of package validation. Source and prototype/control PNGs are included as exact inputs. All fallback weights/checksums are fetched explicitly; offline loading never silently switches models or downloads another backend.

New code: `stages/instruction_editor.py`, `scripts/instruction_edit.py`, focused tests and one optional dependency extra. Existing captioning/planning/localization/SAM/SD1.5/review code and historical experiment bytes remain unchanged. The existing final report remains the previous prototype assessment; this is the new Phase 8 research report, not a rewritten historical success claim.

## 14. Evidence-supported conclusion

- **Technical execution/locality:** demonstrated for two real SDXL+Canny local runs, independent pixel checks passed.
- **FLUX/T4 feasibility:** not established; no actual run, weight download or T4 connection.
- **Single-case visual result:** one failure and one provisional samosa-like replacement with realism/boundary concerns.
- **Human-confirmed cultural success:** unavailable; PENDING_HUMAN_EVALUATION, no PASS.
- **Pilot repeatability:** not evaluated; six-case expansion withheld.
- **Automated end-to-end authorization:** not demonstrated; actual Qwen REVIEW/zero candidates remains untouched.

The evidence supports separating object replacement from recoloring and shows that a structurally conditioned fallback can execute on limited hardware. It does **not** establish culturally correct, reliable transcreation. The bounded experiment is closed for independent review with both outputs preserved, rather than expanded until a favorable image is found.
