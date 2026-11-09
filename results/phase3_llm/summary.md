# Phase 3 evidence

[Phase report](../../reports/phase3_llm.md).

`experiments/` contains actual saved Qwen responses, requests/prompts, model metadata, validated plans, issue codes and rejected candidates. Failed revisions are retained because they substantiate the validation corrections.

- [Initial six fixtures](experiments/ollama_planner_phase3_20261108/)
- [Prompt revision 2](experiments/ollama_planner_phase3_20261108_prompt_v2/)
- [Prompt revision 3 and schema rejection](experiments/ollama_planner_phase3_20261108_prompt_v3/)
- [Three CLI cases](experiments/phase3_step2_three_examples_20261108/)
- [Failed consistency revision](experiments/planner_quality_review_20261108/)
- [Final consistency revision](experiments/planner_quality_review_20261108_final/)
- [Initial policy run](experiments/planner_decision_policy_20261108/)
- [Final policy run: inputs, raw proposals and final plans](experiments/planner_decision_policy_20261108_final/)
- [Raw/final comparison and tokens/timings](experiments/planner_decision_policy_20261108_final/comparison.json)
- [Root causes](experiments/planner_decision_policy_20261108_final/root_cause_analysis.json)

Final food: PROPOSE → REVIEW; source/replacement confusion remains in raw evidence, with candidates quarantined. Durga: REVIEW → REVIEW, unsafe proposals withheld. Bicycle: empty PROPOSE → ABSTAIN, no image change. These are validation decisions, not cultural correctness scores. The ramen verification is a hypothetical fixture assertion, not newly verified photographic evidence.

[Input fixtures](../../tests/fixtures/planning/) and [current model settings](../../configs/planner.yaml) remain active. JSON bytes, exact prompts and measurements are unchanged; old path strings are historical provenance resolved through [the relocation manifest](../relocation_manifest.json). Original iteration prose/code snapshots are recoverable in [the text provenance backup](../historical_text_provenance.zip).
