"""Run an explicitly frozen RESEARCH_ONLY reference-compositing request."""
import argparse
import json
from transcreation.stages.reference_replacement import run_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run_request(args.request, args.output), indent=2))


if __name__ == "__main__":
    main()
