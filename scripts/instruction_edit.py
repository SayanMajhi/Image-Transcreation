"""Run an explicitly specified research editor without planner/review escalation."""
import argparse
import json
from pathlib import Path
from transcreation.stages.instruction_editor import InstructionEditInput,run_editor

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    request=InstructionEditInput(**json.loads(args.input.read_text()))
    result=run_editor(request,json.loads(args.config.read_text()),args.out)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
