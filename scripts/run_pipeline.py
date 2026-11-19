"""Run planning, reviewed grounding tests, or read-only research replay; never generate."""
import argparse
import json
from pathlib import Path

from transcreation.contracts import VerifiedObject
from transcreation.orchestration import IntentReference, PipelineInput, PipelineState, ReplayChain, run_pipeline


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        values = json.loads(args.input.read_text(encoding="utf-8"))
        if values.get("replay") is not None:
            values["replay"] = ReplayChain(**values["replay"])
        if values.get("edit_intent") is not None:
            values["edit_intent"] = IntentReference(**values["edit_intent"])
        values["verified_objects"] = tuple(VerifiedObject(**item) for item in values.get("verified_objects", []))
        result = run_pipeline(PipelineInput(**values))
    except (OSError, TypeError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(f"{result.state}: stopped at {result.stopped_at}; generation permitted: {result.image_generation_permitted}")
    if result.state == PipelineState.FAILED:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
