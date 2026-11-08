# Phase 3 Step 2: three real local-planner examples

The existing Ollama integration was inspected and reused. No second planner, new model, or new abstraction was introduced. This run rechecks the three requested scenarios through the actual CLI and archives fresh results without replacing earlier evidence.

## Important components

- `contracts.py`: defines the typed planning input, verified-object records, candidate edits, and PROPOSE/REVIEW/ABSTAIN result.
- `stages/ollama_planner.py`: sends the system prompt and separate JSON input to local Ollama with stream=false and JSON Schema; records actual responses and raises explicit transport/JSON/schema errors.
- `config.py` and `configs/planner.yaml`: configure model, local endpoint, timeout and generation options. This run uses qwen2.5:3b, timeout 180 seconds, temperature 0, seed 42, context 4096, output ceiling 1024, keep_alive 0.
- `stages/planning.py`: validates the draft and deterministically requires review for truncation, caption uncertainty, reported uncertainty, unsupported edit objects, or known instruction-injection markers. PROPOSE is only a draft, never image-edit authorization.
- `cli.py`: the plan command reads a planning-input JSON file, saves an audit record, refuses to overwrite existing results, and exits nonzero for inference/validation errors.
- `tests/test_ollama_planner.py`: mocked API checks for valid/malformed responses, missing model, connection failure, timeout, uncertainty, truncation, abstention, injection boundaries, and CLI recording.

## Actual generated results

Model: `qwen2.5:3b`, Q4_K_M, digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.

| example | raw decision | final decision | request seconds | generation seconds | prompt / output tokens |
| --- | --- | --- | ---: | ---: | ---: |
| [01_japanese_food](01_japanese_food.plan.json) | PROPOSE | REVIEW | 7.22 | 4.16 | 823 / 277 |
| [02_durga_uncertain_incense](02_durga_uncertain_incense.plan.json) | ABSTAIN | REVIEW | 7.55 | 4.45 | 928 / 329 |
| [03_bicycle_no_change](03_bicycle_no_change.plan.json) | ABSTAIN | REVIEW | 6.17 | 3.12 | 842 / 217 |

Each `.plan.json` contains the final validated contract object, copied exactly from its matching `.audit.json`. The audit includes the original generated response, exact prompts, input, schema, settings, installed-model identifier/digest, load/generation timing, token usage, deterministic validation, unloading outcome, and blank human-review notes. No generated wording has been corrected or embellished.

The Japanese food case is synthetic, with hypothetical user-verified ramen and source-culture assertions. The Durga Puja and bicycle captions are copied from archived VLM records; provenance remains in tests/fixtures/planning/scenarios.json.

## Observations

- Food: the model proposed a replacement dish but still confused some original/edited details and declared uncertainty, so the final plan requires REVIEW. Its cultural reasoning is an unverified model claim.
- Durga Puja: object identity is uncertain, and this actual archived caption is also truncated. Both are reasons for REVIEW; this example does not isolate their separate effects.
- Bicycle: raw ABSTAIN is appropriate for no obvious adaptation, but the model added unnecessary cultural doubts about graffiti. The conservative uncertainty rule changed the final result to REVIEW. This is an over-review limitation, not a successful final ABSTAIN.
- Structural validity does not establish cultural correctness. The model can still stereotype, misunderstand the scene, or propose an inappropriate localization phrase. No image modification is authorized.
- Request time includes local model lookup/loading and response handling. Generation time is Ollama eval_duration converted from nanoseconds and excludes loading and prompt processing. Loading and full CLI wall times are retained in summary.json.
- The examples ran sequentially without loading SmolVLM. Automatic and explicit unloading were used; /api/ps reported no model loaded after each run. No new peak-memory measurement was made for these three runs.

## Verification and diff summary

- 41 offline tests passed in 0.291 seconds, including 17 mocked Ollama tests, 13 planning-contract tests, and 11 existing captioning tests.
- All three real CLI invocations exited with code 0 and passed structural validation.
- git diff --check passed.
- SHA-256 verification confirmed 243 pre-existing source/config/evidence files unchanged, including VLM implementation/settings, earlier outputs/reports, and local research archives.
- This request reused the existing integration and tests. The only source adjustment was correcting a stale planning-module docstring. Fresh artifacts are confined to this new report directory.
- The working-tree diff also contains the earlier, still-uncommitted planner integration and contracts. These changes were preserved, not recreated or committed.
- No new dependencies, other LLMs, segmentation, inpainting, commit, or push.

## Run the planner

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/new_food_plan.json
```

Use a new output filename. Substitute `02_durga_uncertain_incense.json` or `03_bicycle_no_change.json` for the other examples.
