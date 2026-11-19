# Overleaf report source

Compile `main.tex` with **pdfLaTeX**, **BibTeX**, then pdfLaTeX twice. The included `latexmkrc` selects pdfLaTeX automatically. This is the canonical IEEEtran path and avoids the XeLaTeX/fontspec font-shape conflict.

`experiments/scripts/build_phase9_data.py` reads the saved Phase 9 verifier output and generates the CSV used by the PGFPlots chart. From the repository root:

```powershell
.venv\Scripts\python.exe mini-project-report\experiments\scripts\build_phase9_data.py
```

The source tree is self-contained for Overleaf. `evidence-and-review.md` maps report claims to raw evidence. Before institutional submission, replace the cover and certificate fields because no institute template, supervisor details, or formal wording were present in the project.
