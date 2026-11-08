# Culture transcreation

This project currently describes images using SmolVLM-500M. It prints a caption
and saves the caption plus run details to JSON. A separate cultural planner uses
local Qwen2.5-3B through Ollama. Its output is a draft for human review; image
editing is still future work. The typed interface and mock planner remain available.

## Structure

```text
MiniProject/
|-- configs/
|   |-- models.yaml          Existing SmolVLM settings
|   `-- planner.yaml         Local Ollama settings
|-- data/
|   `-- sample_images/       Place new input images here
|-- src/
|   `-- transcreation/
|       |-- __init__.py      Marks the Python package
|       |-- cli.py           Reads commands, opens images, saves results
|       |-- config.py        Reads and validates models.yaml (only config.py)
|       |-- contracts.py     Defines captioning and planning inputs/results
|       |-- pipeline.py      Selects CPU/GPU and runs captioning
|       `-- stages/
|           |-- __init__.py  Marks the stages package
|           |-- caption.py   Loads SmolVLM and generates image descriptions
|           |-- planning.py  Planning validation, review rules, and mock planner
|           |-- ollama_planner.py Local Qwen HTTP adapter and audit records
|           |-- grounding.py Future: locate objects to adapt
|           |-- segmentation.py Future: create masks for those objects
|           `-- inpainting.py Future: edit masked regions
|-- tests/                   Offline tests and six planning input fixtures
|-- scripts/evaluate_planner.py Standalone probe and six sequential planner runs
|-- outputs/                 Generated results
|-- reports/                 Saved experiment results and model comparison
|-- pyproject.toml           Dependencies and transcreate command
|-- .gitignore               Keeps local/generated files out of Git
`-- README.md                This guide
```

The project folder on this computer remains `MiniProject`.
Existing input images remain at their original paths, including `data/sample_images/durga.jpg`.
Generated files, environments, caches, installation metadata, and local archives
are left in place. `.venv/`, `.python311/`, `.idea/`, `*.egg-info/`, and
`__pycache__/` are local tool folders, separate from the source structure above.

## Flow

`cli.py` receives your image path -> `config.py` checks `configs/models.yaml` ->
`pipeline.py` chooses CPU/GPU -> `stages/caption.py` runs SmolVLM -> `cli.py`
prints the caption and saves a result in `outputs/` using `contracts.py`.

Planning is available separately through the `plan` command or Python interface;
it is not automatically run by the caption command. Grounding, segmentation, and inpainting remain placeholders.

## How to run (Windows PowerShell)

Use Python 3.11 and open the project root:

```powershell
cd C:\Users\sayan\PycharmProjects\MiniProject
```

If you do not already have `.venv`, create it:

```powershell
py -3.11 -m venv .venv
```

Install or refresh the project after the structure change:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

This installation step updates generated installation metadata and the
`transcreate` command to point to `transcreation.cli`.

Run the existing sample image:

```powershell
.\.venv\Scripts\transcreate.exe caption --image data/durga.jpg --out outputs/caption.json
```

Or use Python directly after installation:

```powershell
.\.venv\Scripts\python.exe -m transcreation.cli caption --image data/durga.jpg --out outputs/caption.json
```

For a new image, put it in `data/sample_images/` and substitute its path.
For a shorter caption, add `--prompt-variant concise_grounded`.
The first captioning run downloads model weights if they are not already cached.

The caption prints in the terminal. The JSON includes the caption, prompt,
image hash, model revision, settings, timing, memory, and completion flags.

To run directly from source without refreshing generated installation files:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli caption --image data/durga.jpg --out outputs/caption.json
```

In PyCharm, select `.venv\Scripts\python.exe`, run the module
`transcreation.cli`, set parameters to `caption --image data/durga.jpg`, and use
the project root as the working directory. Mark `src` as Sources Root if needed.

## Settings and tests

`configs/models.yaml` selects SmolVLM-500M, pins its checkpoint revision, and uses
a 128-token output limit. GPU uses float16; CPU automatically uses float32.
Transformers is pinned to 4.57.6, and remote model code is disabled.
The default settings path is found relative to the source checkout; if you use
an installed copy without the checkout, supply `--config path/to/models.yaml`.
A result with `eos_reached: false` and `token_ceiling_reached: true` may be cut short.

Run offline tests from the source tree without creating Python bytecode:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Tests use a mocked model and do not download weights or run full AI inference.

See [model findings](.local_archive/model_comparison.md) and
[saved experimental outputs](.local_archive/experiment_results.md).
Original experiment evidence remains in
`.local_archive/smolvlm_commitment_20261108/`.

## Phase 3: cultural-planning contract

The planner receives an unverified caption and user information, then returns a
structured draft. `contracts.py` defines its typed data; `stages/planning.py`
validates responses and applies review rules. `stages/ollama_planner.py` adds
the real local adapter while keeping these contracts and mock fixtures. No
culture-specific substitution rules or new dependencies are included.

### Input and output schema

`PlanningInput`:

| field | type | meaning |
| --- | --- | --- |
| `source_caption` | nonempty string | model-generated description, never verified visual truth |
| `caption_status` | `CaptionStatus` | `COMPLETE`, `TRUNCATED`, or `UNKNOWN` |
| `target_culture` | nonempty string, required | user's requested target context |
| `source_culture` | string or `None` | optional user-declared context, not inferred from appearance |
| `user_instructions` | string or `None` | optional requested edits |
| `verified_objects` | tuple of `VerifiedObject` | user-checked `{object_id, description}` records; defaults to empty |

`PlanningInput.from_caption(caption_result, target_culture, ...)` reuses an
existing caption result. It maps SmolVLM's completion flags into the status above;
older results without those flags become `UNKNOWN`. Reaching an end-of-sequence
marker counts as complete even when the token ceiling is also reached. The
conversion does not create any verified objects.

`PlanningResult`:

| field | type | meaning |
| --- | --- | --- |
| `decision` | `PlanningDecision` | `PROPOSE` (draft), `REVIEW` (needs checking), or `ABSTAIN` (no edit suggested) |
| `decision_reason` | nonempty string | explanation of the decision and any enforced review |
| `scene_summary` | nonempty string | original scene only; retain and attribute unverified caption claims |
| `candidate_edits` | tuple of `CandidateEdit` | suggested changes |
| `must_preserve` | tuple of strings | unchanged features and relationships; not an object identity being replaced |
| `uncertainties` | tuple of strings | unresolved facts material to the planning decision or edit |
| `verification_requirements` | tuple of strings | specific checks before permitting an edit |

Each `CandidateEdit` has nonempty `object_description`, `localization_phrase`,
`proposed_change`, and `cultural_reason` strings; a required `identity_uncertain`
boolean; and an optional `verified_object_id`. That id only references an existing
user-checked input object. It cannot create verification. Candidate descriptions
must exactly match the referenced description to avoid enforced review.

`object_description` names the original object, `localization_phrase` locates that
original object and retains its label, and only `proposed_change` describes the
future replacement/modification. A verified source-object id never verifies a
replacement object or a generated scene summary.

The parser accepts JSON-shaped dictionaries with lists for collection fields,
converts them to immutable tuples, and rejects missing/extra fields and wrong
value types. Direct dataclass construction is also validated. `PROPOSE` requires
an edit; `ABSTAIN` forbids edits; edits require features to preserve.
`dataclasses.asdict()` followed by `json.dumps()` serializes typed inputs/results.

### Review rules

Call `plan_cultural_edits(request, planner)` to apply these rules. Calling
`planner.plan()` alone only obtains its draft and bypasses the review wrapper.

- Truncated or unknown caption completion forces `REVIEW`, even for abstention.
- Unresolved uncertainty with proposed edits or an uncertain/unverified source
  object forces `REVIEW`. A complete no-edit `ABSTAIN` can retain unrelated doubts;
  leaving an image unchanged is not approval of an edit or of the caption's truth.
- Missing source labels in localization, detectable replacement phrases in the
  original-scene summary, and potential preserve/edit conflicts force review.
- An existing `REVIEW` is never promoted to `PROPOSE`.
- Every plan containing edits requires user checks of cultural suitability and
  future visual localization. `PROPOSE` never means automatic approval.

Only the caller supplies `VerifiedObject` input after human checking. Model
summaries, reasons, object descriptions, and localization phrases remain generated
claims. This contract cannot discover a model's unreported factual errors or
prove cultural suitability; actual visual/human verification is still required.

### Mocked example

This fixture follows a hypothetical user's explicit food choice. It is not a
rule about how a culture should be represented.

```python
from transcreation.contracts import CaptionStatus, PlanningInput, VerifiedObject
from transcreation.stages.planning import MockPlanner, plan_cultural_edits

request = PlanningInput(
    source_caption="A plate of pasta on a wooden table.",
    caption_status=CaptionStatus.COMPLETE,
    target_culture="Japanese home meal",
    user_instructions="Show soba instead of pasta; keep the table and lighting.",
    verified_objects=(VerifiedObject("food-1", "plate of pasta"),),
)
planner = MockPlanner({
    "decision": "PROPOSE",
    "decision_reason": "The user explicitly requested a food adaptation.",
    "scene_summary": "The caption reports a plate of pasta on a wooden table.",
    "candidate_edits": [{
        "object_description": "plate of pasta",
        "localization_phrase": "plate of pasta on the table",
        "proposed_change": "Show soba in a bowl in the same position.",
        "cultural_reason": "Follow the user's requested Japanese home meal presentation.",
        "identity_uncertain": False,
        "verified_object_id": "food-1",
    }],
    "must_preserve": ["wooden table", "lighting", "camera angle"],
    "uncertainties": [],
    "verification_requirements": [],
})
result = plan_cultural_edits(request, planner)
print(result.decision)  # REVIEW: free-text user constraints need human compatibility checks
```

Changing the caption status to `TRUNCATED`, omitting verified objects, or reporting
an uncertain identity makes this example return `REVIEW`. A complete scene with
no appropriate changes can return `ABSTAIN` with an empty edit list.

Final `REVIEW` results now have no downstream candidates. Review the original
draft in an audit record rather than treating its rejected edits as actionable.

Run the existing test command above for both captioning and planning checks.
`tests/test_planning.py` covers the mocked food proposal, truncation, unsupported
identities, abstention, malformed responses, and caption-result compatibility.

## Local Ollama planner

The real adapter is `src/transcreation/stages/ollama_planner.py`. It uses Python's
standard HTTP library to call local `/api/chat` with `stream: false`, the existing
planning-result JSON schema, and the generation options in `configs/planner.yaml`.
It does not load SmolVLM or change images. The system instructions are constant;
all input fields are serialized as a separate JSON data message.

Ollama must be installed and running. If the model is missing, install only the
selected model with `ollama pull qwen2.5:3b`. Start `ollama serve` only if the
Ollama service is not already running. The application reports missing service
or model errors rather than downloading anything or inventing a plan.

Run the planner from the project root without changing the Python installation:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B -m transcreation.cli plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/japanese_food_plan.json
```

After the normal editable installation, the equivalent command is:

```powershell
.\.venv\Scripts\transcreate.exe plan --input tests/fixtures/planning/01_japanese_food.json --out outputs/japanese_food_plan.json
```

The input is a user-authored `PlanningInput` JSON file using the schema above.
The food example is a hypothetical fixture with explicitly asserted user
verification, not a newly verified real image. Use a fresh output filename for
each run: the planner refuses to overwrite existing records.

Settings are separate from the VLM: `--config configs/planner.yaml`. Edit its
model, local endpoint, timeout, or generation `options`. The CLI also supports
`--model`, `--endpoint`, and `--timeout` overrides. Defaults are `qwen2.5:3b`,
180 seconds, temperature 0, seed 42, context 4096, output limit 1024, and
`keep_alive: 0`. These aid repeatability but do not guarantee identical output
across model digests, Ollama versions, and hardware.

Each output is an audit JSON containing the exact input, system/user messages,
schema, options, resolved installed-model metadata/digest, raw Ollama response,
validated final plan, timing, available token counts, validation outcome, unload
outcome, and initially blank `human_review_notes`. Errors are archived with
`planning_result: null`; the CLI exits with code 2. Connection failure, missing
model, timeout, invalid JSON/schema, interrupted HTTP, empty content, and
non-stop/truncated generation are explicit failures. No fallback plan is generated.

`OllamaPlanner.plan()` returns the model's typed draft. Use
`plan_cultural_edits(request, planner)` for deterministic review rules, or
`planner.record_plan(request)` for both those rules and the audit record.
No keyword blacklist decides uncertainty materiality or detects every injection.
The trust boundary uses separate system/data messages, immutable input references,
schema validation, source-object checks and the absence of automatic edit approval.
A well-formed plan can still contain unsupported cultural reasoning,
wrong scene claims, or a poor adaptation. Human and visual review remain required.

Keep the stages sequential on a 4 GB GPU: finish the separate caption process
and save its result before running Qwen. `keep_alive: 0` requests immediate model
unloading; recorded runs also send an explicit empty-chat unload request,
including after failures. Unload failures are recorded separately. No changes
have been made to the VLM's loading or memory behavior.

### Reproduce the six scenarios

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -B scripts/evaluate_planner.py --out reports/ollama_planner_new_run
```

Choose a new output directory. The runner first performs a standalone Qwen probe,
then runs the six fixtures sequentially. It requires `keep_alive: 0`. Fixtures and
caption provenance are in `tests/fixtures/planning/`; existing VLM evidence is
read-only. Synthetic verification and adversarial additions are explicitly labeled.
No culture-specific substitution is encoded in application logic.

The runner saves each audit JSON, summaries, the environment, probe, and sampled
memory observations. `nvidia-smi` readings include all desktop applications;
Ollama `/api/ps` reports its model allocation. These samples can miss peaks and
are not PyTorch tensor peaks or process RSS. Expected decisions are policy checks,
not automatic cultural-correctness scores. All human-review notes start blank.

The recorded iterations for this milestone are under
`reports/ollama_planner_phase3_20261108*`. Their exact prompts and outputs are
preserved separately, including unsuccessful cultural reasoning. See the final
run's report for actual decisions, runtime, memory, and limitations.

Current evidence: [final-run report](reports/ollama_planner_phase3_20261108_prompt_v3/REPORT.md)
and [six-scenario summary](reports/ollama_planner_phase3_20261108_prompt_v3/summary.json).
Five responses passed structural validation; the injection response was rejected.
The bicycle scene received unnecessary review, and the food proposal still confused
original and edited scene details. These are recorded limitations, not evidence of
cultural correctness. All 41 offline tests passed.

API references: [Ollama chat](https://docs.ollama.com/api/chat) and
[loaded-model memory reporting](https://docs.ollama.com/api/ps).

## Planner consistency review

The latest [before/after report](reports/planner_quality_review_20261108_final/REPORT.md)
records the same three inputs with unchanged model/quantization/generation settings.
All 53 offline tests pass. The bicycle now remains `ABSTAIN`; the food scene also
abstains, while Durga Puja remains `REVIEW`. These decisions are not cultural-quality
scores: the food adaptation was lost, and Durga still contains an inappropriate
candidate suggestion and broken source/localization fields.

The validator checks explicit source labels and ids rather than guessing cultural
facts or classifying arbitrary uncertainty words. Potential preservation overlaps
and missing source labels require review. This can over-flag valid position-only
preservation or synonyms, and it cannot detect every future-scene paraphrase.
Every proposed edit explicitly requires human checks of summary provenance,
localization, cultural suitability and preservation consistency.

No-edit `ABSTAIN` does not require resolving every background doubt or verifying
every caption fact. It authorizes no image change and does not certify the caption.
With an actual edit pending, free-text uncertainty with unresolved relevance remains
conservative `REVIEW`; the current string-only contract cannot reliably infer its
materiality. Raw wording, earlier results and unsuccessful revised-prompt output
are preserved, including the model's remaining errors.

## Decision policy and rejected drafts

The [latest decision-policy report](reports/planner_decision_policy_20261108_final/REPORT.md)
traces input, prompt, generation, contract and postprocessing causes separately.
All 72 offline tests pass, including the existing captioning and transport tests.

Object fields reject placeholders such as `null`, `none` and `N/A`. A nullable
verified id must use actual JSON `null`. Localization is a short object phrase
(at most 16 words / 160 characters); this bound alone does not prove grounding.

Use `OllamaPlanner.record_plan()` or the existing `plan` CLI for the full audit:

- `raw_planning_result` and `response` retain the original generated content.
- `planning_result` is the policy result. `REVIEW` and `ABSTAIN` release no edits.
- `validation.issues` records codes, severity and candidate indices.
- `validation.rejected_candidates` preserves rejected raw proposals and codes.
- `raw_schema_valid` distinguishes raw validity from the final contract's validity.
- `automatically_authorized` is always false, including for a retained `PROPOSE`.

Bad candidates are quarantined instead of returned with a warning. Malformed JSON,
transport failures and missing/malformed top-level fields still produce errors.
A `PROPOSE` with no candidate can resolve only to coded no-action abstention;
the code never invents an edit to repair it. Prior rejection, truncation or
unresolved adaptation context still forces review.

Free-text user instructions are not a machine-verified permission/protection list.
Every pending edit with unresolved user constraints is withheld for review. This
is deliberately conservative, including for some legitimate requests; do not
remove preservation instructions to force a candidate through. Known-source,
verified-object adaptation requests can also require review of an abstention's
target-context rationale. Different cultures alone do not require an edit.

Ordinary no-action abstention has a neutral policy reason and empty edit checks,
without endorsing invented cultural restrictions. Raw reasons and checks remain
unchanged in the audit, with explicit normalization codes. Final reviewed summaries
can still contain unverified model claims and must not be used as visual truth.
