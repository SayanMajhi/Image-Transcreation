"""Independent SAM research CLI; run as a module from the repository root."""
import argparse
from dataclasses import replace
from pathlib import Path

from transcreation.config import load_sam_config
from transcreation.stages.segmentation import SamSegmenter, load_segmentation_input


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--image-sha256")
    parser.add_argument("--detection", type=Path, required=True)
    parser.add_argument("--prediction-index", type=int)
    parser.add_argument("--points", type=Path, help="Optional source-bound research point JSON; coordinates stay in original pixels")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--research-only", action="store_true")
    mode.add_argument("--review", type=Path)
    parser.add_argument("--note", required=True, help="Why this exact source box is being tested")
    parser.add_argument("--config", type=Path, default=Path("configs/sam.yaml"))
    parser.add_argument("--device", choices=("cuda", "cpu"))
    parser.add_argument("--out", type=Path, required=True, help="New artifact directory only")
    args = parser.parse_args(argv)
    segmenter = None
    try:
        config = load_sam_config(args.config)
        if args.device:
            config = replace(config, device=args.device)
        request = load_segmentation_input(args.image, args.detection, args.prediction_index,
                                          args.research_only, args.review, args.note, args.image_sha256, args.points)
        segmenter = SamSegmenter(config)
        result = segmenter.segment(request, args.out)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, ImportError) as exc:
        parser.error(str(exc))
    finally:
        if segmenter:
            segmenter.close()
    print(f"{request.selection_status}: {result.status}; {len(result.masks)} mask candidates; saved {args.out}")
    if result.status != "SEGMENTED":
        parser.error(str(result.observations))


if __name__ == "__main__":
    main()
