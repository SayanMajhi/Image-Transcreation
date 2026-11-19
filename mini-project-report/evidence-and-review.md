# Evidence and review map

| Report claim | Evidence | Status / boundary |
|---|---|---|
| Pipeline is staged and review-gated | `src/transcreation/`, `tests/test_edit_intent.py`, `tests/test_orchestration.py` | Implemented; automated real example still stopped at REVIEW. |
| 482 offline tests passed | `results/phase9_pilot/tests_full.log`, `REPRODUCTION.md` | Historical recorded run; offline tests do not prove model quality. |
| Phase 8 locality and runtime values | `results/phase8_cultural_validation/visual_improvement/independent_verification.json`, `runtime_summary.json` | Executed, research-only; diffusion visual success not established. |
| Six-case technical verification | `results/phase9_pilot/run_002/verification_summary.json` | PASS; 0 exterior/protected changes, deterministic replay. |
| Visual status of Phase 9 cases | `results/phase9_pilot/README.md`, `CASE_XX/REVIEW.md` | Assistant notes only, except historical CASE_01 direct user pass. |
| Human panel conclusion | `results/phase8_cultural_validation/human_evaluation_analysis/evaluation_summary.json` | Insufficient evidence: no genuine completed blinded panel forms. |
| Full-scene comparison | `results/submission_demo/full_scene_india_to_japan/README.md` | Supplementary guided illustration only; excluded from quantitative claims. |

## Review actions before submission

1. Fill the institute, department, supervisor, roll number and approved certificate wording in `mini-project-report`.
2. Compile with XeLaTeX and Biber in Overleaf; inspect all figures, the table of contents and references.
3. Do not change any pending human-review status without genuine review evidence and re-running the relevant validator.
4. Keep the generated full-scene illustration labelled as supplementary guided work.
