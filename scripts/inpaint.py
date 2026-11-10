"""Run one explicitly scoped inpainting research request, independently of the planner."""
import argparse
import json
from pathlib import Path

from transcreation.config import load_inpainting_config
from transcreation.contracts import InpaintingInput
from transcreation.stages.inpainting import run_inpainting


def main(argv: list[str] | None = None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True,help="Explicit RESEARCH_ONLY request with pinned source hashes")
    parser.add_argument("--config",type=Path,default=Path("configs/inpainting.yaml"))
    parser.add_argument("--out",type=Path,required=True,help="New experiment directory")
    args=parser.parse_args(argv)
    try:
        request=InpaintingInput(**json.loads(args.input.read_text(encoding="utf-8")))
        config=load_inpainting_config(args.config)
        result=run_inpainting(request,config,args.out)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        parser.error(str(exc))
    print(f"{result['status']}: RESEARCH_ONLY; saved {args.out}")
    if result["status"]!="COMPLETED": parser.error(str(result["observations"]))


if __name__=="__main__":
    main()
