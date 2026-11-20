# Cultural-planner validation review

Evidence-only review of the latest saved decision-policy evaluation. No model or tests were rerun; code and existing results were not changed. Expand the scenario evidence below for all three inputs, verbatim raw LLM outputs, and final validated JSON plans.

**Model:** `qwen2.5:3b` (Q4_K_M); digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Settings remained temperature 0, seed 42, context 4096, output limit 1024, and keep-alive 0. The scenarios are single observations, not a cultural-accuracy benchmark. The food fixture asserts hypothetical user verification; it is not a newly verified real image.

## Decisions and runtime

| Scenario | Previous raw / final | Latest raw / final | Final candidates before -> after | Generation time | Input / output tokens |
| --- | --- | --- | ---: | ---: | ---: |
| Japanese meal -> India | ABSTAIN / ABSTAIN | PROPOSE / REVIEW | 0 -> 0 | 3.55 s | 714 / 242 |
| Durga Puja -> Japan | REVIEW / REVIEW | REVIEW / REVIEW | 1 -> 0 | 5.88 s | 819 / 432 |
| Bicycle -> India | ABSTAIN / ABSTAIN | PROPOSE / ABSTAIN | 0 -> 0 | 3.94 s | 733 / 288 |

All three final candidate lists are empty and `automatically_authorized` is false. Generation time excludes loading; total request times were 6.07 s, 9.03 s, and 6.95 s respectively. A valid **final** contract does not establish that the raw model response, scene claims, or cultural reasoning were correct.

## Validation issue codes

**Japanese meal -> India**

- `SOURCE_OBJECT_MISMATCH` (review; candidate 0): The source-object identity does not match the user-verified description.
- `SOURCE_REPLACEMENT_IDENTICAL` (review; candidate 0): The proposed replacement/modification is indistinguishable from the original object.
- `USER_CONSTRAINTS_UNRESOLVED` (review; plan-wide): Check all proposals against supplied user instructions/protected constraints; text validation cannot prove compatibility.

**Durga Puja -> Japan**

- `CAPTION_INCOMPLETE` (review; plan-wide): Verify the complete source caption and image before planning an edit.
- `MODEL_REVIEW_REQUESTED` (review; plan-wide): The model requested context review; no direct edit is authorized.

**Bicycle -> India**

- `PROPOSE_WITHOUT_EDITS` (info; plan-wide): The raw decision proposed no edit; resolve only to a no-action disposition, never invent a candidate.
- `ABSTENTION_NORMALIZED` (info; plan-wide): No-edit reason and checks normalized; raw cultural claims/checks remain in the audit.

Food: the replacement was mislabeled as the verified source object and repeated as its own replacement; its candidate was removed. Durga: the latest response already has no edits; truncation still blocks action. Bicycle: raw `PROPOSE` contains no actual candidate (`raw_schema_valid: false`); the explicit no-action policy produces `ABSTAIN`, without inventing an edit or retaining cultural restrictions.

## Root causes of the previous failures

| Failure | Diagnosis by layer | Validation change |
| --- | --- | --- |
| Food source/target confusion | Input correctly specified Japan -> India. Prompt under-specified that distinction; Qwen treated source membership as a reason to abstain. Structural validation could not assess its rationale, and postprocessing accepted it unchanged. | Explicit target-context instructions and conservative contextual review; source membership neither requires nor rules out adaptation. |
| Unsafe protected-content edit in REVIEW | Input marked truncation and protected worship, idol, people and relationships. Qwen violated those instructions; the application also failed by flagging REVIEW while retaining the candidate. | Final REVIEW releases no candidates; truncation and unresolved user constraints have coded blockers. |
| Placeholder description / scene localization | Qwen generated the quoted description `"null"` and a scene paragraph. The observed verified-object ID was already actual JSON null. Nonempty-string validation accepted both invalid descriptions; warnings did not remove them. | Placeholder/nullable-ID checks, short-phrase bounds, and candidate quarantine. |
| Irrelevant bicycle checks | Input requested an ordinary unchanged scene. Qwen invented cultural checks; string-list validation and postprocessing carried them into ABSTAIN. | Neutral no-action reason and empty verification requirements, with raw claims retained separately. |

Offline replay of the previously saved raw responses is recorded in [previous_raw_revalidated.json](../reports/planner_decision_policy_20261108_final/previous_raw_revalidated.json):

- Japanese meal -> India: `REVIEW`, 0 candidates; `ABSTENTION_CONTEXT_UNVERIFIED`.
- Durga Puja -> Japan: `REVIEW`, 0 candidates; `PLACEHOLDER_OBJECT_FIELD`, `LOCALIZATION_NOT_OBJECT_PHRASE`, `BATCH_REVIEW_REQUIRED`, `CAPTION_INCOMPLETE`, `USER_CONSTRAINTS_UNRESOLVED`.
- Bicycle -> India: `ABSTAIN`, 0 candidates; `ABSTENTION_NORMALIZED`.

These replays were saved during implementation; this review did not execute validation again. The earlier failed real run, including the empty-PROPOSE schema error, remains in [its original evidence directory](../reports/planner_decision_policy_20261108/).

## Regression tests (previously recorded)

| Stage | Tests | Result | Reported test time |
| --- | ---: | --- | ---: |
| Before changes | 53 | OK | 0.338 s |
| After changes | 72 | OK | 0.233 s |

Nineteen new regressions cover source/target reasoning, placeholder fields, JSON null versus string null, long localization, verified references, protected constraints, truncated candidates, valid drafts, no-action abstention, raw audit preservation, and empty proposals. Existing JSON, connection, timeout, schema and SmolVLM tests remain covered. The saved record confirms tests passed before final inference. [Test evidence](../reports/planner_decision_policy_20261108_final/test_results.json).

## Task-specific Git diff

This is the saved diff relative to the start of the validation-change request, not the cumulative working tree containing earlier uncommitted work.

| File | Added | Removed |
| --- | ---: | ---: |
| `README.md` | 41 | 1 |
| `src/transcreation/contracts.py` | 33 | 4 |
| `src/transcreation/stages/ollama_planner.py` | 72 | 52 |
| `src/transcreation/stages/planning.py` | 145 | 53 |
| `tests/test_ollama_planner.py` | 20 | 2 |
| `tests/test_planning.py` | 6 | 4 |
| `tests/test_planning_policy.py` (new) | 195 | 0 |

**Total:** 7 code/docs/test files, 512 additions and 116 deletions, plus new evaluation evidence. [Saved patch](../reports/planner_decision_policy_20261108_final/task_changes.diff) / [diff summary](../reports/planner_decision_policy_20261108_final/task_diff_summary.json).
The saved verification reported 285 pre-existing evidence/configuration files unchanged. Model/quantization/settings, fixtures, SmolVLM and CLI commands were preserved; no model, dependency, image-editing stage, commit or push was added.

## Remaining limitations

- Qwen still confuses source and replacement objects and can mix imagined edits into a scene summary. REVIEW summaries and preservation statements remain unverified model claims.
- Text checks cannot prove visual identity, cultural correctness, protected-content compatibility, or arbitrary paraphrased contradictions. A short phrase is not proof of correct single-object localization.
- Free-text user constraints conservatively block pending edits until reviewed, including some legitimate preferences. Known-source verified adaptation requests may also receive unnecessary contextual review.
- Raw candidate rejection and no-action normalization improve downstream safety, not model reasoning. The food result is a justified validation REVIEW, not a successfully grounded adaptation.
- Raw reasons/checks are intentionally retained even when unsupported. Use final policy results for downstream disposition and raw/rejected data for review; no result automatically authorizes modification.

## Complete scenario evidence

JSON below is copied from the saved files without changing generated wording. The matching audit retains exact prompts, full Ollama responses, rejected candidates, decision changes and validation metadata. Human-review notes remain blank.

<details>
<summary>Japanese meal -> India: input, raw response, final plan</summary>

Sources: [input](../reports/planner_decision_policy_20261108_final/01_japanese_food.input.json), [raw](../reports/planner_decision_policy_20261108_final/01_japanese_food.raw.json), [final](../reports/planner_decision_policy_20261108_final/01_japanese_food.plan.json), [full audit](../reports/planner_decision_policy_20261108_final/01_japanese_food.audit.json).

### Original input

```json
{
  "source_caption": "Two people share lunch at a table. A bowl of ramen with chopsticks sits between them.",
  "caption_status": "COMPLETE",
  "target_culture": "India",
  "source_culture": "Japan",
  "user_instructions": "Adapt only the meal if justified; keep both people, their shared lunch, and seating.",
  "verified_objects": [
    {
      "object_id": "meal-1",
      "description": "bowl of ramen"
    }
  ]
}
```

### Raw Qwen output ? unchanged

```json
{
  "decision": "PROPOSE",
  "decision_reason": "The meal (ramen) is adapted to a culturally appropriate Indian dish, maintaining the scene purpose and relationships.",
  "scene_summary": "Two people share lunch at a table. A bowl of ramen with chopsticks sits between them. The meal is adapted to an Indian dish, maintaining the scene purpose and relationships.",
  "candidate_edits": [
    {
      "object_description": "bowl of dal with curry and rice",
      "localization_phrase": "bowl of dal with curry and rice",
      "proposed_change": "bowl of dal with curry and rice",
      "cultural_reason": "Dal is a common Indian dish that can be served with rice and curry, providing a culturally appropriate alternative to ramen.",
      "identity_uncertain": false,
      "verified_object_id": "meal-1"
    }
  ],
  "must_preserve": ["Two people share lunch at a table.", "A bowl of ramen with chopsticks sits between them.", "Both people remain seated."],
  "uncertainties": [],
  "verification_requirements": []
}
```

### Final validated plan

```json
{
  "decision": "REVIEW",
  "decision_reason": "Review required; no candidate edit is released downstream. The source-object identity does not match the user-verified description. The proposed replacement/modification is indistinguishable from the original object. Check all proposals against supplied user instructions/protected constraints; text validation cannot prove compatibility.",
  "scene_summary": "Two people share lunch at a table. A bowl of ramen with chopsticks sits between them. The meal is adapted to an Indian dish, maintaining the scene purpose and relationships.",
  "candidate_edits": [],
  "must_preserve": [
    "Two people share lunch at a table.",
    "A bowl of ramen with chopsticks sits between them.",
    "Both people remain seated."
  ],
  "uncertainties": [],
  "verification_requirements": [
    "The source-object identity does not match the user-verified description.",
    "The proposed replacement/modification is indistinguishable from the original object.",
    "Check all proposals against supplied user instructions/protected constraints; text validation cannot prove compatibility.",
    "Review the original-scene summary and any paraphrased identities against the image.",
    "Human review must check protected content and preservation; text checks cannot prove semantic correctness."
  ]
}
```

</details>

<details>
<summary>Durga Puja -> Japan: input, raw response, final plan</summary>

Sources: [input](../reports/planner_decision_policy_20261108_final/02_durga_uncertain_incense.input.json), [raw](../reports/planner_decision_policy_20261108_final/02_durga_uncertain_incense.raw.json), [final](../reports/planner_decision_policy_20261108_final/02_durga_uncertain_incense.plan.json), [full audit](../reports/planner_decision_policy_20261108_final/02_durga_uncertain_incense.audit.json).

### Original input

```json
{
  "source_caption": "The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga. The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke. Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms. The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess. The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood.\n\nThe background includes a building with a large, white wall and a few trees",
  "caption_status": "TRUNCATED",
  "target_culture": "Japan",
  "source_culture": "India",
  "user_instructions": "The source context is Durga Puja. The incense-object identity is uncertain. Preserve worship, the idol, people, and their relationships.",
  "verified_objects": []
}
```

### Raw Qwen output ? unchanged

```json
{
  "decision": "REVIEW",
  "decision_reason": "The scene depicts Durga Puja, a significant religious event in India. The proposed target culture is Japan, which is not a common context for Durga Puja. The scene includes elements that are specific to Indian culture and religion, such as the goddess Durga, her headdress, and the offerings of incense sticks. These elements would need to be adapted in a way that is culturally appropriate and meaningful in Japan, which is not a straightforward process. The proposed change would require a detailed understanding of Japanese religious practices and cultural norms, which is beyond the scope of this system.",
  "scene_summary": "The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga. The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke. Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms. The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess. The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood. The background includes a building with a large, white wall and a few trees.",
  "candidate_edits": [],
  "must_preserve": ["The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga.", "The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke.", "Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms.", "The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess.", "The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood.", "The background includes a building with a large, white wall and a few trees."],
  "uncertainties": [],
  "verification_requirements": []
}
```

### Final validated plan

```json
{
  "decision": "REVIEW",
  "decision_reason": "Review required; no candidate edit is released downstream. Verify the complete source caption and image before planning an edit. The model requested context review; no direct edit is authorized.",
  "scene_summary": "The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga. The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke. Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms. The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess. The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood. The background includes a building with a large, white wall and a few trees.",
  "candidate_edits": [],
  "must_preserve": [
    "The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga.",
    "The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke.",
    "Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms.",
    "The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess.",
    "The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood.",
    "The background includes a building with a large, white wall and a few trees."
  ],
  "uncertainties": [],
  "verification_requirements": [
    "Verify the complete source caption and image before planning an edit.",
    "The model requested context review; no direct edit is authorized.",
    "Review the original-scene summary and any paraphrased identities against the image.",
    "Human review must check protected content and preservation; text checks cannot prove semantic correctness."
  ]
}
```

</details>

<details>
<summary>Bicycle -> India: input, raw response, final plan</summary>

Sources: [input](../reports/planner_decision_policy_20261108_final/03_bicycle_no_change.input.json), [raw](../reports/planner_decision_policy_20261108_final/03_bicycle_no_change.raw.json), [final](../reports/planner_decision_policy_20261108_final/03_bicycle_no_change.plan.json), [full audit](../reports/planner_decision_policy_20261108_final/03_bicycle_no_change.audit.json).

### Original input

```json
{
  "source_caption": "A bicycle is leaning against a set of black doors. The doors are framed with white trim and have graffiti on them. The graffiti is in various colors including blue, white, yellow, and black. The bicycle is black and has a front basket. The sidewalk is made of brick and is lined with black doors.",
  "caption_status": "COMPLETE",
  "target_culture": "India",
  "source_culture": null,
  "user_instructions": "Keep the ordinary parked-bicycle activity; do not add cultural decoration.",
  "verified_objects": []
}
```

### Raw Qwen output ? unchanged

```json
{
  "decision": "PROPOSE",
  "decision_reason": "The scene depicts a common parked bicycle activity in a specific urban setting. The target culture is India, which is a diverse country with various urban landscapes. The proposed change is to keep the ordinary parked-bicycle activity and maintain the original scene's meaning and relationships. The bicycle, doors, graffiti, and sidewalk are kept as they are, and no cultural decoration is added. The bicycle is black and has a front basket, and the doors are black with graffiti. The sidewalk is made of brick and lined with black doors. The scene's purpose is to depict a typical urban setting with a parked bicycle, and the target culture is India, which can accommodate this scene without adding cultural decoration.",
  "scene_summary": "A bicycle is leaning against a set of black doors. The doors are framed with white trim and have graffiti on them. The bicycle is black and has a front basket. The sidewalk is made of brick and is lined with black doors.",
  "candidate_edits": [],
  "must_preserve": ["A bicycle is leaning against a set of black doors.", "The doors are framed with white trim and have graffiti on them.", "The bicycle is black and has a front basket.", "The sidewalk is made of brick and is lined with black doors."],
  "uncertainties": [],
  "verification_requirements": []
}
```

### Final validated plan

```json
{
  "decision": "ABSTAIN",
  "decision_reason": "No justified image edit is established; leave the source image unchanged. This does not authorize modification or certify cultural appropriateness.",
  "scene_summary": "A bicycle is leaning against a set of black doors. The doors are framed with white trim and have graffiti on them. The bicycle is black and has a front basket. The sidewalk is made of brick and is lined with black doors.",
  "candidate_edits": [],
  "must_preserve": [
    "A bicycle is leaning against a set of black doors.",
    "The doors are framed with white trim and have graffiti on them.",
    "The bicycle is black and has a front basket.",
    "The sidewalk is made of brick and is lined with black doors."
  ],
  "uncertainties": [],
  "verification_requirements": []
}
```

</details>

Detailed implementation evidence: [full report](../reports/planner_decision_policy_20261108_final/REPORT.md), [comparison measurements](../reports/planner_decision_policy_20261108_final/comparison.json), and [layer-by-layer diagnosis](../reports/planner_decision_policy_20261108_final/root_cause_analysis.json).
