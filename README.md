# Culture-aware image transcreation

The project describes an image with **SmolVLM-500M**, then uses **Qwen2.5-3B through
local Ollama** to draft cultural adaptations. Deterministic validation checks the
planner output. It does not edit images.

Implemented: single-image captioning, a typed cultural planner, candidate quarantine,
raw/final audit records, mocked tests, and reproducible planner evaluation.
Grounding DINO is next; grounding, segmentation, inpainting, and complete transcreation
are not implemented. BLIP and Florence-2 are retired research baselines.

## Structure

```text
MiniProject/
|-- src/transcreation/
|   |-- cli.py                 caption and plan commands
|   |-- config.py              validated caption/planner settings
|   |-- contracts.py           typed inputs, drafts, and results
|   |-- pipeline.py            captioning entry point and device selection
|   `-- stages/
|       |-- caption.py         SmolVLM loading, prompts, generation, measurements
|       |-- planning.py        deterministic validation and mock planner
|       `-- ollama_planner.py  local HTTP adapter and audit records
|-- configs/                   models.yaml and planner.yaml
|-- tests/                     offline tests and planning fixtures
|-- scripts/evaluate_planner.py reproducible real-model evaluation utility
|-- data/                      source images and datasets
|-- outputs/                   generated captions/plans and review packages
|-- reports/                   findings, saved experiment evidence, cleanup review
|-- .local_archive/            historical research, ignored by Git
`-- pyproject.toml             installation, dependencies, console entry point
```

Python package marker files remain in place. Three existing docstring-only future
stage modules remain for path compatibility and are flagged in the cleanup review;
they are not implemented stages. SmolVLM lives in `caption.py`; no separate
`smolvlm.py` wrapper is required. Local environments, caches, and editor files are
separate from application code.

## Installation

Use Python 3.11 and run commands from the project root. If no environment exists:

```powershell
py -3.11 -m venv .venv
```

Install or refresh the project:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

This registers `transcreate` as `transcreation.cli:main`. An older local launcher
may still reference the retired `main` module; reinstalling refreshes it. The source
commands below also work without changing generated installation metadata.

## Run captioning and planning

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli caption --image data/sample_images/durga.jpg --out outputs/caption_new.json
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/plan_new.json
```

After editable installation, `transcreate caption ...` and `transcreate plan ...`
provide the same commands. Use `--help`, `caption --help`, or `plan --help` for flags.
Use fresh output names: planner records are never overwritten.

Captioning uses [configs/models.yaml](configs/models.yaml). Planning uses
[configs/planner.yaml](configs/planner.yaml), with model, local endpoint, timeout,
keep-alive, seed, and generation options. CLI overrides include `--model`,
`--endpoint`, and `--timeout` for planning. Do not change settings when reproducing
a recorded experiment without recording that change.

Captioning downloads weights if uncached. Planning requires Ollama running with
`qwen2.5:3b` installed (`ollama pull qwen2.5:3b` if needed); the application does not
silently download the LLM or fabricate a plan when Ollama fails.

## How the modules communicate

The commands are separate stages, not an automatic end-to-end workflow:

1. Captioning returns text, model/settings metadata, and completion flags.
2. `PlanningInput.from_caption(caption_result, target_culture=...)` converts a typed
   caption result into planning input. It maps completion flags and never creates
   verified objects. Users supply the target culture, optional source context,
   instructions, and independently checked object records.
3. The planner CLI reads that planning-input JSON, not the full caption audit JSON.
   [Planning fixtures](tests/fixtures/planning/) demonstrate the input shape.
4. Ollama receives fixed system instructions plus separate input data. The response
   is parsed, checked against the contracts, and passed through validation.

Caption claims remain unverified. Source culture describes the original context;
target culture is the requested context. A cultural difference alone does not
require an edit. Run the stages sequentially on a 4 GB GPU; the planner requests
unloading and records cleanup failures rather than assuming both models fit.

## Validation and audit records

- `PROPOSE`: a conditional draft, never permission to modify an image.
- `REVIEW`: unresolved facts, invalid candidates, truncation, or preservation concerns;
  the final candidate list is empty.
- `ABSTAIN`: no image change; final candidates and edit-verification checks are empty.

Source IDs must match user-verified originals. Placeholders, scene-length localization,
source/replacement mix-ups, and detectable preservation conflicts are checked.
Free-text user constraints are handled conservatively: their compatibility with an
edit requires human review. Text checks do not prove cultural or visual correctness.

Audit JSON keeps `response` and `raw_planning_result` separate from `planning_result`.
`validation.issues` explains decisions; `rejected_candidates` retains quarantined
proposals, and `raw_schema_valid` distinguishes raw from final validity.
`automatically_authorized` is always false. A coded empty proposal can resolve to
no-action abstention; it never produces an invented edit. Malformed JSON, top-level
schema failures, timeouts, and connection failures remain explicit errors.

## Tests and reproducible evaluation

Offline tests do not need running models or model downloads:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Real evaluation is a separate, intentional operation requiring Ollama:

```powershell
.\.venv\Scripts\python.exe -B scripts/evaluate_planner.py --out reports/new_planner_run
```

Use a new directory. The utility records a standalone probe, six fixtures, exact
prompts/settings/model digest, raw/final output, timings, token use, and memory
observations. This is not an automatic cultural-correctness benchmark.

## Reports and evidence

Start with the [report index](reports/README.md), including the latest planner
validation, VLM findings, and [cleanup review](reports/repository_cleanup_review.md).
Existing inference artifacts remain in `outputs/`; experiment bundles remain at
their recorded paths in `reports/` to preserve links and provenance.

Historical VLM raw outputs, token-ceiling/concise-prompt experiments, and retired
code are in `.local_archive/`. That folder, datasets, and outputs are Git-ignored.
No independent backup of the local archive was verified during cleanup; Git history
alone does not protect its untracked contents. Preserve/backup these files separately.
