# Reproduce the independent guided replacement

This is **REFERENCE_GUIDED_COMPOSITING / RESEARCH_ONLY**, with no generative model, no autonomous cultural inference and no approval of the historical Qwen REVIEW. Reference cutout and derived comparisons are CC BY-SA4.0; see LICENSE_AND_ATTRIBUTION.md.

Python3.11, Pillow13.0.0, NumPy2.4.6 are sufficient for replay. OpenCV5.0.0.93 was used only to refine the stored extraction mask. No models or GPU are needed. The supplied original selection and corrected selection masks are immutable source-bound experiment inputs; no extraction algorithm rerun is required to reproduce B. annotation.json and correction_B.json record their origins.

From the repository root (PowerShell):
```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
.venv/Scripts/python.exe -B -m scripts.reference_replacement --request results/phase8_cultural_validation/true_object_replacement/request_B.json --output results/phase8_cultural_validation/true_object_replacement/reproduction_B
.venv/Scripts/python.exe -B results/phase8_cultural_validation/true_object_replacement/verify_result.py
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```
Output must be a NEW directory; prior outputs cannot be overwritten. Reproduction is a deterministic replay of the frozen composite, not a new condition. Compare reproduced PNG bytes/hashes against B/execution.json.

The review ZIP retains repo-relative paths. Unzip to a fresh directory, use its included src/scripts, and run the same module command with your Python3.11 interpreter. The focused test can run with `python -m unittest discover -s tests -p test_reference_replacement.py -v`. The complete 451-test suite is recorded from the original repository, not bundled wholesale.

A used the same scale, position, white reconstruction and shadow. B changes reference extraction only; its explicit reference_box equals the implicit A crop. Full white reconstruction is justified only for this inspected isolated white-background photograph. It must not be assumed suitable for arbitrary scenes. The soft contact shadow is manually modeled; no physical illumination recovery is claimed.
