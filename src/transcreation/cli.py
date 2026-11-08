"""Command-line entry point for culture transcreation."""
import argparse
from dataclasses import asdict, replace
import hashlib
from importlib.metadata import version
from io import BytesIO
import json
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "models.yaml"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Culture transcreation research CLI.")
    parser.add_argument("--version", action="version",
                        version=f"transcreate {version('culture-transcreation')}")
    commands = parser.add_subparsers(dest="command")
    caption = commands.add_parser("caption", help="Caption one image with SmolVLM-500M")
    caption.add_argument("--image", type=Path, required=True)
    caption.add_argument("--model", choices=("smolvlm",))
    caption.add_argument("--prompt-variant", choices=("default", "concise_grounded"))
    caption.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    caption.add_argument("--out", type=Path, default=Path("outputs/caption.json"))
    args = parser.parse_args(argv)
    if args.command is None:
        print("Culture Transcreation CLI is ready.")
        return

    from PIL import Image, UnidentifiedImageError
    from transcreation.config import load_config
    from transcreation.pipeline import run_caption

    try:
        if not args.image.is_file():
            raise FileNotFoundError(f"Image not found: {args.image}")
        if args.image.resolve() == args.out.resolve():
            raise ValueError("--out must differ from the input image path")
        if args.config.resolve() == args.out.resolve():
            raise ValueError("--out must differ from the configuration path")
        config = load_config(args.config, args.model)
        if args.prompt_variant is not None:
            config = replace(config, prompt_variant=args.prompt_variant)
        image_bytes = args.image.read_bytes()
        # Decode exactly the bytes hashed, rather than reopening a potentially changed file.
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.convert("RGB")
        result = run_caption(image, config)
        record = {
            **asdict(result),
            "input_sha256": hashlib.sha256(image_bytes).hexdigest(),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError, ImportError, UnidentifiedImageError) as exc:
        parser.error(str(exc))
    print(result.caption)
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
