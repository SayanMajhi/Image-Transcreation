# Image-Transcreation

Image-Transcreation is a research project for a modular pipeline that adapts
images to a target cultural context while preserving their meaning and visual
content. The Python distribution is named `culture-transcreation`.

The research direction is inspired by Khanuja et al. (EMNLP 2024).
This initial setup makes no claims about benchmark results or research improvements.

## Planned architecture

1. Image captioning with a VLM such as Florence-2 or BLIP.
2. Cultural substitution planning with an LLM.
3. Object localization with Grounding DINO.
4. Segmentation with SAM.
5. Localized editing with diffusion inpainting.
6. Evaluation of semantic equivalence, cultural relevance, and visual preservation.

**ML inference is not yet implemented.** This repository currently contains only
package setup and a minimal CLI. No models or ML runtime dependencies are installed.

## Setup (Windows PowerShell)

Requires Python 3.11 and Git. Run commands from the project root.

```powershell
py -3.11 --version
git --version

# Create the environment only if it does not already exist.
if (-not (Test-Path .venv)) {
    py -3.11 -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
python -m pip install -e .
```

For this workspace, a portable Python 3.11.9 was downloaded from the Python
NuGet package into the ignored `.python311/` directory because the system launcher
only had Python 3.12. Keep that directory while using the environment. To recreate
`.venv` from that interpreter, use the following instead of `py -3.11 -m venv`:

```powershell
if (-not (Test-Path .venv)) {
    .\.python311\tools\python.exe -m venv .venv
}
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python` and `.\.venv\Scripts\transcreate.exe` in place of `transcreate` below.
Activation is optional; no execution policy change is required.

## Verify

```powershell
python --version
python -c "import sys; print(sys.executable)"
git rev-parse --show-toplevel
python -m pip install -e .
transcreate --version
transcreate
```

Expected: Python 3.11.x, the `.venv` interpreter, the project repository root,
`transcreate 0.1.0`, and `Culture Transcreation CLI is ready.`

## Layout

- `configs/`: future configuration files.
- `data/`: local datasets (ignored except `.gitkeep`).
- `outputs/`: generated files (ignored except `.gitkeep`).
- `src/transcreation/`: package and CLI, with a namespace for future stages.
- `tests/`: reserved for tests as functionality is implemented.

Editable installation installs the package and CLI without ML dependencies.
Data, outputs, model files, secrets, IDE settings, and local environments are
excluded from Git. This completes Phase 2, Step 1 only.
