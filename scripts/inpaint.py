"""Run one explicitly scoped inpainting research request, independently of the planner."""
import argparse
import json
from pathlib import Path

from transcreation.config import load_inpainting_config
from transcreation.contracts import InpaintingInput
from transcreation.stages.inpainting import run_inpainting


def main(argv: list[str] | None = None):
    parser=argparse.ArgumentParser(description=__doc__)
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input",type=Path,help="Original SAM-mask RESEARCH_ONLY request")
    inputs.add_argument("--refined-input",type=Path,help="Separate manually refined RESEARCH_ONLY request with polygon/exclusion provenance")
    parser.add_argument("--config",type=Path,default=Path("configs/inpainting.yaml"))
    parser.add_argument("--out",type=Path,required=True,help="New experiment directory")
    parser.add_argument("--max-attempts",type=int,choices=(1,2),help="Refined research only: cap actual generation attempts, including OOM retry")
    args=parser.parse_args(argv)
    try:
        config=load_inpainting_config(args.config)
        if args.refined_input:
            from transcreation.stages.refined_inpainting import RefinedMaskInput, run_refined_inpainting
            request=RefinedMaskInput(**json.loads(args.refined_input.read_text(encoding="utf-8")))
            result=run_refined_inpainting(request,config,args.out,max_attempts=args.max_attempts or 2)
        else:
            if args.max_attempts is not None:
                raise ValueError("attempt override is available only for separate refined research")
            request=InpaintingInput(**json.loads(args.input.read_text(encoding="utf-8")))
            result=run_inpainting(request,config,args.out)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        parser.error(str(exc))
    print(f"{result['status']}: RESEARCH_ONLY; saved {args.out}")
    if result["status"]!="COMPLETED": parser.error(str(result["observations"]))


if __name__=="__main__":
    main()
