"""Extract selected Phase 9 measurements from the saved verifier result."""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "results" / "phase9_pilot" / "run_002" / "verification_summary.json"
OUT = ROOT / "mini-project-report" / "experiments" / "results" / "phase9_selected.csv"

with SOURCE.open(encoding="utf-8") as handle:
    report = json.load(handle)
rows = []
for case in report["cases"]:
    if case["id"] == "CASE_01":
        continue
    selected = case["selected_attempt"]
    attempt = next(item for item in case["attempts"] if item["attempt"] == selected)
    checks = attempt["checks"]
    rows.append({"case": case["id"].split("_")[1], "changed_inside_millions": round(checks["changed_inside"] / 1_000_000, 6), "permitted_millions": round(checks["permitted_pixels"] / 1_000_000, 6), "outside_changed": checks["changed_outside"], "protected_changed": checks["protected_changed"]})
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)
print(f"wrote {OUT} from {SOURCE}")
