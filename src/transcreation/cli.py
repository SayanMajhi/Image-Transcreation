"""Command-line entry point for culture transcreation."""

import argparse
from importlib.metadata import version


def main() -> None:
    """Parse command-line arguments and report readiness."""
    parser = argparse.ArgumentParser(description="Culture transcreation research CLI.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('culture-transcreation')}",
    )
    parser.parse_args()
    print("Culture Transcreation CLI is ready.")


if __name__ == "__main__":
    main()
