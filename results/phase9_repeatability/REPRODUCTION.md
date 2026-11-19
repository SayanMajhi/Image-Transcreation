# Reproduce the six-case pilot

Method: **REFERENCE_GUIDED_COMPOSITING / RESEARCH_ONLY**. No new model inference is needed. Existing captioning/planning/approval routes remain separate and unchanged.

Environment: Python3.11.9, Pillow13.0.0, NumPy2.4.6. OpenCV5.0.0.93 was used for preflight source envelopes and the stored fedora-B mask. Model weights and GPU are unnecessary for replay. Exact original images, reference selections, permits and protected masks are supplied, along with frozen requests and hashes. Replay uses those saved masks, not a new segmentation prediction.

From the repository root (PowerShell):
```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.venv/Scripts/python.exe -B -m scripts.reference_replacement --request results/phase9_repeatability/case2/request_A.json --output results/phase9_repeatability/case2/replay_A
.venv/Scripts/python.exe -B -m scripts.reference_replacement --request results/phase9_repeatability/case3/request_B.json --output results/phase9_repeatability/case3/replay_B
.venv/Scripts/python.exe -B -m scripts.reference_replacement --request results/phase9_repeatability/case4/request_A.json --output results/phase9_repeatability/case4/replay_A
.venv/Scripts/python.exe -B -m scripts.reference_replacement --request results/phase9_repeatability/case5/request_B.json --output results/phase9_repeatability/case5/replay_B
.venv/Scripts/python.exe -B -m scripts.reference_replacement --request results/phase9_repeatability/case6/request_A.json --output results/phase9_repeatability/case6/replay_A
.venv/Scripts/python.exe -B results/phase9_repeatability/validate_pilot.py
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```
Output directories must be NEW; historical results cannot be overwritten. Case3/5 primary A requests are also included for reproduction of the observed defects. Case1 is the unchanged historical baseline, copied with byte checks, not a new experiment. Its existing B request and full reference provenance are included under the original phase8 paths.

The ZIP uses repository-relative paths. Unzip to a fresh directory and use its src/scripts with your Python3.11 interpreter. Its included reference-replacement tests can be run using `python -m unittest discover -s tests -p test_reference_replacement.py -v`. Full451-test logs are from the project-local suite; unrelated application tests are not bundled wholesale.

The source/background assumptions are strong: these are isolated product photos. A component-based envelope plus explicit placement removes the original object and local shadow; the reference is placed at a manually fixed uniform scale and position. Native reference photo patches retain their own studio background/shadow, so exact foreground matting and physical relighting are not claimed. All original pixels outside each declared region are restored exactly.

For human review, open caseN/comparison.jpg then native_closeup.png. A simple chat response such as `Case2 looks natural` or `Case5 looks pasted because the shadow is detached` is enough. No scores or technical form is required.
