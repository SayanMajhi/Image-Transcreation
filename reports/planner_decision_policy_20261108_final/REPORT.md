# Decision policy, candidate quarantine, and regression verification

The milestone fixes validation and downstream decision behavior; it does not establish model-level cultural correctness. The original fixtures, all previous evidence, qwen2.5:3b quantization, and generation settings are unchanged.

## Diagnosis before code changes

Each failure was traced through the exact original input, archived system/user prompts, raw model response and final postprocessing in reports/planner_quality_review_20261108_final. See root_cause_analysis.json for the layer-by-layer analysis.

1. Food input was correct. The prompt under-specified source-versus-target reasoning; Qwen generated the confused source-membership rationale; structural validation could not verify that rationale; postprocessing accepted it unchanged.
2. Durga input explicitly marked truncation and protected worship, idol, people and relationships. Qwen violated preservation instructions, but the application also failed: setting REVIEW did not remove the unsafe candidate from the final list.
3. The quoted null description and full-scene localization came directly from Qwen. The observed verified_object_id was already proper JSON null. The contract accepted nonempty placeholder strings/paragraphs, and postprocessing only added warnings.
4. Bicycle input requested an ordinary unchanged scene. Qwen invented cultural checks. Postprocessing unnecessarily retained those checks and the unsupported cultural reason in the final ABSTAIN.

## Code changes

- contracts.py: object fields reject empty/placeholder values; nullable candidate ids accept actual null but reject placeholder strings. Localization is limited to 16 words / 160 characters as a short-output format rule, not proof that a phrase identifies exactly one visible object.
- planning.py: strict parsing remains available; model-draft parsing explicitly quarantines invalid candidates and records codes. Missing/malformed top-level fields and invalid JSON still fail. No candidate text or id is invented to repair a proposal.
- Final REVIEW always has candidate_edits empty. All invalid, unsupported or review-only proposals remain available only in the raw audit/rejected_candidates. Source ids must exist and match the supplied original descriptions; identical source/replacement wording is flagged.
- User instructions are free text in the unchanged contract. With a pending edit, compatibility with all user-defined protections is unresolved until human review; USER_CONSTRAINTS_UNRESOLVED blocks release. This deliberately blocks some valid preference-only instructions rather than pretending to parse protected entities or permissions with cultural keywords.
- A known-source, verified-object adaptation request with opaque user instructions cannot have its no-edit cultural justification automatically endorsed. ABSTENTION_CONTEXT_UNVERIFIED requires review; it does not require or generate an edit just because cultures differ. It can conservatively flag a legitimate abstention.
- Ordinary ABSTAIN is an explicit no-action disposition with a neutral reason and no verification checklist. Generated cultural statements/checks are retained raw, not promoted to validated reasons.
- A raw PROPOSE with no actual candidates is structurally inconsistent. PROPOSE_WITHOUT_EDITS records this fact and can resolve only to no-action ABSTAIN; incomplete captions, prior rejected candidates and unresolved adaptation context still force REVIEW. No successful edit is synthesized.
- ollama_planner.py: exact raw JSON/text and raw_planning_result are kept separately from planning_result. validation records issue codes/severity/candidate index, rejected raw candidates, raw_schema_valid, raw/final decisions, and automatically_authorized=false.
- Existing CLI and serialized planning input/result field names are preserved. Contracts are stricter about invalid values; final REVIEW no longer exposes draft candidates, and final ABSTAIN reason/check normalization is a documented behavior change.

## Actual real evaluation

Model: `qwen2.5:3b`, 3.1B, Q4_K_M, digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Temperature 0, seed 42, context 4096, output ceiling 1024, keep_alive 0. The runner asserted identical input contents, effective generation options and model digest against the previous evidence.

| case | previous raw / final | new raw / final | previous / new final candidates | new generation seconds | new prompt / output tokens |
| --- | --- | --- | ---: | ---: | ---: |
| [01_japanese_food](01_japanese_food.plan.json) | ABSTAIN / ABSTAIN | PROPOSE / REVIEW | 0 / 0 | 3.55 | 714 / 242 |
| [02_durga_uncertain_incense](02_durga_uncertain_incense.plan.json) | REVIEW / REVIEW | REVIEW / REVIEW | 1 / 0 | 5.88 | 819 / 432 |
| [03_bicycle_no_change](03_bicycle_no_change.plan.json) | ABSTAIN / ABSTAIN | PROPOSE / ABSTAIN | 0 / 0 | 3.94 | 733 / 288 |

All three final CLI invocations exited 0 with safe policy results. This means the final contract is valid, not that the raw model output was correct. The bicycle raw_schema_valid is false because it chose PROPOSE while providing no candidates; the coded final disposition is no-action ABSTAIN.

Food: the revised prompt made Qwen consider the target context, but it mislabeled the replacement as the original verified object and made source/replacement identical. SOURCE_OBJECT_MISMATCH, SOURCE_REPLACEMENT_IDENTICAL and USER_CONSTRAINTS_UNRESOLVED remove its candidate. The final REVIEW reason is the deterministic explanation, not the confused raw cultural assertion. No source-grounded edit is yet validated.
Durga: this new response already contains no candidates. CAPTION_INCOMPLETE and MODEL_REVIEW_REQUESTED keep REVIEW. Its scene summary and cultural reasoning remain unverified model prose; no religious transformation proceeds downstream.
Bicycle: Qwen chose PROPOSE but supplied no candidate and described keeping the scene unchanged. The general no-edit policy records PROPOSE_WITHOUT_EDITS and ABSTENTION_NORMALIZED. Final ABSTAIN has no checks or invented cultural restriction; this does not certify scene/cultural truth.

Request times including loading/lookup were 6.07s, 9.03s and 6.95s. Generation-only times come from Ollama eval_duration; all raw loading/prompt/token measurements remain in the audit. These are individual observations, not a performance benchmark.

## The previous unsafe drafts were also replayed

- Previous food source-membership abstention -> REVIEW with ABSTENTION_CONTEXT_UNVERIFIED, no candidates.
- Previous Durga invalid candidate -> REVIEW, zero candidates, with PLACEHOLDER_OBJECT_FIELD, LOCALIZATION_NOT_OBJECT_PHRASE, BATCH_REVIEW_REQUIRED, CAPTION_INCOMPLETE and USER_CONSTRAINTS_UNRESOLVED.
- Previous bicycle culturally restricted abstention -> ABSTAIN with empty verification requirements and neutral policy reason; original cultural claims remain in the unchanged old audit.
- previous_raw_revalidated.json is explicitly an offline replay of old raw responses under the new policy, not a new LLM inference. Old files were not modified.

## Tests before real inference

- Baseline: 53 offline tests passed in 0.338s.
- Final: 72 offline tests passed in 0.233s, before the final real runs; 19 new tests cover policy and audit regressions.
- Coverage: source/target context, placeholder fields, actual null versus string null, long localization, unknown and mismatched source ids, identical source/replacement, protected objects and unresolved protection paraphrases, truncated candidates, valid verified source-localized drafts, clean abstention, rejected batches, raw audit preservation, empty PROPOSE decisions, JSON/schema/transport/timeout failures, and all existing SmolVLM regressions.
- An initial real rerun exposed the empty-PROPOSE bicycle case. Its error audit is preserved under ../planner_decision_policy_20261108. A general no-action regression was added and all tests passed before repeating the three examples. No failed output was rewritten into success.

## Files and compatibility

- Each *.input.json is an exact byte copy of the existing fixture.
- Each *.raw.json is the exact model content string, including generated wording. The audit also stores that original string and the full Ollama response.
- Each *.plan.json contains the final policy result, with raw/final differences explicitly recorded in *.audit.json.
- comparison.json contains measurements, codes and decision changes; root_cause_analysis.json separates input/prompt/generation/contract/postprocessing causes.
- task_changes.diff and task_diff_summary.json describe this request relative to its starting state, separately from earlier uncommitted planner changes.
- Downstream consumers must treat REVIEW and ABSTAIN as non-actionable and use raw/rejected_candidates only for review. Even a retained PROPOSE remains an unapproved draft.

## Remaining limitations

Text validation does not prove visual identity, localization, cultural correctness, protected-content compatibility, or arbitrary paraphrased contradictions. A short phrase can still be wrong or mention multiple objects. Free-text instructions are deliberately conservative: all pending edits with unresolved user constraints require human review, including some legitimate edits. Known-source verified no-edit adaptation requests can also be over-reviewed. Do not delete user constraints to force a proposal through.

Final scene_summary and must_preserve can retain inaccurate model wording in a REVIEW result; they are unverified claims, not grounding truth. The original-scene/future-scene confusion and source-object hallucination are not fully solved in Qwen. The fixed guarantee is that unsupported drafts do not remain in the downstream candidate list.

The change does not add another LLM, dependencies, grounding, segmentation, diffusion, or image editing. SmolVLM and its configuration are unchanged. All previous research is preserved, and no commit/push occurred. Qwen used sequential requests with explicit unloading; final /api/ps has no loaded models.

## Reproduce

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/new_policy_food.json
```

Use fresh output names and substitute the other two fixture names. Run offline regressions with python -B -m unittest discover -s tests -v.
