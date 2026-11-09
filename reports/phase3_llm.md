# Phase 3: Cultural planning and validation

## Objective
Turn an unverified caption and explicit target culture into a conditional adaptation draft, while preventing unsupported edits from reaching downstream stages.

## Models and tools
`qwen2.5:3b` through Ollama `/api/chat`, structured JSON, `stream=false`, temperature 0, seed 42, context 4096, output ceiling 1024 and timeout 180 seconds. Recorded quantization: Q4_K_M, 3.1B parameters. Recorded digest: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`. Sequential execution and `keep_alive: 0` avoid assuming simultaneous GPU residency.

## Implementation summary
Typed contracts separate caption claims, optional source culture, required target culture, user instructions and verified object information. `ollama_planner.py` handles HTTP, parsing, errors and audit records. `planning.py` validates candidates against the input and records issue codes. Source descriptions/localization refer to the original object; proposed changes refer to a future replacement.

PROPOSE is a draft, not approval. REVIEW quarantines candidates and releases an empty final candidate list. ABSTAIN means no change and carries no edit-verification requirements. Raw responses and rejected candidates remain in the audit.

## Experimental setup
Six fixtures tested Japanese food → India, uncertain/truncated Durga Puja → Japan, ordinary bicycle → India, another truncated caption, unknown source culture and injected instructions. The meal/verified ramen is a hypothetical fixture assertion, not a newly human-verified photograph. Archived captions supply the Durga and bicycle examples.

## Important experiments
Initial six-scenario output was all raw ABSTAIN; validation retained bicycle ABSTAIN and escalated five to REVIEW. Prompt revisions improved some proposals but confused source objects with replacements and introduced unrelated cultural doubts. One injection response combined ABSTAIN with edits and was rejected.

Three CLI examples initially all ended in REVIEW. A later consistency revision exposed application weaknesses as well as model errors: string `"null"` passed a nonempty-text check; whole-scene localization passed; REVIEW still retained a deity-headdress/jewelry proposal; bicycle inherited irrelevant graffiti checks.

Corrections added placeholder validation, original-object consistency checks, user-constraint review, no-action normalization and candidate quarantine. No culture-specific replacement rules were added.

## Actual final decision-policy results
The following table is extracted from the preserved final comparison, not a new inference run:

| Scenario | Earlier raw/final | Final raw → validated | Generation seconds | Prompt/output tokens |
| --- | --- | --- | ---: | ---: |
| Food | ABSTAIN/ABSTAIN | PROPOSE → REVIEW | 3.549810 | 714 / 242 |
| Durga | REVIEW/REVIEW, one retained candidate | REVIEW → REVIEW, no actionable candidates | 5.875071 | 819 / 432 |
| Bicycle | ABSTAIN/ABSTAIN | PROPOSE → ABSTAIN, no candidates | 3.936057 | 733 / 288 |

Food was quarantined for `SOURCE_OBJECT_MISMATCH`, `SOURCE_REPLACEMENT_IDENTICAL` and `USER_CONSTRAINTS_UNRESOLVED`: its raw source description had already become the replacement. Bicycle's empty PROPOSE became no-action ABSTAIN with `PROPOSE_WITHOUT_EDITS` and `ABSTENTION_NORMALIZED`. Full Durga issues and all raw/final plans remain in the comparison and audit files below.

Historical offline suite grew from 41 tests at initial integration to 72 after decision-policy work. These are historical milestone counts, not the current total.

## Findings and limitations
Valid JSON does not establish cultural correctness. Source culture identifies original context; it is not a reason to reject a justified adaptation to a different target. A different target alone does not require an edit. Text matching can detect some contradictions but cannot prove semantic compatibility or complete injection resistance. Free-text preservation constraints require conservative human review.

## Final implementation status and essential artifacts
Local inference, explicit transport/schema errors and deterministic quarantine are implemented. No automatic planner-to-edit execution exists. [Result index](../results/phase3_llm/summary.md) links exact inputs, prompts, raw/final plans, model metadata and failure history. [Final comparison](../results/phase3_llm/experiments/planner_decision_policy_20261108_final/comparison.json), [root-cause evidence](../results/phase3_llm/experiments/planner_decision_policy_20261108_final/root_cause_analysis.json), [fixtures](../tests/fixtures/planning), [settings](../configs/planner.yaml).
