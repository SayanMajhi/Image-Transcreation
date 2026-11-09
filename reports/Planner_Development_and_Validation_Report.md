# From VLM selection to a validated cultural planner

## Project understanding, experimental findings, fixes, and interview guide

**Prepared:** 9 November 2026. **Scope:** the planner development, experiments,
validation fixes and cleanup recorded after selecting SmolVLM.

This is the consolidated narrative for understanding the project and discussing it
in interviews. Original reports and raw evidence remain unchanged. No models or
tests were rerun to prepare this document. The separate
[VLM selection report](VLM_Selection_Experimental_Findings_Refined.md) explains the
earlier BLIP/Florence/SmolVLM comparison; this report starts after that decision.

## 1. What we are building—and what currently works

The eventual goal is to adapt selected parts of an image to a requested cultural
context while preserving its purpose, people and important relationships.

Implemented today:

1. **SmolVLM-500M** describes an image.
2. **Qwen2.5-3B through local Ollama** drafts adaptations from that description and
   user-supplied context.
3. **Deterministic Python validation** checks the draft, quarantines unsupported
   candidates, and returns PROPOSE, REVIEW or ABSTAIN.

Grounding DINO is next. Object localization, segmentation, inpainting and a complete
image-editing transcreation pipeline are not implemented. Existing future-stage
stub files do not constitute working features.

**Central finding:** fluent captions and valid JSON are insufficient. Model
suggestions, user-verified facts and permission to modify an image must remain
separate.

## 2. Starting point: a caption is evidence, not ground truth

Selecting SmolVLM did not make its descriptions automatically correct. The earlier
VLM work showed omissions, unsupported identities, repetition and incomplete
captions. Those errors can propagate: an LLM can confidently propose changing an
object that the captioner misidentified.

We distinguish:

- **Generated claim:** the caption or planner says something appears in the scene.
- **User-verified fact:** a user supplies an object ID and original description
  after checking the image.
- **Proposed change:** something that might appear only after editing.

Completion is independent of correctness. EOS indicates that generation finished;
hitting the token ceiling without EOS can indicate truncation. Missing completion
flags map to UNKNOWN. A complete caption can still hallucinate.

## 3. Architecture and responsibilities

This is the conceptual data flow. The two CLI commands are currently separate,
not an automatically connected end-to-end workflow.

```text
image -> SmolVLM caption + completion flags + metadata
      -> PlanningInput + user cultures/instructions/verified objects
      -> Qwen via local Ollama
      -> raw JSON draft retained in audit
      -> contract parsing and deterministic validation
      -> PROPOSE / REVIEW / ABSTAIN
      -> saved policy result; no automatic image modification
```

| Component | Responsibility |
| --- | --- |
| `stages/caption.py` | SmolVLM loading, prompts, preprocessing, generation and measurements |
| `pipeline.py` | Captioning entry point, device choice and precision fallback |
| `contracts.py` | Typed inputs/results and runtime field validation |
| `stages/planning.py` | Parsing, mock planner, policy rules and candidate quarantine |
| `stages/ollama_planner.py` | HTTP adapter, system prompt, JSON schema and audit recording |
| `config.py` and `configs/` | Separate validated VLM and planner settings |
| `cli.py` | `caption` and `plan` commands and output handling |
| `scripts/evaluate_planner.py` | Reproducible real-model evaluation utility |
| `tests/` | Offline regressions, mock responses and fixed input fixtures |

SmolVLM is the only active VLM; Qwen is the only active LLM. BLIP and Florence-2
remain historical evidence, not selectable runtime alternatives.

### Technical details of the caption-to-planner handoff

The selected checkpoint is `HuggingFaceTB/SmolVLM-500M-Instruct`, pinned in
[models.yaml](../configs/models.yaml) to revision
`a7da5b986cb59b408707209984f360a5f4ad7e47`. The implementation uses the model's
native chat template, RGB images, a 1024-pixel longest-edge processor setting,
greedy generation (`num_beams: 1`, sampling disabled), a 128-token output limit,
and generation caching. Transformers is pinned to the tested `4.57.6` release.

Device selection is automatic: CUDA when available, otherwise CPU. The configured
GPU precision is float16; the CPU path falls back to float32. The adapter removes
input prompt tokens before decoding the new caption, so instructions are not
mistaken for generated content. Caption output also records the image hash,
checkpoint/settings, generated-token count, timing and completion flags.

`eos_reached: true` counts as complete, even if the token ceiling was also reached.
Without EOS, a reached ceiling is TRUNCATED; absent/unclear flags become UNKNOWN.
The planner receives that status rather than assuming every caption is finished.
These settings were retained during planner development; no VLM tuning or training
was performed to hide planner failures.

## 4. Step one: typed contracts and a mock planner

We defined the planning interface before connecting an LLM. Controlled mock
responses let us test valid proposals, truncation, uncertain identities, abstention
and malformed responses without model downloads or service availability.

**Technical approach:** frozen dataclasses represent planning records, tuples hold
planning collections, and string enums represent statuses/decisions. Type hints
alone do not validate runtime values, so parsers and constructors perform checks.
Existing modules were reused; no new validation framework was introduced.

### Planning input

| Field | Meaning |
| --- | --- |
| `source_caption` | Unverified model description |
| `caption_status` | COMPLETE, TRUNCATED or UNKNOWN |
| `target_culture` | Required desired adaptation context |
| `source_culture` | Optional user-declared original context, never invented |
| `user_instructions` | Preferences and preservation requests |
| `verified_objects` | User-checked original object IDs/descriptions |

`PlanningInput.from_caption(...)` converts a typed caption result and maps
completion flags. It does not create verified objects. A caption audit JSON is not
directly interchangeable with a planning-input JSON: target context and planning
fields must be supplied.

### Planning result

| Field | Meaning |
| --- | --- |
| `decision` | PROPOSE, REVIEW or ABSTAIN |
| `decision_reason` | Explanation of the disposition |
| `scene_summary` | Original scene only; caption-only claims remain unverified |
| `candidate_edits` | Draft modifications subject to policy checks |
| `must_preserve` | Features and relationships to keep unchanged |
| `uncertainties` | Unresolved facts material to a decision or edit |
| `verification_requirements` | Specific checks before permitting an edit |

Each candidate includes the original `object_description`, original-object
`localization_phrase`, future `proposed_change`, `cultural_reason`, an
`identity_uncertain` flag and nullable `verified_object_id`.

The mock planner returns supplied fixture data. Test food substitutions are
hypothetical examples, not production rules about cultures.

## 5. Step two: real Qwen integration through Ollama

`OllamaPlanner` uses Python's standard HTTP library and local `/api/chat`, separate
system/user messages, `stream: false`, and the existing planning-result JSON Schema.
The fixed system message defines policy; user values are serialized as data and
cannot authorize edits or invent verification. No additional Python dependency was
needed.

### Recorded model and controls

| Setting | Recorded value |
| --- | --- |
| Model | `qwen2.5:3b` |
| Reported size / compressed variant | 3.1B / `Q4_K_M` |
| Endpoint | `http://127.0.0.1:11434/api/chat` |
| Timeout | 180 seconds |
| Temperature / seed | 0 / 42 |
| Context / generated-output ceiling | 4096 / 1024 tokens |
| Keep-alive | 0, plus explicit unload requests |

Recorded installed-model digest:

```text
357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b
```

Settings live in `configs/planner.yaml`, separately from `configs/models.yaml`.
Temperature 0 and a seed aid repeatability; they do not guarantee identical results
across model digests, runtime versions or hardware. Recording the resolved digest
is more precise than recording a mutable model tag alone.

Connection failures, missing models, timeouts, interrupted HTTP, empty/incomplete
generation, malformed JSON and invalid top-level contracts have explicit errors.
An unfinished response is not accepted just because some JSON arrived.

Per-candidate failures now follow a separate explicit quarantine path: retain the
raw proposal, record issue codes and produce a non-actionable disposition where
appropriate. No edit is invented to repair a failed response.

## 6. Scenarios and provenance

We used six reproducible cases, not a representative cultural benchmark.

| Scenario | Evidence and purpose |
| --- | --- |
| Japanese meal -> India | Synthetic shared lunch with hypothetical verified ramen/source context |
| Durga Puja -> Japan | Archived concise SmolVLM caption; object identity uncertain and caption actually truncated |
| Bicycle -> India | Archived ordinary bicycle caption; tests unnecessary transformation |
| Truncated caption | Archived original Durga output, without repairing its missing ending |
| Unknown source culture | Synthetic shared meal without verified culture/objects |
| Instruction injection | Archived bicycle caption with deliberately added malicious text, not a genuine VLM continuation |

[Fixture provenance](../tests/fixtures/planning/scenarios.json) includes archive
hashes. The Durga case does not isolate uncertainty from truncation because both
occur together. Human-review notes were initially blank; no completed cultural-
expert scores or held-out accuracy estimates support generalization claims.

## 7. Experiment history: findings and changes

### Initial real run

All six raw decisions were ABSTAIN. Validation changed five to REVIEW; the bicycle
remained ABSTAIN. Responses were structured but included unsupported statements
about which objects/foods belonged in a target culture.

**Finding:** allowed decisions and valid JSON do not establish cultural reasoning.
We clarified that scene purpose can remain while an ordinary object changes, and
that contextual adaptation is not a universal national rule.

### Prompt iteration 2

The model began proposing a food change, but described the replacement dish as the
original object. Scene summaries sometimes described the imagined edited scene.
The bicycle gained irrelevant national-style uncertainty and became REVIEW.

**Finding:** source/future field confusion and indiscriminate uncertainty handling
were separate problems. Instructions were revised to retain original-object IDs,
source descriptions and localization phrases.

### Prompt iteration 3

Food, Durga and truncation still required review. Unknown-source input abstained.
The injection case returned ABSTAIN together with candidate edits and was rejected.

**Finding:** cross-field contradictions can survive structured generation. Rejection
showed a functioning boundary, not complete prompt-injection immunity. Unsupported
cultural statements remained.

### Three CLI examples and consistency review

A repeated food/Durga/bicycle CLI run ended in REVIEW for all three. Food still mixed
source and future details. The bicycle selected raw ABSTAIN but unnecessary doubt
triggered review.

We clarified field meanings and separated safe no-change behavior from permission
to edit. Keyword-based uncertainty/instruction classification was removed; proposed
edits remained conservative, while unrelated doubts need not block no change.

The first revised prompt still produced malformed field content and all-REVIEW
results. That unsuccessful attempt was preserved. The final consistency run exposed:

- Food abstention for the wrong reason that the original meal already belonged to
  Japan, rather than evaluating India as the target.
- Durga REVIEW containing a deity-restyling candidate, a quoted `"null"` object
  description, and full-scene localization.
- Bicycle ABSTAIN containing invented graffiti-related cultural checks.

**Finding:** REVIEW was only a warning label; unsafe candidates could still survive
in the final array. ABSTAIN could also retain unsupported cultural restrictions.

### Decision-policy correction

We traced input, prompt, generation, contract and postprocessing causes before
editing. Deterministic quarantine, coded issues and clean abstention became the
central fixes. A real rerun exposed raw PROPOSE with no candidate; a regression and
general no-action rule were added. The failure remained saved, and offline tests
passed before the final rerun.

## 8. Root causes: not everything was an LLM failure

| Failure | Prompt/generation contribution | Application contribution |
| --- | --- | --- |
| Food source/target confusion | Input was correct; prompt distinction was weak and Qwen used source membership to reject adaptation. | Shape validation could not assess rationale; postprocessing accepted it without a contextual review boundary. |
| Protected Durga restyling | Input explicitly protected worship/idol/people/relationships; Qwen violated it. | REVIEW did not remove the candidate. |
| Quoted null and paragraph localization | Qwen generated both values. The observed verified ID was already proper JSON null. | Nonempty-string checks accepted placeholders/paragraphs; warnings did not quarantine them. |
| Irrelevant bicycle checks | Input requested an ordinary unchanged scene; Qwen invented restrictions. | Postprocessing copied those checks/reasons into ABSTAIN. |

The quoted null problem was not Python None being incorrectly serialized into a
string. The literal quoted value already existed in Qwen's output.

## 9. Final validation design

### Original context, desired context and object identity

Source culture describes origin, not an automatic reason to forbid adaptation.
Target culture describes intent, not an automatic reason to force one. Original
objects must stay distinct from future replacements.

A known-source, verified-object adaptation request with opaque instructions can
receive `ABSTENTION_CONTEXT_UNVERIFIED`. This conservatively asks for review; it
does not prove a rationale wrong or require changing an object merely because
cultures differ.

### Runtime validation beyond JSON shape

Python reconstructs typed records and checks fields/cross-field rules after the
server receives the JSON Schema. Unknown/missing fields and malformed top-level
data still fail. Object descriptions reject empty values and placeholders.

Actual JSON `null` maps to Python `None`; `"null"` is literal text and is not a
valid nullable ID. A missing verified ID does not establish a safe source identity.
IDs must exist in the supplied input and match the original description.

Localization must retain the source label and is limited to 16 words/160 characters.
This is an output-format/reference constraint, not proof of single-object grounding.
Checks also cover identity uncertainty, identical source/replacement wording,
detectable future-scene contamination and preservation overlap.

### Quarantine, not warnings alone

Invalid/materially unsupported candidates remain in the raw audit but not in final
`candidate_edits`. **Every final REVIEW releases zero candidates.** A batch requiring
review is withheld as a whole rather than exposing partially checked edits.

Previously Durga's raw and final decisions were both REVIEW while an unsafe edit
survived. Decision labels alone therefore do not prove safety; candidate contents,
counts and issue codes must be inspected.

### Protected constraints and uncertainty

User instructions remain free text, not a machine-verified permission/protection
list. Pending edits with unresolved instructions receive
`USER_CONSTRAINTS_UNRESOLVED`. This avoids cultural keyword bans but also blocks
some valid preference-only requests. Human compatibility checks remain necessary.

The current string-only uncertainty field cannot reliably classify every material
ambiguity. Proposed edits stay conservative; unrelated descriptive uncertainty need
not block a no-action choice. Removing user constraints to obtain PROPOSE would
defeat the intended protection boundary.

### No change is not approval

Final ABSTAIN has no candidates, no edit-verification checklist and a neutral
policy reason. It does not certify cultural appropriateness or image truth. Raw
invented restrictions are retained for review, not endorsed as final explanations.

`PROPOSE_WITHOUT_EDITS` records an internally inconsistent empty proposal. It can
resolve only to no action, never an invented candidate. Truncation, prior rejection
or unresolved context can still force REVIEW. Even a retained PROPOSE is conditional;
an end-to-end human-approval-to-image-execution workflow does not yet exist.

## 10. Actual final three-scenario evaluation

Inputs, effective generation settings and installed-model digest matched prior
runs. This is the latest policy evaluation, not an average across prompt versions.

| Scenario | Raw -> final | Final candidates | Request / generation seconds | Input / output tokens |
| --- | --- | ---: | ---: | ---: |
| Japanese meal -> India | PROPOSE -> REVIEW | 0 | 6.07 / 3.55 | 714 / 242 |
| Durga Puja -> Japan | REVIEW -> REVIEW | 0 | 9.03 / 5.88 | 819 / 432 |
| Bicycle -> India | PROPOSE -> ABSTAIN | 0 | 6.95 / 3.94 | 733 / 288 |

Request time includes lookup/loading and response handling. Generation time is
Ollama's `eval_duration` converted from nanoseconds, excluding loading/prompt
processing. These are individual observations, not a statistical speed benchmark.

**Food:** Qwen considered an Indian replacement but mislabeled it as the verified
original and repeated it as its own replacement. `meal-1` actually described ramen.
`SOURCE_OBJECT_MISMATCH`, `SOURCE_REPLACEMENT_IDENTICAL` and
`USER_CONSTRAINTS_UNRESOLVED` removed the candidate. Final REVIEW explains code-level
blockers; no grounded, culturally correct adaptation was demonstrated.

**Durga:** the latest raw response already contains no candidates.
`CAPTION_INCOMPLETE` and `MODEL_REVIEW_REQUESTED` keep REVIEW. Its scene/cultural
prose remains unverified. Replaying the previous unsafe draft removed its candidate
with placeholder, localization, batch-review, truncation and protection issue codes.
That saved replay is explicitly distinguished from new inference.

**Bicycle:** raw PROPOSE had no edit. The policy recorded `PROPOSE_WITHOUT_EDITS` and
`ABSTENTION_NORMALIZED`, returning clean ABSTAIN. Its raw-schema-valid flag is false
despite a valid final no-action contract. This is explicit recovery, not a claim that
Qwen answered correctly.

### Audit record: what is raw and what is final?

| Field | Meaning |
| --- | --- |
| `input`, `request` | Input, exact system/user messages, schema and options |
| `resolved_model` | Installed identity, digest and metadata |
| `response` | Full Ollama response, original text and available timing/tokens |
| `raw_planning_result` | Decoded original proposal, not silently repaired wording |
| `planning_result` | Final typed policy disposition |
| `validation.issues` | Codes, severity and candidate indices |
| `validation.rejected_candidates` | Rejected raw proposals and codes |
| `validation.raw_schema_valid` | Raw validity, separate from final validity |
| `validation.automatically_authorized` | Always false, including for conditional proposals |
| `human_review_notes` | Initially blank, not an invented expert score |

## 11. Testing and reproducibility

We separated software correctness from cultural quality. Mock HTTP/model responses
test failures, dangerous drafts and valid conditional proposals without model
downloads or service availability. They do not measure cultural accuracy.

| Recorded milestone | Passing offline tests | Main expansion |
| --- | ---: | --- |
| First real Ollama integration | 41 | Captioning, mock contracts and HTTP adapter |
| Consistency review | 53 | Source/future, localization, preservation and uncertainty |
| Final decision-policy milestone | 72 | Placeholder/null handling, quarantine, protection and no-action rules |
| Cleanup | 72 before and 72 after | Existing behavior preserved; no feature changes |

The policy milestone recorded 53 baseline tests in 0.338 seconds and 72 after-change
tests in 0.233 seconds, passing before final inference. Cleanup recorded 72 in
0.475 seconds before and 0.252 seconds after. Time variation is not an optimization
claim.

Cleanup also matched 33 complete saved-response audit replays, including full mocked
HTTP requests, schema, prompts, configurations, decisions, issue codes and quarantine.
Time/timestamps were fixed inside that verifier for deterministic comparison. Six
input fixtures matched. These were offline replays, not 33 new LLM runs.

Reproducibility means retaining failed iterations as well as successes: exact
inputs, hashes, model identifiers, prompts, settings, raw/final output and measurements.
Seed/temperature controls complement those records; they do not replace them.

## 12. Hardware and execution observations

Recorded experiments used a 4 GiB NVIDIA GeForce RTX 3050 Laptop GPU. A standalone
Qwen structured-output probe passed before cultural cases. SmolVLM was not kept
resident with Qwen during those evaluations.

Earlier six-scenario observations:

- Largest sampled Qwen allocation from `/api/ps`: 2,163,568,803 bytes, about 2.01 GiB.
- Largest sampled total GPU usage: 3597 MiB out of 4096 MiB.
- Baseline/final global usage: 1438 MiB; final `/api/ps` listed no loaded model.

Global readings include desktop/other applications. Sampling can miss peaks; Ollama
allocation is not PyTorch tensor peak memory or process RSS. Concurrent residency
was not tested, so these numbers do not prove both models fit together.

The implementation uses separate stages, `keep_alive: 0`, and explicit cleanup for
recorded planner runs. Unload failures are recorded. An unload request is separate
from observed memory release; a timeout does not become a successful plan.

## 13. Cleanup after validation

The cleanup inspected the actual checkout rather than assuming the historical
72-test count. It found a clean Git baseline and 72 passing tests.

Only small refactors were made: reuse existing label normalization, remove a
duplicate timeout alias check (`socket.timeout is TimeoutError` on tested Python
3.11), remove one unused test import, correct docstrings, and simplify documentation.

No model prompt, checkpoint, preprocessing, setting, validation rule, schema field
or candidate policy changed during cleanup. Seven tracked files changed; no files
were moved/deleted. 352 pre-existing files outside authorized edits stayed byte-identical.

65 duplicate-content groups were retained: the same caption/input can belong to
trials with different provenance. Compatibility-sensitive diagnostics and existing
future-stage stubs were flagged rather than deleted.

The cleanup recorded two operational debts:

1. Installed `transcreate.exe` still referenced retired `main:main`, while project
   configuration correctly declared `transcreation.cli:main`. Source commands worked.
   Cleanup did not reinstall the environment; this report did not recheck that launcher.
2. `.local_archive/` is Git-ignored, no independent backup was verified, and 35 old
   archive image references were broken. Historical evidence was preserved rather
   than silently rewritten.

## 14. How to run and understand the current commands

Use Python 3.11 from the project root. Explicit source invocation avoids an old
generated launcher:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli caption --image data/sample_images/durga.jpg --out outputs/caption_example.json
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/planner_example.json
```

The second command uses an existing fixture; it does not automatically consume the
first output. For a new image, prepare planning input with caption/status and user
context. After normal editable installation (`python -m pip install -e .` using
the intended environment), `transcreate caption ...` and `transcreate plan ...` are
configured equivalents. Planner output names must be new.

Offline regressions and optional intentional real evaluation:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B scripts/evaluate_planner.py --out reports/fresh_planner_evaluation
```

None of these commands were executed to prepare this report. See the
[project README](../README.md) for installation and usage.

## 15. Interview guide

### A 60-second explanation

> We are building a culture-aware image transcreation prototype. After selecting
> SmolVLM-500M for captioning, we integrated local Qwen2.5-3B through Ollama. We first
> defined typed contracts and tested them with mocks. Real experiments exposed
> source/target confusion, imagined future scenes, invalid references, protected-
> content edits and unnecessary checks. A major application bug was that REVIEW
> still retained unsafe candidates. We fixed that with deterministic validation,
> quarantine and raw/final audit separation. The policy milestone had 72 passing
> offline tests, and cleanup preserved 33 full audit replays. Grounding and image
> editing are not implemented, and cultural accuracy is not solved.

### Questions and defensible answers

**Why two models?** The VLM describes an image; the LLM reasons over text and supplied
context. This separates responsibilities but introduces error propagation, so a
caption remains unverified.

**Why SmolVLM?** Earlier experiments showed useful coverage of some cultural details
with hallucination/truncation limitations. It was a practical project choice, not
proof of universal superiority; cite the separate VLM report.

**Why Qwen2.5-3B?** It was the selected local LLM for a constrained setup. We did not
compare multiple LLMs or prove this model is the best cultural planner.

**What does structured output solve?** Expected machine-readable shape. It does not
prove visual truth, appropriate cultural reasoning or cross-field consistency.

**What was the most important bug?** REVIEW retained dangerous final candidates.
The corrected boundary keeps rejected drafts only in the audit, not downstream edits.

**Why JSON null versus string null?** Actual null maps to Python None. The quoted
string is literal text. The observed bad description was generated by Qwen, not
caused by a None-to-string serializer.

**Does a verified ID establish a safe edit?** No. It only references a user-checked
original object. It does not verify its replacement, cultural reason, localization
or preservation compatibility.

**Why not only improve the prompt?** Revisions sometimes helped one case and harmed
another. Stable invariants, such as zero final candidates for REVIEW, belong in code.

**How are protected constraints handled?** Their original text is retained and
pending edits conservatively require compatibility review. No claim is made that
text matching understands every protected practice or relationship.

**Do 72 tests prove cultural accuracy?** No. They prove specified software behavior
under mocks/fixtures, not representative accuracy or expert cultural agreement.

**How is research reproducible?** Exact input, identifiers/digests, prompts, settings,
hashes, raw/final results, issues and measurements remain saved, including failed runs.

**What remains?** Grounding DINO next, eventually segmentation/inpainting. No complete
image-editing or human-approval-to-execution workflow is currently working.

**Avoid claiming:** model training, a cultural-accuracy percentage, solved injection,
universally valid substitutions, proved concurrent 4 GiB capacity, or completed
image editing. A policy rejection is not a successful generated adaptation.

## 16. Remaining limitations and terms

- Source/future confusion, invented cultural facts and unsupported identities remain
  model limitations. REVIEW summaries must not become grounding truth automatically.
- Length/label checks do not prove visual localization or arbitrary semantic consistency.
- Conservative free-text constraints can over-review valid requests. No reliable
  materiality classifier or complete injection detector is implemented.
- No-action normalization improves disposition, not model reasoning; its effect is
  coded explicitly and raw answers are retained.
- Six convenience scenarios, synthetic verification and combined uncertainty/
  truncation do not establish general cultural performance.
- Archive backup and old paths remain operational issues. Future stages and full
  image transformation are unimplemented; no decision automatically permits editing.

| Technical term | Meaning here |
| --- | --- |
| Inference | Running pretrained weights, not training them |
| Checkpoint/revision/digest | Model identifiers used to record what actually ran |
| Quantization | Compressed numerical representation of weights; this project used a pre-quantized Q4_K_M artifact, not a custom quantization/training procedure |
| Token / EOS / ceiling | Model text unit / finish marker / output limit |
| JSON Schema | Output shape, not proof of meaning |
| Typed contract | Python representation plus runtime checks |
| Deterministic validator | Explicit code rules, not another LLM |
| Localization phrase | Text identifying an original object for future grounding |
| Grounding / segmentation / inpainting | Future object location / pixel mask / region editing |
| Quarantine | Retain rejected drafts for review, remove them from final candidates |
| Mock / audit | Controlled test response / preserved input-response-validation record |

## 17. Evidence map

This report merges the explanation, not the evidence files. Earlier reports describe
the policy at their time, not necessarily the latest behavior.

| Stage | Primary saved evidence |
| --- | --- |
| VLM starting point | [Selection findings](VLM_Selection_Experimental_Findings_Refined.md) |
| Initial Ollama run | [Six-case summary](ollama_planner_phase3_20261108/summary.json) |
| Prompt iteration 2 | [Summary](ollama_planner_phase3_20261108_prompt_v2/summary.json) |
| Prompt iteration 3 | [Report](ollama_planner_phase3_20261108_prompt_v3/REPORT.md) |
| Three CLI examples | [Report](phase3_step2_three_examples_20261108/REPORT.md) |
| Initial consistency revision | [Comparison](planner_quality_review_20261108/comparison.json) |
| Final consistency revision | [Report](planner_quality_review_20261108_final/REPORT.md) |
| First policy run, including failure | [Comparison](planner_decision_policy_20261108/comparison.json) |
| Final policy correction | [Report](planner_decision_policy_20261108_final/REPORT.md), [root causes](planner_decision_policy_20261108_final/root_cause_analysis.json), [old-response replays](planner_decision_policy_20261108_final/previous_raw_revalidated.json) |
| Complete three-case review package | [Inputs, raw outputs and final plans](../outputs/planner_review.md) |
| Cleanup and equivalence checks | [Cleanup report](repository_cleanup_review.md), [offline verifier](repository_cleanup_20261108/compatibility_check.py) |

### Latest original inputs, raw model outputs and final JSON

| Case | Input | Raw output | Final plan | Full audit |
| --- | --- | --- | --- | --- |
| Food | [JSON](planner_decision_policy_20261108_final/01_japanese_food.input.json) | [JSON](planner_decision_policy_20261108_final/01_japanese_food.raw.json) | [JSON](planner_decision_policy_20261108_final/01_japanese_food.plan.json) | [JSON](planner_decision_policy_20261108_final/01_japanese_food.audit.json) |
| Durga | [JSON](planner_decision_policy_20261108_final/02_durga_uncertain_incense.input.json) | [JSON](planner_decision_policy_20261108_final/02_durga_uncertain_incense.raw.json) | [JSON](planner_decision_policy_20261108_final/02_durga_uncertain_incense.plan.json) | [JSON](planner_decision_policy_20261108_final/02_durga_uncertain_incense.audit.json) |
| Bicycle | [JSON](planner_decision_policy_20261108_final/03_bicycle_no_change.input.json) | [JSON](planner_decision_policy_20261108_final/03_bicycle_no_change.raw.json) | [JSON](planner_decision_policy_20261108_final/03_bicycle_no_change.plan.json) | [JSON](planner_decision_policy_20261108_final/03_bicycle_no_change.audit.json) |

Each audit retains exact messages, options, full response and validation issues.
Original evidence remains unchanged. This consolidation does not turn recorded
failures into successful cultural adaptations.
