# Reproduction guide

All commands run from the **repository root** in Windows PowerShell, and were executed on
2026-11-12 (Windows 11, Python 3.11.9, Pillow 13.0.0, NumPy 2.4.6). Every output directory
must be **new**: the tools refuse to overwrite earlier results.

## 1. Setup

```powershell
python --version                      # must print Python 3.11.x
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If `python` opens the Microsoft Store, install Python 3.11 from python.org (or call it by
full path). After activation, `python` is the venv interpreter.

### A. CPU-only (enough for the six-case pilot and the samosa reproduction)

```powershell
python -m pip install "Pillow>=10" "numpy>=1.26"
```

No GPU, no model weights, no Ollama, no network. `scripts.pilot` finds `src/` by itself.
(`opencv-python-headless` was used once, historically, to prepare some masks; replay does not need it.)

### B. Full project (model stages)

Install a PyTorch build that matches your machine first (check
<https://pytorch.org/get-started/locally/>; do not guess the CUDA version, see
`nvidia-smi`). The development laptop used `torch 2.15.0+cu132` on an RTX 3050 4 GB. Then:

```powershell
python -m pip install -e ".[inpainting]"
$env:PYTHONPATH = (Resolve-Path src).Path
```

Model weights download from Hugging Face on first use, pinned in `configs/`:
SmolVLM-500M-Instruct (`configs/models.yaml`, revision pinned), Grounding DINO Tiny
(`configs/grounding.yaml`), SAM ViT-Base (`configs/sam.yaml`), and SD v1.5 Inpainting
(`configs/inpainting.yaml`). Live planning needs [Ollama](https://ollama.com) running locally
with `ollama pull qwen2.5:3b`. Models load one at a time and fit in 4 GB VRAM.

## 2. Six-case repeatability pilot (CPU)

```powershell
python -B -m scripts.pilot validate --manifest configs/phase9_pilot_cases.json
python -B -m scripts.pilot run --manifest configs/phase9_pilot_cases.json --out results/phase9_pilot/run_001
python -B -m scripts.pilot verify --run results/phase9_pilot/run_001
python -B -m scripts.pilot package --run results/phase9_pilot/run_001 --out results/repeatability_pilot_review.zip
```

`run_001` and the ZIP already exist in this repository, so to reproduce them use new names,
e.g. `--out results/phase9_pilot/run_002` and `--out results/my_review.zip`.
Exit codes: `0` ok, `1` project-level error (bad manifest, existing output, verification
failure), `2` the run finished but a case failed (failures are saved in `CASE_xx/status.json`).

| Step | What it checks or does | Measured time (CPU) |
|---|---|---|
| validate | schema, six IDs, directions, licence fields, every image/request SHA-256, attempt budget, no review decision without verbatim user feedback | under 1 s |
| run | copies CASE_01 unchanged; executes the 8 frozen attempts of CASE_02..06; builds review images | about 20 s |
| verify | reopens every file; re-hashes inputs and outputs; locality, protected pixels, leftover-source check, in-memory deterministic replay, historical byte/pixel equality | about 27 s |
| package | runs verify again, writes ZIP plus `SHA256SUMS.txt`, reopens the ZIP and checks every hash | about 31 s |

## 3. Reproduce the original samosa result (CASE_01)

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -B -m scripts.reference_replacement --request results/phase8_cultural_validation/true_object_replacement/request_B.json --output results/phase8_cultural_validation/true_object_replacement/reproduction_B_new
```

Compare the new output with the frozen `B/final.png`. Decoded pixels are what matter: PNG
bytes may differ with another Pillow/zlib version even when pixels are identical.

```powershell
python -B -c "from PIL import Image; import numpy as np; d='results/phase8_cultural_validation/true_object_replacement/'; a=np.asarray(Image.open(d+'B/final.png').convert('RGB')); b=np.asarray(Image.open(d+'reproduction_B_new/final.png').convert('RGB')); print('pixels identical:', (a==b).all())"
```

On 2026-11-12 this gave identical pixels **and** identical bytes (`reproduction_B_phase9/`).

## 4. Tests

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$env:HF_HUB_OFFLINE = "1"
python -B -m unittest discover -s tests -v                                    # full suite (needs setup B)
python -B -m unittest tests.test_pilot tests.test_reference_replacement -v    # pilot only (setup A is enough)
```

Result on 2026-11-12: **482 tests, 0 failures, 0 errors** (451 earlier tests + 31 new pilot tests).
Log: `results/phase9_pilot/tests_full.log`. All tests are offline, using synthetic or mocked data.

## 5. Optional model stages (setup B; separate from the pilot)

```powershell
python -B -m transcreation.cli --help
python -B -m transcreation.cli caption --image path\to\photo.jpg --out outputs\caption.json
python -B -m transcreation.cli plan --input path\to\planning_input.json --out outputs\plan.json      # needs Ollama + qwen2.5:3b
python -B -m transcreation.cli ground --image path\to\photo.jpg --phrase "croissant" --out outputs\ground.json
python -B -m scripts.segment_sam --help
python -B -m scripts.inpaint --help
python -B -m transcreation.cli run --input path\to\request.json
```

`plan` never edits images. REVIEW/ABSTAIN plans cannot dispatch edits; guided research uses
its own explicit specification and never promotes a rejected plan.

## 6. Reviewing the pilot

Open `results/phase9_pilot/run_001/overview.jpg`, then, per case, `CASE_xx/comparison.jpg`,
`CASE_xx/closeup_native.png`, `CASE_xx/attempts.jpg` (if there were two attempts) and
`CASE_xx/REVIEW.md`. Cases 02–06 are `PENDING_USER_REVIEW`. Record a user's answer only as
their own words, in `human_feedback` (with an evidence file) in the manifest. `validate`
rejects any PASS/FAIL that has no such evidence.

## 7. Using the review ZIP elsewhere

Unzip it into an empty folder and run the same section 2 commands there with new output names.
Paths inside are repository-relative, so validate/run/verify work from the unzipped folder.
The historical outputs are not duplicated in the ZIP: verify compares against their recorded
SHA-256 instead.
