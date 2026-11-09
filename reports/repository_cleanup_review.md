# Repository cleanup review

This was a conservative refactor, not a new planning or image-editing milestone.
No model inference was run. No files, datasets, environments, model caches, or
research archives were moved or deleted. No commit or push was made.

## 1. Baseline and protection

The actual checkout, rather than the historical test count, was inspected first.
Git was clean at commit `434ab23b316157f39a553dc2b2023b029af31689`.
The exact commit and initial status are recorded in
[git_before.json](repository_cleanup_20261108/git_before.json).

Before editing, the cleanup recorded the directory inventory, SHA-256 hashes for
359 existing project/evidence files, source/import inventories, interpreter and
dependency versions, CLI output, and the current test run. Source snapshots were
also kept in a temporary directory outside the working tree during the refactor.
No pre-existing uncommitted changes were present to overwrite.

The tested interpreter is `.venv/Scripts/python.exe`, Python **3.11.9** on Windows.
The shell's `python` command resolves to a WindowsApps alias, so verification used
the explicit virtual-environment interpreter and `PYTHONPATH=src`.
`VIRTUAL_ENV` was unset; this does not change which explicit interpreter was used.
The virtual environment depends on `.python311/tools`; both were left intact.

Recorded package versions: torch `2.15.0+cu132`, transformers `4.57.6`, Pillow
`13.0.0`, PyYAML `6.0.3`, setuptools `78.1.0`, pip `26.3`, and this project `0.1.0`.
See [environment_before.json](repository_cleanup_20261108/environment_before.json).

## 2. Before and after structure

The source layout and existing experiment paths are deliberately unchanged.
The trees below omit virtual-environment internals and list experiment bundles as
directories; the linked inventories contain the detailed paths.

Before:

```text
MiniProject/
|-- configs/                       models.yaml, planner.yaml, existing bytecode
|-- src/transcreation/
|   |-- __init__.py, cli.py, config.py, contracts.py, pipeline.py
|   `-- stages/
|       |-- __init__.py, caption.py, planning.py, ollama_planner.py
|       `-- grounding.py, segmentation.py, inpainting.py (docstring-only stubs)
|-- scripts/evaluate_planner.py
|-- tests/                         four test modules and planning fixtures
|-- data/                          sample_images/ and vlm_collection/
|-- outputs/                       generated captions/plans and planner_review.md
|-- reports/
|   |-- VLM_Selection_Experimental_Findings_Refined.md
|   `-- eight existing planner experiment bundles
|-- .local_archive/                four historical directories and two summaries
|-- README.md                      long, overlapping historical guides
|-- pyproject.toml, .gitignore
`-- local environment/editor/generated files and ignored sayan.md
```

After:

```text
MiniProject/
|-- configs/                       unchanged
|-- src/transcreation/             same modules and import paths
|-- scripts/evaluate_planner.py     unchanged
|-- tests/                         same 72 tests and unchanged fixtures
|-- data/                          unchanged
|-- outputs/                       unchanged
|-- reports/
|   |-- README.md                  new index of existing evidence
|   |-- repository_cleanup_review.md
|   |-- repository_cleanup_20261108/ baseline and verification records
|   `-- all previous findings and experiment bundles (unchanged)
|-- .local_archive/                unchanged
|-- README.md                      concise current installation and usage guide
`-- pyproject.toml, .gitignore and local runtime/editor files (unchanged)
```

[Before inventory](repository_cleanup_20261108/tree_before.json) and
[after inventory](repository_cleanup_20261108/tree_after.json).
No separate `smolvlm.py` shim was introduced: the working adapter already lives in
`stages/caption.py`. `pipeline.py` remains because CLI and tests use its entry points.

## 3. Audit classification and retained files

The [per-file classification](repository_cleanup_20261108/file_classification.json)
covers all 359 baseline files. Classes are KEEP, REFACTOR, ARCHIVE, DELETE CANDIDATE,
and NEEDS REVIEW. ARCHIVE means already archived, not newly moved.

| Area | Classification and action |
| --- | --- |
| Caption implementation, CLI, contracts, YAML settings | KEEP; byte-identical |
| `pipeline.py` | REFACTOR documentation only; used entry points retained |
| Planner adapter/validator | REFACTOR only the two proven duplications below |
| Tests and fixtures | KEEP, except one unused test import; no test semantics or fixture values changed |
| `scripts/evaluate_planner.py` | KEEP; the only active research utility, still needed for reproducible evaluation |
| Data, outputs, reports and archive evidence | KEEP or already ARCHIVE; no paths or content changed |
| `pyproject.toml` and `.gitignore` | KEEP; no packaging, dependency, ignore or entry-point configuration changes |
| Existing future-stage stubs | NEEDS REVIEW; retained to preserve referenced paths |
| Ignored user notes and partial dataset manifest | NEEDS REVIEW; retained as user/research work |
| Generated Python bytecode outside the archive | DELETE CANDIDATE only; left untouched |

Static import/use inspection found one unreferenced imported name: `asdict` in
`tests/test_planning_policy.py`. No remaining unused-import candidates were found
by the same scan after cleanup. Name scanning is not proof about reflection or
external callers; call sites and tests were inspected as well.

The public `edit_consistency_issues()` diagnostic has no active internal caller,
but was retained for import compatibility. The large validator's ordered safety
branches were not split up: issue ordering, explanations and candidate quarantine
are observable behavior. Caption loader options and config defaults were retained;
their apparent repetition expresses fallback/validation and reproducibility policy.
CLI progress/output statements are intentional, not temporary debug prints.

## 4. Meaningful refactors and why they preserve behavior

| Change | What was confusing/redundant | Simplification and evidence |
| --- | --- | --- |
| `_contains_label()` in `planning.py` | Repeated the same case-folding, regex tokenization and tuple conversion already defined by `_normalized_label()` | Calls the existing pure helper for text and label, in the same order. Matching, schema and decisions are unchanged; all tests and full audit replays match. |
| Timeout handling in `ollama_planner.py` | Checked both `TimeoutError` and `socket.timeout`, then imported socket solely for that alias | On the required/tested Python 3.11 runtime, `socket.timeout is TimeoutError` is true. Uses `TimeoutError` once in both checks and removes the now-unneeded import. Existing direct/wrapped timeout tests pass. |
| Test import | Imported `asdict` without using it | Removes that import only; all 72 tests remain present and pass. |
| Module/function docstrings | Config documentation mentioned only captioning; a caption wrapper implied all later work was unimplemented | Clarifies separate caption/planner settings and the independently invoked planner. No executable logic changed in these files. |
| README and report index | Repeated historical milestones, mixed current instructions with older results, and used the old `data/durga.jpg` path in commands | Replaced the main guide with current responsibilities/commands, corrected the example to `data/sample_images/durga.jpg`, and indexed existing findings. No evidence was rewritten. |

The docstring-only changes are in `config.py`, `pipeline.py`, and `stages/__init__.py`.
No model loading/generation/preprocessing code or safety-rule branch was rewritten.

## 5. Files moved, archived, or proposed for deletion

**Moved: none. Newly archived: none. Deleted: none.**

The three existing `grounding.py`, `segmentation.py` and `inpainting.py` modules
contain only future-work docstrings. No Python call sites import them, but ignored
user notes reference their paths. Removing them would remove existing import/file
paths, so they remain flagged for review. They are not presented as implemented
stages, and no new Grounding DINO, SAM, diffusion or other placeholders were created.

Generated Python bytecode outside the historical archive is a possible later
deletion candidate. It is not a model cache and was not removed here. The bootstrap
package, virtual environments, editor state, installed metadata, and ignored
`sayan.md` are not cleanup targets without a separate ownership/compatibility decision.
See [review_candidates.json](repository_cleanup_20261108/review_candidates.json).

## 6. Research evidence and backup status

All pre-existing research/dataset/output files retained their exact bytes and paths.
The cleanup found **65 duplicate-content groups** among evidence files. Identical
captions, inputs or code can belong to distinct prompt/settings/timing trials; hash
identity alone was not used to discard an experiment. Historical BLIP/Florence code
and experimental scripts remain in `.local_archive/`, not the active application.

The [report index](README.md) links the latest planner validation, VLM selection,
saved VLM outputs, token-ceiling and concise-prompt evidence, audit records and
fixture provenance. Raw artifacts already bundled in `reports/` were not moved to
`outputs/`: that would disturb evidence links and recorded provenance for no
behavior-preserving benefit.

**No independent backup of `.local_archive/` was verified.** Git ignores that
directory and tracks none of its files. The tracked VLM findings summarize only
part of its content. Local hashes, source snapshots, and Git history of tracked
reports are not an independent backup of the raw archive. Treat it as having no
verified independent backup; no historical results were deleted or relocated.

The baseline link scan found **35 broken relative references**, all in three
historical archive Markdown files: `smol_concise/concise_review.md` (11),
`smol_extended/review.md` (11), and `vlm_comparison/review.md` (13). They refer to
an old layout and were not edited inside evidence. The corresponding current
image locations are `data/sample_images/durga.jpg` and `data/vlm_collection/`.
The new/current documentation links are checked separately. These are pre-existing
archive reference problems, not introduced cleanup regressions.
See [link findings](repository_cleanup_20261108/links_before.json) and
[duplicate groups](repository_cleanup_20261108/duplicates_before.json).

## 7. Regression and CLI checks

| Check | Before | After |
| --- | --- | --- |
| Existing offline suite | 72 passed, 0 failures, 0.475 s reported test time | 72 passed, 0 failures, 0.252 s |
| Source `--help` | exit 0 | identical text and exit 0 |
| Source `caption --help` | exit 0 | identical text and exit 0 |
| Source `plan --help` | exit 0 | identical text and exit 0 |
| Source `--version` | exit 0 | identical text and exit 0 |
| Installed `transcreate.exe --help` | exit 1: missing `main` | identical pre-existing failure |
| `pip check` | no broken requirements | no broken requirements |

The evaluation utility's `--help` also exits 0; its file is byte-identical, and its
real-model execution path was not run. Test-time differences are ordinary run
variation, not a performance claim.

The generated local launcher still points to `main:main`, although pyproject
correctly declares `transcreation.cli:main`. No editable reinstall or manual
metadata patch was performed, preserving the environment. The README provides the
verified source-module command and explains normal editable installation.

Offline compatibility verification also compared **33 full saved-response audit
replays** and **six planning fixtures** before/after. HTTP was mocked; time and audit
timestamps were fixed solely inside the verifier. Full final records, HTTP request
bodies, schema, prompts, generation/config settings, decisions, issue codes and
candidate quarantine matched exactly. Historical error outcomes were preserved.
All final REVIEW/ABSTAIN candidates in these replays remain empty; no automatic
authorization appeared. Positive conditional PROPOSE and transport failures remain
covered by the existing suite.

SmolVLM and Ollama modules imported successfully; actual configs validated.
`stages/caption.py`, `contracts.py`, `cli.py`, both YAML files, and model/inference
constants were unchanged. No checkpoint, prompt, seed, precision, processor setting,
schema field name, or serialization policy was changed.

Detailed records: [tests before](repository_cleanup_20261108/tests_before.json),
[tests after](repository_cleanup_20261108/tests_after.json),
[CLI before](repository_cleanup_20261108/cli_before.json),
[CLI after](repository_cleanup_20261108/cli_after.json), and
[offline verifier](repository_cleanup_20261108/compatibility_check.py).

## 8. Git diff and dependencies

Seven tracked files were modified: README, five application files (two tiny logic
deduplications and three docstrings), and the test file's unused import. New files
are documentation and cleanup evidence only; no new active module, interface,
dependency or feature was introduced. The exact final diff is saved in
[cleanup_changes.diff](repository_cleanup_20261108/cleanup_changes.diff), with
[Git status](repository_cleanup_20261108/git_after.json).

No dependency changes were necessary. torch, transformers, Pillow and PyYAML are all
used; setuptools remains the build backend. The project file and environment were
left unchanged, and no packages were installed, upgraded or removed.

## 9. Remaining issues and limits of verification

- The installed local console launcher is stale. Its existing failure is documented;
  module invocation works. Refreshing generated installation state is outside this
  behavior-preserving source cleanup.
- Existing future-stage import paths and the public unused diagnostic are retained
  for compatibility. Their eventual removal needs review; no external caller search
  can be exhaustive from this checkout.
- The archive has no verified independent backup and retains 35 old broken relative
  image references. No claim is made that its historical manifests are complete or
  that a remote backup exists.
- Existing planner limitations remain: unverified image/cultural claims, conservative
  treatment of free-text constraints, and lack of semantic proof. No safety rule or
  reviewed/rejected-candidate handling was weakened to make cleanup pass.
- No live Ollama calls, weight downloads, GPU inference, grounding, segmentation or
  inpainting were run. Offline equality and unchanged inference source/settings do
  not claim new live-model, GPU-memory, network or runtime-performance equivalence.
- Complete cultural transcreation remains unimplemented. Grounding DINO is the next
  planned feature, not part of this cleanup.
