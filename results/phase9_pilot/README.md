# Phase 9: Six-case repeatability pilot of reference-guided cultural replacement

*2026-11-12. Implementation, execution and visual notes by the AI coding assistant (Claude);
research direction, the historical samosa review and all pending reviews belong to the project user.*

## 1. Research objective

Phase 8 produced one result the user judged natural: croissant → samosa, made by
REFERENCE_GUIDED_COMPOSITING. The question here is:

> Does reference-guided cultural replacement repeat for other cultural objects, or was the
> samosa an isolated success?

We report six dimensions separately: cultural relevance, semantic preservation, visual
realism, scene preservation, technical reproducibility and autonomy. No combined "accuracy"
number is reported.

## 2. Existing architecture

```text
Automated:      photo -> SmolVLM -> Qwen2.5-3B -> deterministic validator -> human review boundary
Guided research: explicit spec -> DINO -> SAM -> SD v1.5 | baseline | REFERENCE_GUIDED_COMPOSITING -> verification
Phase 9:        configs/phase9_pilot_cases.json -> scripts.pilot {validate, run, verify, package}
```

The pilot reuses `transcreation.stages.reference_replacement` (`run_request`/`replace_object`).
New code: `src/transcreation/pilot.py` (manifest validation, orchestration, verification,
packaging), `scripts/pilot.py` (CLI) and `tests/test_pilot.py`. The compositor gained one
default-off option, `patch_fade_sigma`; with the default it reproduces every historical
output byte for byte. No planner, model, review or approval code changed, and no Qwen
REVIEW/ABSTAIN decision was bypassed.

## 3. Historical successful samosa case (CASE_01)

| Item | Value |
|---|---|
| Source → target | croissant (Petr Kratochvil, CC0) → samosa (Kaushalspeed, CC BY-SA 4.0) |
| Frozen output | `results/phase8_cultural_validation/true_object_replacement/B/final.png`, SHA-256 `bb922916…ddfb` |
| User review | "The new reference-guided samosa replacement B looks natural and realistic." One direct user review; not an independent panel |
| Pilot handling | copied byte for byte; never regenerated. Verify replays it in memory only |
| Reproduction | `scripts.reference_replacement` into a new folder: **decoded pixels identical and PNG bytes identical** (`results/phase9_pilot/samosa_B_reproduction.json`) |

## 4. Frozen six-case pilot

The case set was frozen on **2026-11-11 20:10 UTC, before any new composite**
(`results/phase9_repeatability/frozen_manifest.json`, SHA-256 `741ce80c…419b`). This milestone
restated the same six cases with full provenance in `configs/phase9_pilot_cases.json`. No case
was substituted. While being written, the manifest failed validation on one label
inconsistency (CASE_06 direction "Western" vs culture "Generic Western"). The label was
corrected before any run.

| ID | Source → target | Direction | Category | Attempts |
|---|---|---|---|---|
| CASE_01 | croissant → samosa | French→Indian | food | historical |
| CASE_02 | salted pretzel → croissant | German→French | food | A |
| CASE_03 | chocolate-chip cookie → yaki-onigiri | American→Japanese | food | A, B |
| CASE_04 | Borsalino fedora → fez | Italian→Moroccan | headwear | A, B |
| CASE_05 | fez → Borsalino fedora | Moroccan→Italian | headwear | A, B |
| CASE_06 | handled mug → wabi-sabi tea bowl | Generic Western→Japanese | drinkware | A |

The cases cover 6 directions and 3 categories, and all 5 new cases have a non-Indian target.
Culture labels are intended associations, not claims of national ownership.

## 5. Case-selection rationale

Each pair keeps the object's purpose: a single snack, a single hat, a single drinking vessel.
All are isolated studio photos on near-white backgrounds with clear boundaries, chosen so that
licensing and pixel preservation could be checked rigorously. That is a **convenience
selection**:

- The inverse hat cases reuse the same two photos.
- The CASE_02 croissant is the CASE_01 source photo.
- The mug has weak source-culture specificity.

So the cases are not statistically independent and do not test cluttered scenes. Context
sources are in `results/phase9_repeatability/cultural_context.md`.

## 6. Image sources and licensing

All 9 photographs come from Wikimedia Commons. On 2026-11-12 each local file's SHA-1 was
compared with the current Commons file through the imageinfo API: **9/9 match**.

| Image | Creator | Licence used |
|---|---|---|
| Croissant-Petr Kratochvil.jpg | Petr Kratochvil | CC0 |
| Samosa-and-Chatni.jpg | Kaushalspeed | CC BY-SA 4.0 |
| Pretzel (1).jpg | Renee Comet / NCI | Public domain |
| Chocolate chip cookie.jpg | Renee Comet / NCI | Public domain |
| Yaki-Onigiri 001.jpg | Ocdp | CC0 |
| A fedora hat, made by Borsalino.jpg | Kjetil Ree | CC BY-SA 3.0 (see note) |
| Fez.jpg | Edouard Hue | CC BY-SA 3.0 |
| Mug.jpg | Filo gèn' | CC BY-SA 4.0 |
| Contemporary wabi-sabi tea bowl.jpg | ottmarliebert.com | CC BY-SA 2.0 |

**Recorded discrepancies.**

- **Fedora:** the structured metadata says CC BY 2.5, while the permission text links CC
  BY-SA 3.0 (the file is multi-licensed). We use CC BY-SA 3.0, the stricter option.
- **Cookie and tea bowl:** two credit details from earlier notes ("colour correction by
  Hohum", "o2ma") were not found in the API fields.

Derivatives of BY-SA photos stay BY-SA. Full records: `images` in the manifest,
`results/phase9_pilot/license_recheck.json` and
`results/phase9_repeatability/LICENSE_AND_ATTRIBUTION.md`.

## 7. Reference-guided replacement method

For each attempt, a frozen request names:

- the source photo;
- a reference photo plus its selection mask (a manual polygon, contour or photo patch);
- a permitted region (the source object plus margin, its shadow, and the target footprint);
- a protected region;
- placement, scale and shadow parameters.

The compositor then:

1. paints the whole permitted region with the inspected background colour, so no source
   object survives under the cutout;
2. adds the documented soft shadows;
3. pastes one aspect-preserved reference cutout;
4. restores every pixel outside the region from the source.

**Background reconstruction is uniform near-white fill.** That suits these studio photos only;
it is not a general method for complex backgrounds. A researcher selected every reference,
mask, position and scale. This is guided photographic compositing, not generation.

## 8. Experimental settings

- **Software and hardware:** CPU only on an AMD laptop (Windows 11, Python 3.11.9,
  Pillow 13.0.0, NumPy 2.4.6). No GPU, model weights, Ollama or network were used.
- **Attempt budget:** two per new case, the second only to fix one diagnosed defect.
- **Selection rule (declared before running):** the last technically successful attempt is
  shown for review; both attempts are kept.
- **The one new attempt this milestone, CASE_04 B:**
  - *Diagnosis:* the top edge of A's rectangular fez photo patch (mean RGB about 253 against
    the 255 plate) shows as a faint line.
  - *Single change:* `patch_fade_sigma = 15` reference pixels.
  - *Pre-check:* no reference pixel with min(RGB) < 235 lies within 40 px of any patch edge.
  - *Freeze:* the request was frozen before execution (`case4/request_B.json`).
- CASE_03 B and CASE_05 B come from the earlier session (cleanup rectangle; contour matte
  plus shadow).

## 9. Actual six-case outputs and status

| Case | Run | Selected | Assistant visual note | Human review |
|---|---|---|---|---|
| CASE_01 | copied | historical | STRONG | **PASS** (user, historical) |
| CASE_02 | OK | A | STRONG | PENDING_USER_REVIEW |
| CASE_03 | OK, A+B | B | PARTIAL | PENDING_USER_REVIEW |
| CASE_04 | OK, A+B | B | PARTIAL | PENDING_USER_REVIEW |
| CASE_05 | OK, A+B | B | PARTIAL | PENDING_USER_REVIEW |
| CASE_06 | OK | A | PARTIAL | PENDING_USER_REVIEW |

Outputs are in `results/phase9_pilot/run_001/CASE_xx/`: `final.png`, `comparison.jpg`,
`closeup_native.png`, `attempts.jpg`, `REVIEW.md`, `status.json`, and `attempt_X/` (clean plate
`source_removed.png`, `placed_alpha.png`, `shadow_alpha.png`, `execution.json`).
`overview.jpg` shows all six.

## 10. Pixel-preservation results

Every check below was recomputed from disk by `scripts.pilot verify`, giving **PASS, 0 failures**.

| Case | Att. | Size | Permitted px | Changed inside | Target px | Shadow-only px | Background-only px | Non-white source px → background | Outside / protected changed | Leftover source px | Replay identical | Same as historical | Time |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|---:|
| 01 | hist | 1280×853 | 749,700 | 469,215 | – | – | – | – | 0 / 0 | – | yes | (is historical) | – |
| 02 | A | 2700×1800 | 2,970,760 | 2,499,350 | 2,335,200 | 0 | 635,560 | 519,930 | 0 / 0 | 0 | yes | yes | 0.76 s |
| 03 | A | 2700×1800 | 2,565,107 | 2,357,135 | 1,450,404 | 67,021 | 1,047,682 | 752,911 | 0 / 0 | 0 | yes | yes | 1.23 s |
| 03 | B | 2700×1800 | 3,510,000 | 2,404,354 | 1,450,404 | 67,021 | 1,992,575 | 752,946 | 0 / 0 | 0 | yes | yes | 1.09 s |
| 04 | A | 1952×1732 | 2,537,722 | 2,367,894 | 1,131,600 | 0 | 1,406,122 | 1,199,188 | 0 / 0 | 0 | yes | yes | 1.25 s |
| 04 | B | 1952×1732 | 2,537,722 | 2,367,722 | 1,131,552 | 0 | 1,406,170 | 1,199,212 | 0 / 0 | 0 | yes | new | 1.50 s |
| 05 | A | 5760×4320 | 14,877,000 | 11,426,476 | 10,257,800 | 0 | 4,619,200 | 734,370 | 0 / 0 | 0 | yes | yes | 3.52 s |
| 05 | B | 5760×4320 | 14,877,000 | 11,815,546 | 7,048,727 | 652,669 | 7,175,604 | 3,026,343 | 0 / 0 | 0 | yes | yes | 4.45 s |
| 06 | A | 2008×1754 | 1,518,259 | 1,298,848 | 474,269 | 75,020 | 968,970 | 694,616 | 0 / 0 | 0 | yes | yes | 0.55 s |

How to read the columns:

- **Changed outside / protected:** zero everywhere.
- **Leftover source px:** region pixels outside the target footprint that differ from the
  reconstructed plate plus shadow by more than 2 levels. Zero means no source object remains
  visible beside the new object.
- **Background-only px:** background that was **reconstructed, not preserved**. It is
  reported separately on purpose. "Non-white source px → background" counts source object
  and shadow pixels that were turned into plate there.
- **Same as historical:** run outputs match the earlier session's saved outputs in both
  decoded pixels and bytes. A second full run also matched the first: 38/38 PNGs identical.

Pixel locality does **not** prove realism or cultural correctness.

## 11. Visual-quality findings

These are the assistant's own observations, from full images, contrast-stretched views and
native crops. They are not a human review.

- **CASE_02 (STRONG):** pretzel fully gone. The croissant keeps its own photographed contact
  shadow and lamination, with slight upscale softness. The thin dark line at the left image
  border is in the original photo, outside the region.
- **CASE_03 (PARTIAL):** the onigiri is clearly recognizable with real rice texture. Straight
  polygon cut edges, a camera-angle mismatch (top-down cookie vs angled rice ball) and a weak
  contact shadow give a cut-out look. B removed A's faint leftover cookie shadow.
- **CASE_04 (PARTIAL):** the fez and tassel look real. The faint horizontal line from the
  patch edge remains. **The B correction failed visibly:** it changed only 4,612 pixels, by at
  most 5 levels. The grey band runs deeper than the fade could reach without fading the hat,
  and no third attempt is allowed. The earlier session had rated this case STRONG without
  noticing the line.
- **CASE_05 (PARTIAL):** the fedora is recognizable. The modeled ellipse shadow looks detached,
  so the hat can seem to float, and the lighting comes from the fedora photo.
- **CASE_06 (PARTIAL):** the mug and its hard black shadow are fully removed and the bowl is
  recognizable. But the 600×450 reference is visibly soft at native size, the foot shows faint
  vertical line artifacts, and the flat shadow looks pasted. Fixing this needs a different
  reference photo, which would change a frozen input, so it was not done.

## 12. Successful vs failed cases

- **Technical:** 6/6 complete. 9/9 outputs verified (1 historical + 8 attempts), 0 failures.
- **Visual (assistant, provisional):** 2 STRONG (01, 02), 4 PARTIAL (03–06), 0 FAIL. Of the
  new cases, only 1 of 5 is strong.
- **Correction attempts:** 1 of 3 clearly helped (CASE_03 B). CASE_05 B was a partial
  improvement. CASE_04 B made no visible difference.
- **Human:** 1 PASS (historical), 5 pending.

## 13. Common failure modes

1. Shadows modeled as ellipses look detached; only native reference shadows (CASE_01, 02, 04)
   look grounded.
2. Manual polygon or contour edges read as cut-outs.
3. The camera angle or lighting of the reference differs from the source scene.
4. Rectangular reference patches whose background is not exactly the plate colour leave
   seams.
5. A low-resolution reference looks soft after upscaling.
6. Uniform white background reconstruction works only because every scene is a white studio
   shot.

## 14. Automated vs researcher-guided limitations

- **Researcher-guided steps:** reference selection, masks, scale, position, shadows and
  culture labels were all chosen by researchers or the assistant, not by Qwen or another
  model. Autonomy for these results is therefore **low**.
- **Automated pipeline:** its real example remains REVIEW with zero released candidates.
- **What is and isn't shown:** this pilot shows a repeatable *guided* procedure, not
  autonomous cultural reasoning or scene understanding.

## 15. Human review status

- **CASE_01:** PASS. One user, one sentence, quoted verbatim in the manifest.
- **CASE_02–06:** `PENDING_USER_REVIEW`. The user will judge them in ChatGPT, using
  `comparison.jpg`, `closeup_native.png` and the four plain questions in each `REVIEW.md`.
- **How answers are recorded:** only verbatim, in `human_feedback`. `validate` rejects any
  PASS/FAIL without that evidence.
- One user's review is not the three-independent-reviewer criterion.

## 16. Reproduction commands (all executed 2026-11-12)

```powershell
python -B -m scripts.pilot validate --manifest configs/phase9_pilot_cases.json
python -B -m scripts.pilot run --manifest configs/phase9_pilot_cases.json --out results/phase9_pilot/run_001
python -B -m scripts.pilot verify --run results/phase9_pilot/run_001
python -B -m scripts.pilot package --run results/phase9_pilot/run_001 --out results/archive/repeatability_pilot_review.zip
python -B -m scripts.reference_replacement --request results/phase8_cultural_validation/true_object_replacement/request_B.json --output results/phase8_cultural_validation/true_object_replacement/reproduction_B_phase9
```

Transcript: `results/phase9_pilot/commands.log`. The first `run_001` was built before the
visual notes existed. It was replaced by an identical rerun (38/38 PNGs same); its manifest,
log and verification are kept as `dev_run_000_*`.

**Relocation:** a review ZIP unzipped into an empty folder validated, ran and verified PASS,
with 14/14 final images byte-identical (`relocation_check.json`). The first relocation attempt
exposed a real bug: validate demanded reference copies that the package omits. It was fixed
and a regression test was added. Setup details are in `REPRODUCTION.md`.

## 17. Test results

- **Full suite:** `python -B -m unittest discover -s tests -v` ran **482 tests: 0 failures,
  0 errors, 0 skipped**, in about 48 s (`results/phase9_pilot/tests_full.log`).
- **Before this milestone:** 451/451.
- **New tests (31):** manifest schema and rejections (missing field, duplicate ID, unsupported
  direction, bad path, hash mismatch, missing licence, fabricated approval, attempt budget);
  run outputs, no overwrite and failure isolation; verify (tamper, missing, leftover source,
  replay); packaging (coverage, exclusions, hash mismatch, relocation); CLI; `patch_fade_sigma`.
- One existing ResourceWarning in `test_instruction_editor.py` is unrelated to this work.

## 18. Research conclusion

On carefully chosen isolated white-background photos, reference-guided replacement is
**technically repeatable**. All 5 new cases completed with exact preservation outside the
edit region, deterministic replay and traceable licences. **Visual quality is mixed:** only
one new case looks strong to the assistant, and the user has not yet judged any of them. The
samosa was therefore not a technical fluke. But it is not yet shown to be a repeatable
*visual* success, and it says nothing about cluttered scenes or autonomous cultural
adaptation.

The next step is the user's simple review of CASE_02–06. If more experiments follow, the
evidence points to native-shadow references, matching camera angle and higher-resolution
references as the most valuable changes.
