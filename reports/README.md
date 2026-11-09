# Reports and research evidence

These links index existing evidence; no experimental results have been moved or
rewritten. Raw model output is not verified visual or cultural ground truth.

## Current summaries

- [Post-VLM development report and interview guide](Planner_Development_and_Validation_Report.md): one chronological explanation of the planner experiments, findings, fixes, technical design, tests, hardware, and cleanup. Start here after VLM selection.
- [Repository cleanup review](repository_cleanup_review.md): audit classifications,
  before/after tests, environment/CLI checks, unchanged evidence, and remaining issues.
- [Latest planner validation](planner_decision_policy_20261108_final/REPORT.md):
  source/target reasoning, candidate quarantine, protected constraints, issue codes,
  and the recorded 72-test milestone.
- [Planner review package](../outputs/planner_review.md): concise review with the
  three inputs, raw outputs, final plans, root causes, and limitations.
- [VLM selection findings](VLM_Selection_Experimental_Findings_Refined.md): comparison
  findings and the reasons for selecting SmolVLM rather than the retired baselines.

## Planner experiment history

| Evidence | What it records |
| --- | --- |
| [Initial Ollama run](ollama_planner_phase3_20261108/summary.json) | Six scenarios with the first system prompt |
| [Prompt iteration 2](ollama_planner_phase3_20261108_prompt_v2/summary.json) | Revised instructions and observed model failures |
| [Prompt iteration 3](ollama_planner_phase3_20261108_prompt_v3/REPORT.md) | Source/future confusion and an explicitly rejected response |
| [Three CLI examples](phase3_step2_three_examples_20261108/REPORT.md) | Recorded food, Durga Puja, and bicycle invocations |
| [First consistency revision](planner_quality_review_20261108/comparison.json) | Unsuccessful prompt revision retained as evidence |
| [Consistency revision summary](planner_quality_review_20261108_final/REPORT.md) | Original-scene, localization, preservation, and uncertainty checks |
| [First decision-policy run](planner_decision_policy_20261108/comparison.json) | Empty-proposal contract failure before the no-action rule |
| [Final decision-policy evidence](planner_decision_policy_20261108_final/comparison.json) | Raw/final decisions, coded rejections, runtime, and token use |

Repeated captions or identical inputs belong to different recorded trials. They
were not deduplicated: surrounding prompts, timing, code, and validation may differ.

## Historical VLM evidence

- [Consolidated saved outputs](../.local_archive/experiment_results.md)
- [Model-comparison interpretation](../.local_archive/model_comparison.md)
- [Original experiment archive](../.local_archive/smolvlm_commitment_20261108/)
- [Archive manifest](../.local_archive/smolvlm_commitment_20261108/manifest.json)
- [Fixture provenance](../tests/fixtures/planning/scenarios.json)

The archive includes BLIP/Florence baselines, SmolVLM captions, token-ceiling and
concise-prompt experiments, diagnostics, and prior cleanup records. Historical files
may contain paths from an older layout; they are preserved rather than silently
edited. Current images live under `data/`, including `data/sample_images/durga.jpg`.

`.local_archive/` is Git-ignored. No independent backup was verified. The tracked
VLM findings summarize some results but are not a complete backup of raw evidence.
