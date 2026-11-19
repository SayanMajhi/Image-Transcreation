# Culture-Aware Image Transcreation: final project review

## 1. Project objective
Investigate user-directed cultural reinterpretation of a photograph while preserving its scene. The V4 target is pale, Italian-labeled spaghetti reinterpreted as visibly reddish-brown Indian-style masala spaghetti. This is an explicit research objective, not a claim of universal Indian tradition or expert-verified authenticity.

**PROJECT STATUS: PARTIALLY COMPLETE.** All requested V4 stages and both allowed generations executed. Technical locality passed; neither generated image meets the visual objective. The completed package records unsuccessful results rather than claiming a finished cultural transformation.

## 2. Architecture

```text
Automated: photo -> SmolVLM -> Qwen raw draft -> deterministic validator
           -> REVIEW/ABSTAIN stop; PROPOSE still needs actual review

Guided RESEARCH_ONLY: explicit user objective -> original-object DINO query
           -> inspected source box -> SAM candidates -> research mask/refinement
           -> source/provenance/protection checks -> SD inpainting
           -> original-resolution binary composite -> independent pixel checks
```

The guided route is independent of rejected planner candidates. An image-generation result is not a human-approved cultural edit. No raw/final Qwen output, historical decision or approval policy was rewritten.

## 3. Models and responsibilities

| Stage | Model / pin | Responsibility |
| --- | --- | --- |
| Caption | SmolVLM-500M-Instruct, `a7da5b986cb59b408707209984f360a5f4ad7e47` | Unverified visual description with completion metadata |
| Planning | Ollama `qwen2.5:3b`, digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`, Q4_K_M | Structured cultural-edit draft |
| Localization | Grounding DINO Tiny, `a2bb814dd30d776dcf7e30523b00659f4f141c71` | Boxes for the original object |
| Segmentation | SAM ViT-Base, `70c1a07f894ebb5b307fd9eaaee97b9dfc16068f` | Original-resolution candidate masks |
| Generation | SD v1.5 Inpainting, `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb` | Localized appearance generation |

Existing Python contracts, deterministic candidate quarantine, review tools, CLI, crop restoration and hard compositing were reused. Models ran sequentially on Windows/Python 3.11 with an RTX 3050 Laptop GPU, 4 GB. No application-code, checkpoint, model setting or dependency change was needed for V4.

## 4. Automated versus guided execution

The real SmolVLM caption begins: **"In the foreground of this image is a plate of spaghetti with parsley on top."** It reaches EOS after **93 tokens**, without truncation. Its exact herb identity and guess that a small piece is mushroom/meat remain model claims, not verified visual facts.

Qwen returned raw **PROPOSE**, but used `masala-coated spaghetti strands` as its original-object localization phrase. It also falsely claimed some scene details were user-verified. No personal human inspection/verified-object record was fabricated for the new source; the automatic request correctly has an empty verified-object list.

The unchanged validator returned **REVIEW with zero released candidates**. Issues: `UNVERIFIED_SOURCE_OBJECT`, `SOURCE_LOCALIZATION_MISMATCH`, `USER_CONSTRAINTS_UNRESOLVED` (human-verification warning), and `EDIT_UNCERTAINTY_UNRESOLVED`. The automated route stopped. Qwen's scene-attribution error was flagged in this visual/manual assessment; text validation cannot prove every semantic claim.

The separate guided route used the actual V4 protocol's source phrase, editable scope and target. It did not recover or release the quarantined Qwen candidate. No named reviewer or mask approval was invented.

[Actual complete caption](../results/phase7_integration/v4_completed/automated/caption.json), [raw Qwen and full audit](../results/phase7_integration/v4_completed/automated/planner_audit.json), [final plan/issues](../results/phase7_integration/v4_completed/automated/validated_plan.json), [stage/cleanup log](../results/phase7_integration/v4_completed/automated/pipeline_result.json).

## 5. Source-image attribution

**Spaghetti aglio e olio**, by **10Rosso**, [Wikimedia Commons description](https://commons.wikimedia.org/wiki/File:Spaghetti_aglio_e_olio.jpg), [original Flickr source](https://www.flickr.com/photos/29768027@N07/4345842519/), **[CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)**. The Commons record reports the Flickr license verification at transfer. The downloaded original matches its published SHA-1 and the user-provided expected SHA-256.

Source: JPEG, **2272 x 1704**, SHA-256 `062eb9f18e0175dec675f9e1edefd3ef1238837e627727e58b9d9c309fa49d0e`. The photo visibly shows thick pale pasta with attached green seasoning; the Italian dish label comes from its source description, not independent proof of origin. No Japanese-origin claim applies.

The original JPEG remains unchanged. Generated PNGs, raw crops, overlays and comparisons are identified as modifications, with photographer credit/license retained and no endorsement implied. [Original source](../results/phase7_integration/v4_completed/source.jpg), [attribution and modifications](../results/phase7_integration/v4_completed/ATTRIBUTION.md), [source/hash/license evidence](../results/phase7_integration/v4_completed/source_and_license.json).

## 6. Ramen negative-case findings

Earlier ramen runs established safe stopping, source/replacement separation problems, false semantic detections, unsafe SAM boundaries and exact outside-mask compositing. A 4,224-pixel refined ramen edit generated text-like marks. V3's 20,484-pixel, three-region mask removed the text artifact but failed seasoning and erased lower-left noodle structure. All historical images, raw plans, final REVIEW results, Sayan's MATERIAL_UNRESOLVED review and previous ZIPs remain unchanged. Those failures motivated this simpler licensed source; they are not relabeled as successes.

## 7. Spaghetti demonstration methodology

The explicit V4 scope permits visible pasta, attached seasoning and necessary food surface changes. It protects plate/rim, background/unrelated objects, framing and lighting direction; strand structure should remain plausible. This is RESEARCH_ONLY operator scope, not a human-approved Qwen proposal.

One caption call, one Qwen call, one DINO condition and one SAM box-prompt run were followed by one fixed refined mask and at most two predeclared diffusion conditions. The earlier unavailable-protocol blocker was resolved by the complete user V4 instructions. No source substitution, additional seed, threshold search, model switch or post-generation mask revision occurred.

[Protocol/preregistration](../results/phase7_integration/v4_completed/protocol_and_preregistration.json), [frozen diffusion inputs](../results/phase7_integration/v4_completed/diffusion_frozen.json).

## 8. Grounding and segmentation results

DINO queried **`spaghetti noodles`**, box threshold .30 / text .25, FP32, seed 42. It returned one source-object box: `[3.6668,394.7537,2266.1372,1698.0287]`, confidence **.918594**. Inspection found the food mound, while the rectangular box also contained plate margins. Prediction 0 was explicitly selected from that inspection, not automatically accepted by score.

| SAM candidate | Predicted score, not measured IoU | Foreground pixels |
| --- | ---: | ---: |
| 0 | 0.907188 | 2,476,478 |
| 1 | 0.786805 | 1,316,995 |
| 2 | 0.364945 | 328,765 |

Candidate 0 coherently covers most pasta, but peripheral plate speckles and internal gaps are uncertain. Candidates 1/2 omit many strands. All original predictions and overlays were retained. Candidate 0 is a geometric reference only; no SAM acceptance record was invented.

A manually traced inward food polygon avoids the plate/background edge. Before diffusion, every original-SAM background gap inside that polygon was conservatively protected with a 4-connected component bounding rectangle and three-pixel margin: **116 gap exclusions**. This preserves uncertain pixels without claiming every gap is actually ceramic. Draft geometry before this correction is retained separately; no draft was generated through.

Final mask origin: **RESEARCH_MASK_MANUALLY_REFINED**. Dimensions **2272 x 1704**, binary **0/255**, foreground **1,846,716 pixels**, **47.7004% of the photograph**, bounds `[75,470,2191,1621]`. It adds zero pixels to the SAM reference and removes 629,762. It has **zero intersection with full protected-region masks**. These percentages describe image/reference area, not ground-truth pasta coverage.

Full/native overlays and the actual 512-grid crop were inspected before generation. Pasta strands remain visible after resizing; the editable region is substantial rather than a tiny patch. The uncertain gap protection is conservative operator geometry, not pixel ground truth. It later contributes to visible rectangular seams, a quality limitation retained in the results.

[Detection/annotation](../results/phase7_integration/v4_completed/localization/grounding), [all SAM candidates](../results/phase7_integration/v4_completed/sam/segmentation), [exact editable/protected polygons](../results/phase7_integration/v4_completed/annotations.json), [full mask overlay](../results/phase7_integration/v4_completed/mask_overlay.png), [protection overlay](../results/phase7_integration/v4_completed/protected_overlay.png), [mask/hash checks](../results/phase7_integration/v4_completed/mask_checks.json), [actual processing preview](../results/phase7_integration/v4_completed/processing_overlay_preview.png).

## 9. Inpainting settings

Both A/B use the pinned dedicated 9-channel SD inpainting model, safetensors FP16 variant, CPU model offload, batch 1, seed **42**, **20 requested steps**, guidance **7.5**, configured strength **.9**, DDIM scheduler and **18 effective denoising steps**. Working size **512 x 512**; original-resolution restoration and original-mask hard compositing are unchanged.

The local crop is `[11,406,2255,1685]` (2244 x 1279), padded `[0,482,0,483]` to a square before consistent resizing. Source geometry was not stretched. A/B source, mask, crop, sampler and all numerical settings are identical.

Positive prompt, unchanged in both conditions:

> Photorealistic spaghetti strands coated in reddish-brown Indian masala sauce and spices, visible individual pasta strands, natural food texture, matching the original composition, camera angle and lighting.

A has no negative prompt. Its unnatural insert/weak coating justified the single predefined B condition. B adds only:

> text, letters, printed labels, watermark, logo, packaging, smooth plastic, melted food, distorted pasta, disconnected noodle strands

Token lengths including special tokens: positive **38**, B negative **31**, both below **77**. Exactly **two** diffusion calls occurred, one per condition, zero retries/OOM events. `--max-attempts 1` enforced the bound. The negative prompt remains an explicit refined-research input, not a production default.

[A exact input](../results/phase7_integration/v4_completed/input_A.json), [B exact input](../results/phase7_integration/v4_completed/input_B.json), [negative-only comparison](../results/phase7_integration/v4_completed/A_B_input_comparison.json), [A assessment before B](../results/phase7_integration/v4_completed/A_visual_assessment_before_B.json).

## 10. Original/generated comparisons

![Original and both actual modified photographs](../results/phase7_integration/v4_completed/original_generated_comparison.png)

[Original](../results/phase7_integration/v4_completed/source.jpg), [A final PNG](../results/phase7_integration/v4_completed/A/final.png), [B final PNG](../results/phase7_integration/v4_completed/B/final.png), [native food detail](../results/phase7_integration/v4_completed/food_native_comparison.png), [native boundary detail](../results/phase7_integration/v4_completed/boundary_native_comparison.png). Raw 512 crops and all pipeline artifacts are preserved in the A/B directories.

## 11. Pixel-integrity results

| Independent saved-file check | A | B |
| --- | ---: | ---: |
| Original/final dimensions | 2272 x 1704 | 2272 x 1704 |
| Editable pixels | 1,846,716 | 1,846,716 |
| Actual changed inside mask | **1,846,657** | **1,846,686** |
| Changed outside mask | **0** | **0** |
| Maximum outside-mask channel difference | **0** | **0** |
| Changed in annotated protected regions | **0** | **0** |
| Protected-region pixels checked | 1,550,006 | 1,550,006 |

The standalone verifier imports no model or compositor. It reopens source/final/mask PNG/JPEGs, checks hashes/dimensions/binary values, and compares every decoded RGB pixel. Protected geometry is assistant research annotation; numerical equality does not independently prove semantic segmentation or cultural quality.

[A verification](../results/phase7_integration/v4_completed/A_pixel_verification.json), [B verification](../results/phase7_integration/v4_completed/B_pixel_verification.json), [independent verifier](../results/phase7_integration/v4_completed/verify_outputs.py).

## 12. Actual visual evaluation

**Visual objective: FAIL in both A and B.** Generation completed, but neither is a credible masala-coated spaghetti demonstration.

- **Recognizable food/strands:** pasta-like ribbons remain, but many strands broaden, flatten, soften or lose original continuity.
- **Coating:** a conspicuous red food-like chunk/insert appears rather than coherent reddish-brown sauce on the strands. Most pasta remains pale. A red patch alone is not cultural adaptation.
- **Texture/lighting:** some food-like texture, but waxy/soft regions and the synthetic insert do not match the source material and flash-lit strand structure convincingly.
- **Plate/background:** original RGB pixels are exactly preserved outside the mask; no global composition change.
- **Seams:** hard-compositing contours and frozen rectangular gap islands produce visible mosaic-like transitions. Conservative protection sacrifices visual continuity.
- **Text/graphics:** no obvious text-like artifact in inspected outputs. Absence of text does not imply target success.
- **Normal viewing:** the change is noticeable as an unnatural insert/rearrangement, not a believable masala preparation. It is a substantial but partial localized attempt; untouched pasta margins remain.

Raw generated crops already contain the unwanted insert and pale pasta, so model/prompt following contributes independently of compositing. Coarse conservative exclusions add a separate seam problem. Flash exposure and working scale may contribute; no single cause was experimentally isolated. Both failures are retained, without cherry-picking, cleanup, mask enlargement or additional calls.

[Full qualitative assessment](../results/phase7_integration/v4_completed/visual_evaluation.json).

## 13. Tests and engineering quality

Baseline **412 passing tests** is the prior V4-readiness run on a byte-identical source/config/test checkout; its log and identity checks are retained. Current full rerun: **412 passed, zero failures/errors**, 37.195 s unittest / 41.473 s process wall time. Tests are offline synthetic/mocked inference, distinct from the real runs above.

No implementation bug required changing application code, and no new tests merely mirroring existing behavior were added. Existing validator, candidate quarantine, review isolation, hash tampering, research-mask provenance, negative-prompt isolation, bounded retries and exact compositing tests remain intact. All prior ramen/V3/readiness artifacts, decisions, model configurations and source files remain unchanged. No commit/push occurred.

[Full current test log](../results/phase7_integration/v4_completed/tests_after.json), [baseline identity](../results/phase7_integration/v4_completed/baseline_identity.json), [historical preservation](../results/phase7_integration/v4_completed/preservation_after.json), [exact software versions](../results/phase7_integration/v4_completed/environment.json).

## 14. Runtime and memory

| Diffusion condition | Load s | Inference s | Stage s | CLI wall s | Peak allocated CUDA GiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 7.612 | 10.984 | 23.388 | 29.033 | 2.472 |
| B | 8.244 | 10.153 | 22.939 | 28.180 | 2.472 |

Each diffusion peak is **2,654,782,464 bytes**. Other actual forward/request measurements: caption **5.122 s / 1.098 GiB**, Qwen HTTP planning **12.397 s** (1,142 input / 353 output tokens; peak GPU memory not measured), DINO **1.085 s / 1.705 GiB**, SAM **.862 s / 1.924 GiB**. Loading is recorded separately in stage JSONs. These are single-run observations, not comparative benchmarks. PyTorch allocation excludes driver/desktop/other-process memory.

Caption references were released before Qwen, Ollama idle/unloading was confirmed, detector/SAM closed in finally blocks, and fresh sequential processes executed diffusion. No simultaneous project-model residency, CUDA OOM or CPU fallback occurred in the real runs.

[A execution log](../results/phase7_integration/v4_completed/A_execution.json), [B execution log](../results/phase7_integration/v4_completed/B_execution.json), [A model/settings/memory](../results/phase7_integration/v4_completed/A/inpainting.json), [B model/settings/memory](../results/phase7_integration/v4_completed/B/inpainting.json).

## 15. Limitations

The visual target remains unachieved under the allowed two conditions. Exact preservation is easier to guarantee than plausible food recoloring and continuous strand geometry. Conservative gap boxes may protect genuine food as well as uncertain gaps; no independently annotated food/plate mask exists. Source flash/overexposure obscures fine detail. The low-memory 512-grid generative model does not guarantee exact strand geometry, uniform sauce coverage or cultural appropriateness. Qwen still makes semantic/localization and attribution errors. No expert cultural evaluation or human mask approval is claimed.

The historical ramen MATERIAL_UNRESOLVED verdict is not cleared by this separate scope. No approved automatic Qwen-to-diffusion cultural transformation has been demonstrated. More optimization would require a new targeted mentor instruction; this run does not silently change strength, mask, prompt, model or seed beyond the protocol.

## 16. Reproduction instructions

From the repository/extracted package root with Python 3.11, tested dependencies, compatible CUDA Torch, cached pinned weights and Ollama with the recorded Qwen digest. Install via `python -m pip install -e ".[inpainting]"` if needed; no package was upgraded in this run.

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$env:HF_HUB_OFFLINE = "1"
python -B -m unittest discover -s tests -v
python -B results/phase7_integration/v4_completed/verify_outputs.py
```

Actual live CLI stages used these request files:

```powershell
python -B -m transcreation.cli run --input results/phase7_integration/v4_completed/automated_request.json
python -B -m transcreation.cli run --input results/phase7_integration/v4_completed/localization_request.json
python -B -m transcreation.cli run --input results/phase7_integration/v4_completed/segmentation_request.json
```

They refuse to overwrite existing output directories. For fresh stage replay, copy the request and set a new output directory. Do not regenerate upstream evidence and silently reuse stale downstream hashes. The raw model audits are not rewritten. Separate path-normalized copies are provided for portable artifact references; GPU bitwise reproduction across other hardware/OS is not asserted.

Exact fixed diffusion conditions into fresh directories:

```powershell
python -B -m scripts.inpaint --refined-input results/phase7_integration/v4_completed/reproduce_input_A.json --out outputs/v4_reproduction_A --max-attempts 1
python -B -m scripts.inpaint --refined-input results/phase7_integration/v4_completed/reproduce_input_B.json --out outputs/v4_reproduction_B --max-attempts 1
```

B was conditional on A failure in the actual experiment. These commands reproduce failed visual conditions, not approved edits. The full final annotation JSON directly reconstructs the mask via existing `rasterize_annotations`; no synthetic SAM metadata is needed. Source, SAM, mask, polygon and protected-region SHA-256 values must match before inference. [Path-copy explanation](../results/phase7_integration/v4_completed/reproduction_paths.json).

## 17. Honest project status

| Area | Status |
| --- | --- |
| All five existing models | Actually executed for V4 |
| Automated route | Correctly stopped at REVIEW; zero candidates released |
| Guided research execution | DINO/SAM/refinement and two real SD generations completed |
| Licensed source/provenance | Verified expected original hash; CC BY 2.0 attribution retained |
| Numerical locality/plate-background preservation | PASS, zero outside/protected differences |
| Credible masala-spaghetti visual objective | **FAIL in both conditions** |
| Regression suite | 412 passed, zero failures/errors |
| Human approval / cultural certification | Not claimed or fabricated |
| Project | **PARTIALLY COMPLETE** |

The earlier missing-protocol blocker is resolved and is not the reason for this outcome. The remaining issue is visual quality/model following and mask-boundary consistency. Stop after the bounded V4 protocol for independent mentor evaluation. Deliverable: `results/final_project_review_v4_completed.zip`.
