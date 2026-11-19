# Final submission reproduction

Extract this ZIP and work from its root. Install Python 3.11 and the recorded dependencies.
For same-environment PNG hashes use Pillow 13.0.0 / LittleCMS 2.19.

```powershell
python -m pip install -e ".[inpainting]"
$env:PYTHONPATH = (Resolve-Path src).Path
python -B -m scripts.appearance_transfer --refined-input results/phase7_integration/v4_completed/reproduce_input_A.json --out outputs/appearance_reproduction
python -B results/appearance_transfer_baseline/verify_saved.py
$env:HF_HUB_OFFLINE = "1"
python -B -m unittest discover -s tests -v
```

No model weights or Ollama are needed for the classical run. Compare the reproduced final PNG SHA-256 against `results/appearance_transfer_baseline/pixel_verification.json`. Never rerun into existing output folders. The verification script reopens the INCLUDED saved baseline; the reproduction hash check is separate.

The request's old positive prompt is immutable diffusion provenance and is ignored by the classical treatment. Numerical settings are frozen in the appearance module and recorded before processing. No review authorization is inferred.

Original source: Spaghetti aglio e olio, 10Rosso, CC BY 2.0. See included attribution. Appearance/diffusion/comparison images are modified derivatives, no endorsement implied.

The current baseline is more structurally coherent but FAILS the full masala-coating objective. Historical SD A/B FAIL. Automated planning remains REVIEW/zero released candidates. No new models ran in stabilization.

The submission contains selected real V4 A/B final/raw/processing files and metadata, not duplicate historical ZIPs or every duplicate evidence copy. Unchanged full SAM/localization/automated bundles establish baseline provenance. `inpainting.json` also records hashes of duplicate diffusion evidence copies not all repeated here; original complete V4 evidence remains preserved locally and in the prior V4 review ZIP. Old path strings are retained for audit; baseline reproduction uses the included normalized request and local SAM bundle rather than those historical paths.

The historical human decision summary is not a new review. All original private ramen evidence remains unchanged locally. No archived reviewer decision has been cleared.
