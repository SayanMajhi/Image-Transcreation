# Targeted visual improvement reproduction

This is a new, explicitly guided RESEARCH_ONLY correction. Read the pre-generation diagnosis, user feedback and frozen A/B conditions. Old Qwen REVIEW and historical decisions are not approvals. No new VLM/Qwen/DINO/SAM calls are needed.

Use the recorded Python 3.11 / Diffusers 0.35.2 / Transformers 4.57.6 environment and existing cached pinned SDXL + Canny safetensors. No new weights are in this ZIP. Use original-region masks, source and Canny PNGs exactly as supplied. Run from the extracted package/repository root, with a fresh output directory:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
$env:HF_HUB_OFFLINE = "1"
python -B -m scripts.instruction_edit --input results/phase8_cultural_validation/visual_improvement/reproduce_request_A.json --config results/phase8_cultural_validation/visual_improvement/config_A.json --out outputs/visual_improvement_A_reproduction
python -B results/phase8_cultural_validation/visual_improvement/verify_outputs.py
python -B -m unittest discover -s tests -v
```

The verifier checks the included saved outputs. For a fresh reproduction, independently reopen the new PNG and compare source RGB at every outside-mask/protected pixel. GPU bitwise identity across systems is not guaranteed. The two-generation budget applies to this research execution; no third generation is run for packaging. If B was executed, its request/config and single-variable preregistration are included; use the same CLI with their paths and another fresh directory.

Current experiments deliberately change multiple conditions relative to the old seed43 (geometry, region/crop, prompt); no isolated-cause claim is valid. Canny only carries edges, not the prototype's shading or measured depth. Direct chat review of new outputs is pending, not a fabricated panel of three.
