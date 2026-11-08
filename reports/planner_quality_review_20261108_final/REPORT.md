# Planner consistency and no-change safety review

This update clarifies existing fields and improves deterministic checks without adding contract fields, dependencies, models, or image-editing stages. The real model remains unreliable in several ways described below. Improvements are not a claim of semantic or cultural correctness.

## What changed

- Contract docstrings distinguish original scene/object/localization, intended replacement, unchanged features, material uncertainties, and specific verification checks. Field names and serialized types are unchanged.
- The system prompt uses the same distinctions, asks for attribution of caption-only details and retained qualifiers, treats adaptations as contextual suggestions, and explicitly separates keeping an image unchanged from approving an edit.
- Source-object ids still have to match the user-supplied description exactly. A model cannot verify its own invented/replacement object.
- Localization must retain the original source label. Case/punctuation are ignored, but synonyms are not guessed. Missing the label causes REVIEW, not a claim that a phrase is semantically impossible.
- If an intended-change phrase appears in scene_summary but not in supplied source text, the result requires review. This is only a detectable exact-phrase inconsistency; image omissions and paraphrases remain human checks.
- Preservation statements mentioning the edited source label or intended replacement are flagged as potential conflicts. Even a legitimate position-only statement may require human clarification; the code does not pretend to infer identity-versus-feature semantics.
- Caption uncertainty-word scanning and the instruction keyword blacklist were removed. Trust comes from system/data separation, strict schema validation, supplied verified-object references, and no automatic modification authorization, not a promise to recognize every injection.
- COMPLETE no-edit ABSTAIN can retain unrelated uncertainty, with an explicit note that no image change is authorized. TRUNCATED/UNKNOWN still requires REVIEW; explicit model REVIEW is not promoted.
- With actual edits pending, unresolved relevance of free-text uncertainty remains conservative REVIEW. The unchanged string-only uncertainty field cannot reliably classify arbitrary materiality. This limitation is explicit rather than hidden behind a cultural/keyword rule.
- The raw model message is never rewritten. Final results only add deterministic review/check requirements and baseline preservation obligations; every model-generated wording remains archived.

## Fixed experimental controls

Model: `qwen2.5:3b`, 3.1B, Q4_K_M.
Digest: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
The three inputs, source/target cultures, user instructions, verified-object records, model digest/quantization and all generation settings were checked against the previous run: temperature 0, seed 42, context 4096, output ceiling 1024, keep_alive 0. Only instructions/schema descriptions and deterministic validation changed. These are single observations, not statistical performance estimates.

## Before / after

The before column uses reports/phase3_step2_three_examples_20261108. Raw and final decisions are listed separately; no old result was overwritten.

| case | before raw / final | after raw / final | generation seconds before / after | prompt tokens before / after | output tokens before / after |
| --- | --- | --- | ---: | ---: | ---: |
| [01_japanese_food](01_japanese_food.plan.json) | PROPOSE / REVIEW | ABSTAIN / ABSTAIN | 4.16 / 1.82 | 823 / 678 | 277 / 125 |
| [02_durga_uncertain_incense](02_durga_uncertain_incense.plan.json) | ABSTAIN / REVIEW | REVIEW / REVIEW | 4.45 / 7.35 | 928 / 783 | 329 / 529 |
| [03_bicycle_no_change](03_bicycle_no_change.plan.json) | ABSTAIN / REVIEW | ABSTAIN / ABSTAIN | 3.12 / 2.77 | 842 / 697 | 217 / 198 |

Request times including loading were 7.22 -> 4.31 seconds (food), 7.55 -> 10.42 seconds (Durga), and 6.17 -> 5.79 seconds (bicycle). Raw Ollama load/prompt/generation timing is preserved in each audit. No inference speedup claim is made from three single runs.

### 01_japanese_food

- original scene: before: Summary incorrectly described a bowl of dal already present instead of the verified original ramen. after: Summary refers to the original ramen meal and attributes it to the caption; no imagined replacement is described.
- localization: before: bowl of dal names the future object, not the original ramen. after: Not applicable: no candidate edit. This does not demonstrate successful localization generation.
- preservation: before: Preserves the whole original bowl of ramen while proposing to replace it, a detectable potential conflict. after: No candidate edits or preservation list, so the previous conflict is absent because the model abstained.
- uncertainty: before: Treats its own proposed substitution as an uncertainty. after: No reported uncertainties.
- remaining issue: The abstention reason focuses on the Japanese source and does not substantively address the Indian target; a potentially useful adaptation was lost, not demonstrated to be inappropriate.

### 02_durga_uncertain_incense

- original scene: before: Original scene mostly retained, but tentative incense identity restated as fact. after: Starts with caption attribution and retains objects resembling incense sticks and likely offerings. These remain unverified caption claims.
- localization: before: Not applicable: no candidate edits. after: Incorrect: source description is the literal string null and localization is a long copied paragraph. Source-reference checks flag both.
- preservation: before: No edits, so no edit/preserve conflict to assess. after: No reliable source label to compare. Changing sacred headdress/jewelry for national styling may conflict with religious meaning even if position and crowd remain; this requires human judgment and is not automatically proven consistent.
- uncertainty: before: Uncertain incense identity plus broad cultural-context doubts. after: Unresolved source identity and religious/contextual significance; review remains conservative.
- remaining issue: Despite the prompt, the model suggests culturally inappropriate national restyling of sacred objects. The draft is not approved; unresolved identity, broken localization and truncation all require review.

### 03_bicycle_no_change

- original scene: before: Description remains about the original bicycle scene. after: Copies the original caption rather than describing a changed scene, but does not explicitly attribute it to the caption.
- localization: before: Not applicable: no edits. after: Not applicable: no edits.
- preservation: before: No edits, so no contradiction. after: No edits, so no contradiction.
- uncertainty: before: Irrelevant speculation about national graffiti styles forced final REVIEW. after: uncertainties is empty and ABSTAIN remains ABSTAIN. However, verification_requirements still include irrelevant national-norm checks.
- remaining issue: Qwen still calls graffiti culturally sensitive and invents target-country verification needs. No-change safety improved; cultural reasoning and attribution are not fully fixed.

Accuracy above means consistency with the provided textual source and user assertions, not independently verified image accuracy. The food case is a synthetic user-verified fixture, and the archived Durga caption is both uncertain and truncated. No scene-summary correctness, cultural suitability or grounding accuracy score is inferred.

## Tests and verification

- 53 offline tests passed in 0.335 seconds: 12 added tests plus the existing adapter/contract/captioning suite. Transport/malformed-JSON/schema tests remain mocked and all 11 SmolVLM regressions passed.
- New tests cover original/replacement identity, future-object localization, future-scene contamination, preservation overlap (including ambiguous legitimate feature preservation), harmless no-edit uncertainty, material edit uncertainty, no keyword classification, verified original references, empty ABSTAIN and explicit human checks for paraphrases.
- All three real CLI invocations passed structural validation. Structural validity is not semantic approval.
- Current validation replayed over the archived final raw responses exactly reproduces the saved final plans. Exact input, system/user messages, schema, metadata/digest and raw responses are in the audit JSON files.
- SHA-256 checks confirmed 263 pre-existing evidence/fixture/VLM/settings files unchanged. The prior results and initial unsuccessful revised-prompt run remain intact.
- Qwen was unloaded after each request; final /api/ps has no loaded model. SmolVLM was not loaded or modified.
- No commit or push.

## Artifacts and task diff

- `*.plan.json`: final typed plans; `*.audit.json`: exact original responses plus final review notes and metadata.
- `comparison.json`: raw/final decisions, timings, token counts, input hashes, surface-reference diagnostics.
- `qualitative_comparison.json`: textual consistency observations and remaining model failures; these are engineering observations, not completed cultural-expert review notes.
- `test_results.json`, `task_changes.diff` and `task_diff_summary.json`: actual tests and the diff relative to the start of this request (separate from earlier uncommitted work).
- [initial revised prompt run](../planner_quality_review_20261108/comparison.json): retained despite malformed field content and all-REVIEW output; it was not substituted for the final run.

## Reproduce

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/new_food_review.json
```

Use fresh output filenames and substitute the other two fixture names. The planner never authorizes or performs image modification. Arbitrary semantic contradictions, misleading cultural explanations, relevance of free-text uncertainties during an edit, and future-object paraphrases still require human/visual checking.
