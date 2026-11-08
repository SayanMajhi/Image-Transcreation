# Culture transcreation

This project currently describes images using SmolVLM-500M. It prints a caption
and saves the caption plus run details to JSON. Cultural planning and image
editing are future stages.

## Structure

```text
MiniProject/
|-- configs/
|   `-- models.yaml          Model settings you can edit
|-- data/
|   `-- sample_images/       Place new input images here
|-- src/
|   `-- transcreation/
|       |-- __init__.py      Marks the Python package
|       |-- cli.py           Reads commands, opens images, saves results
|       |-- config.py        Reads and validates models.yaml (only config.py)
|       |-- contracts.py     Defines the caption interface and result format
|       |-- pipeline.py      Selects CPU/GPU and runs captioning
|       `-- stages/
|           |-- __init__.py  Marks the stages package
|           |-- caption.py   Loads SmolVLM and generates image descriptions
|           |-- planning.py  Future: decide cultural adaptations
|           |-- grounding.py Future: locate objects to adapt
|           |-- segmentation.py Future: create masks for those objects
|           `-- inpainting.py Future: edit masked regions
|-- tests/                   Offline checks using a mocked model
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

The other four stage files are documented placeholders. They do not run yet.

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
