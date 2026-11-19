"""Phase 9 six-case repeatability pilot (REFERENCE_GUIDED_COMPOSITING, CPU only).

  python -B -m scripts.pilot validate --manifest configs/phase9_pilot_cases.json
  python -B -m scripts.pilot run      --manifest configs/phase9_pilot_cases.json --out results/phase9_pilot/run_001
  python -B -m scripts.pilot verify   --run results/phase9_pilot/run_001
  python -B -m scripts.pilot package  --run results/phase9_pilot/run_001 --out results/repeatability_pilot_review.zip

Exit codes: 0 success, 1 project-level error (invalid manifest, existing output,
verification failure), 2 run finished but at least one case failed.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from transcreation import pilot
except ModuleNotFoundError:  # allow running from a checkout without PYTHONPATH/pip install
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from transcreation import pilot


def _print(obj):
    print(json.dumps(obj, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -B -m scripts.pilot", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("validate", help="Check schema, provenance, hashes and attempt budget")
    p.add_argument("--manifest", required=True)
    p = sub.add_parser("run", help="Execute all cases into a NEW output directory")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("verify", help="Independently reopen and re-check a run")
    p.add_argument("--run", required=True)
    p = sub.add_parser("package", help="Verify, then build a SHA-256-manifested review ZIP")
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            _print(pilot.validate_manifest(args.manifest))
            return 0
        if args.command == "run":
            summary = pilot.run_pilot(args.manifest, args.out)
            _print(summary)
            return 2 if summary["failed_cases"] else 0
        if args.command == "verify":
            summary = pilot.verify_run(args.run)
            _print({"result": summary["result"], "failures": summary["failures"],
                    "cases": [{"id": c["id"], "result": c["result"], "selected": c["selected_attempt"],
                               "human_review": c["human_review_status"]} for c in summary["cases"]],
                    "written": str(Path(args.run) / pilot.VERIFICATION)})
            return 0 if summary["result"] == "PASS" else 1
        summary = pilot.package_run(args.run, args.out)
        _print(summary)
        return 0 if summary["verification"] == "PASS" and summary["package_check"]["result"] == "PASS" else 1
    except pilot.ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (FileExistsError, FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
