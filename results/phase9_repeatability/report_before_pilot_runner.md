# Six-case guided cultural replacement pilot

## Objective and fixed cases

Test whether the existing reference-guided workflow repeats beyond the user-accepted croissant-to-samosa example. The [six-case manifest](../results/phase9_repeatability/frozen_manifest.json) was hashed and frozen **before any new composite**. Case1 remains byte-identical. Five new cases were executed, spanning three food cases and three objects (two headwear and one drinkware). [Selection log](../results/phase9_repeatability/candidate_selection.json).

| Case | Research source ? target context | Technical | Provisional visual | Human review |
|---|---|---|---|---|
| 1 | French croissant ? Indian samosa | PASS, historical recheck | STRONG | PASS, supplied user feedback |
| 2 | German-associated pretzel ? French croissant | PASS | STRONG | PENDING_USER_REVIEW |
| 3 | American-style cookie ? Japanese yaki-onigiri | PASS, corrected B | PARTIAL | PENDING_USER_REVIEW |
| 4 | Italian Borsalino fedora ? Moroccan-associated fez | PASS | STRONG | PENDING_USER_REVIEW |
| 5 | Moroccan-associated fez ? Italian Borsalino fedora | PASS, corrected B | PARTIAL | PENDING_USER_REVIEW |
| 6 | Generic handled mug ? Japanese-style wabi-sabi tea bowl | PASS | PARTIAL | PENDING_USER_REVIEW |

Culture labels describe intended associations, not unique ownership, shooting location or cultural authenticity. The generic mug is the weakest culturally specific source. Snacks retain their broad function, hats remain headwear, and vessels remain drinkware; this does not prove preservation of dietary or ceremonial meaning. [Context and references](../results/phase9_repeatability/cultural_context.md).

## Method and provenance

All cases use **REFERENCE_GUIDED_COMPOSITING / RESEARCH_ONLY**: manually chosen photographic references and placement, source-object/background cleanup, aspect-preserving resizing and explicit compositing. No model was invoked and no automated plan was promoted. The existing compositor and all validation/review policies were unchanged. This is guided photographic replacement, not autonomous cultural planning or generative understanding.

Original photographs and redistribution terms were checked on their Commons description pages. Renee Comet/NCI pretzel and cookie are public domain; Ocdp's onigiri and Petr Kratochvil's croissant are CC0. Kjetil Ree's fedora and Edouard Hue's fez are CC BY-SA3.0; Filo g?n's mug is CC BY-SA4.0; ottmarliebert.com's bowl is CC BY-SA2.0. Exact files, SHA-256s, author links and derivative licensing are in [provenance](../results/phase9_repeatability/asset_provenance.json) and [attribution](../results/phase9_repeatability/LICENSE_AND_ATTRIBUTION.md). Case1 retains Kaushalspeed's CC BY-SA4.0 reference.

The isolated source object's main RGB component plus cleanup margin and the explicit target footprint define a declared composite region. Before case5 execution, native mask inspection found disconnected tassel strands; the documented source/tassel envelope was added, retaining initial preflight files. This was a preflight correction, not an unrecorded image attempt. References use inspected photo patches with native contact shadows or explicit manual polygons. These are not ground-truth segmentation masks or SAM approvals. See [annotations](../results/phase9_repeatability/annotations.json) and per-case masks/requests.

## Actual attempts and observations

Five primary composites completed. Only cases3 and5 used their one allowed correction. All seven new outputs remain saved; no other variants or hidden retries were made.

- **Case2:** one recognizable croissant, photographic lamination and native contact shadow. Slight enlargement softness remains. Strong provisional isolated-scene integration.
- **Case3:** A retained a faint original-cookie shadow below the rice snack. B widened the explicit source-shadow cleanup, preserving target conditions. The rice snack is recognizable, but tight polygon edges, perspective and contact-shadow mismatch retain a cutout impression. Partial.
- **Case4:** one recognizable fez with felt/tassel detail and native reference shadow. Its illumination differs from the original hat, but is coherent enough on white for a strong provisional assessment. Faint original background flecks remain protected.
- **Case5:** A's hat looked unsupported. B changed the opaque reference photo-patch matte to a hat contour and added a modeled shadow, keeping scale/crop/pose fixed. These are coupled changes, not an isolated causal experiment. The shadow still appears detached and the hat can look floating. Partial; no third correction.
- **Case6:** the handled blue mug and its hard cast shadow were removed; the handleless tea vessel is recognizable. The low-resolution reference is soft and the modeled shadow appears detached. Partial; no speculative extra attempt.

![Six fixed source/replacement comparisons](../results/phase9_repeatability/pilot_review_sheet.jpg)

Each case folder contains `comparison.jpg`, a native500px detail pair, `review_summary.json`, actual attempts and independent pixel verification. Visual labels above are the assistant's qualitative assessments. **None of the five new results has a human success decision.** Case1's PASS comes solely from the user's explicit Phase9 baseline declaration, not three reviewers or invented numeric ratings.

## Verification, runtime and tests

Independent disk reopening checked dimensions, binary regions, every RGB pixel outside the permitted region, protected pixels, input/output hashes, nonzero changes, the fixed-case manifest and attempt budgets. All **8 saved results** (historical plus7 new) have **zero outside-region changes and zero protected differences**. The source object is visually absent in the selected final images; pixel locality alone is not an object-identity or realism test. [Detailed checks](../results/phase9_repeatability/all_pixel_verification.json).

| Case/condition | Dimensions | Changed inside | Outside/protected changes | Composite wall time |
|---|---|---:|---:|---:|
| 1 historical B | 1280?853 | 469,215 | 0 / 0 | .384 s, inherited |
| 2 A | 2700?1800 | 2,499,350 | 0 / 0 | .817 s |
| 3 A | 2700?1800 | 2,357,135 | 0 / 0 | 1.148 s |
| 3 B | 2700?1800 | 2,404,354 | 0 / 0 | 1.190 s |
| 4 A | 1952?1732 | 2,367,894 | 0 / 0 | 1.204 s |
| 5 A | 5760?4320 | 11,426,476 | 0 / 0 | 3.725 s |
| 5 B | 5760?4320 | 11,815,546 | 0 / 0 | 4.499 s |
| 6 A | 2008?1754 | 1,298,848 | 0 / 0 | .567 s |

CPU-only Python3.11.9/Pillow13/NumPy2.4.6; OpenCV5 was used in mask preparation. No CUDA/model memory was allocated by this experiment. Peak CPU memory and full preparation/download time were not instrumented. Composite timings include input loading, computation and output saving; they exclude manual selection/annotation and are not model benchmarks.

The full project-local suite passed **451/451 before** (38.494s unittest time) and **451/451 after** (38.379s), with zero failures/errors. No application code changed, so no extra implementation-mirroring unit tests were added. The separate pilot validator checks real saved data, hashes and budgets. All391 preexisting source/config/test/report/Phase8 files in the entry snapshot remain byte-identical. Existing Qwen REVIEW and human decisions remain untouched. [Tests](../results/phase9_repeatability/tests_after.log), [history check](../results/phase9_repeatability/historical_preservation.json).

## Outcome, limitations and next step

**6/6 technically completed**, including the inherited baseline; **3 provisionally strong, 3 partial, 0 selected-final visual failures**. Of these, only **2 new cases** are provisionally strong. **Human acceptance:1 historical PASS,5 pending.** This is not a6/6 cultural-success claim. Primary defects and unsuccessful corrections are retained, not hidden.

The workflow repeats technically on carefully selected, mostly white isolated-object photographs. Contact shadows, exact lighting, cutout boundaries and reference resolution remain visual weaknesses. Near-white background reconstruction does not establish arbitrary-scene removal; permitted regions include declared background/shadow reconstruction. The two inverse hat cases reuse assets, and the croissant is reused as a reference, so the pilot is not statistically independent. Manual target selection, pose/scale decisions and licensing work are substantial; there is no automatic relighting or3D geometry matching. Cultural labels remain tentative and cannot substitute for actual target-culture judgment.

Next: simple ChatGPT review of all five comparisons, beginning with **cases2 and4**, then explicit feedback on the partial cases. No new review framework or automatic experiment expansion is proposed. [Reproduction commands](../results/phase9_repeatability/REPRODUCTION.md). The evidence supports **limited guided repeatability with mixed visual quality**, not generalization or autonomous end-to-end authorization.
