"""Compare unchanged raw evidence with the saved baseline and corrected validator.

No models, manual execution plans or approvals. Outputs are replay-only evidence.
Run from repository/package root with src on PYTHONPATH and a new output folder.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import argparse

from transcreation.stages import planning as corrected
from transcreation.stages.ollama_planner import parse_planning_input


ROOT = Path(__file__).resolve().parents[3]
BASELINE = Path(__file__).parent/'baseline/src/transcreation/stages/planning.py'


def save(path, data):
    if path.exists():
        existing = path.read_bytes()
        # A previous Windows text write may use CRLF; leave its bytes untouched.
        if existing != data and existing.replace(b'\r\n', b'\n') != data:
            raise FileExistsError(f'refusing to overwrite different replay evidence: {path}')
    else:
        with path.open('xb') as output:
            output.write(data)


def evaluate(policy, supplied, raw):
    try:
        draft, initial = policy.parse_model_draft(deepcopy(raw))
        final, issues = policy.validate_planning_result(parse_planning_input(supplied), draft, initial)
        return {'status':'VALIDATED','planning_result':asdict(final),'issues':issues,
            'decision':final.decision,'candidate_count':len(final.candidate_edits),
            'human_review_requirement':'PENDING_EDIT_INTENT_REQUIRED' if final.decision=='PROPOSE' else 'NO_RELEASED_CANDIDATES',
            'grounding_permitted':False,'sam_permitted':False,'inpainting_permitted':False}
    except (ValueError, TypeError, KeyError) as exc:
        return {'status':'REJECTED_MALFORMED','error_type':type(exc).__name__,'message':str(exc),
            'candidate_count':0,'grounding_permitted':False,'sam_permitted':False,'inpainting_permitted':False}


def replay(out):
    spec=importlib.util.spec_from_file_location('recorded_iteration3_policy', BASELINE)
    before=importlib.util.module_from_spec(spec); spec.loader.exec_module(before)
    out.mkdir(parents=True,exist_ok=True)
    def comparison(name, supplied, raw, provenance):
        old=evaluate(before,supplied,raw); new=evaluate(corrected,supplied,raw)
        if raw.get('decision')!='PROPOSE' and new.get('decision')=='PROPOSE':
            raise AssertionError('A raw REVIEW/ABSTAIN was promoted')
        return {'record_type':'POLICY_REPLAY_ONLY','case':name,'provenance':provenance,'input':supplied,
            'untouched_raw_result':raw,'before':old,'after':new,'model_calls':0,'review_approval_created':False}
    diagnostics=json.loads((ROOT/'results/phase7_integration/iteration3/policy_diagnostics.json').read_text(encoding='utf8'))
    rows=[]
    for case in diagnostics['cases']:
        rows.append(comparison(case['case'],case['input'],case['synthetic_raw_draft'],
            {'scope':'SYNTHETIC_POLICY_DIAGNOSTIC','source':'results/phase7_integration/iteration3/policy_diagnostics.json'}))
    base=diagnostics['cases'][1]
    for name,change in (
        ('placeholder_object', lambda p:p['candidate_edits'][0].update(object_description='null')),
        ('malformed_candidate_structure', lambda p:p['candidate_edits'][0].update(unexpected_field='invalid')),
        ('overlong_localization', lambda p:p['candidate_edits'][0].update(localization_phrase='source object '*20)),
        ('raw_abstain', lambda p:p.update(decision='ABSTAIN',candidate_edits=[]))):
        raw=deepcopy(base['synthetic_raw_draft']);change(raw)
        rows.append(comparison(name,base['input'],raw,{'scope':'SYNTHETIC_NEGATIVE_REGRESSION'}))
    save(out/'synthetic_before_after.json',(json.dumps(rows,indent=2)+'\n').encode())
    historical=[]
    for folder, names in (
        ('planner_decision_policy_20261108_final', ('01_japanese_food','02_durga_uncertain_incense','03_bicycle_no_change')),
        ('planner_decision_policy_20261108', ('01_japanese_food','02_durga_uncertain_incense','03_bicycle_no_change')),
        ('planner_quality_review_20261108_final', ('02_durga_uncertain_incense',)),
    ):
        for name in names:
            source=ROOT/'results/phase3_llm/experiments'/folder/(name+'.audit.json')
            data=source.read_bytes(); audit=json.loads(data)
            raw=json.loads(audit['response']['message']['content'])
            row=comparison(folder+'/'+name,audit['input'],raw,
                {'source':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),
                 'saved_final_decision':(audit.get('planning_result') or {}).get('decision'),'scope':'HISTORICAL_SAVED_RAW_RESPONSE'})
            target=out/(folder+'_'+name+'.replay.json')
            save(target,(json.dumps(row,indent=2)+'\n').encode())
            original=out/(folder+'_'+name+'.original_audit.json');save(original,data)
            historical.append(row)
    summary={'synthetic_cases':len(rows),'historical_cases':len(historical),
        'synthetic_decision_changes':[{'case':r['case'],'before':r['before'].get('decision'),'after':r['after'].get('decision')}
            for r in rows if r['before'].get('decision')!=r['after'].get('decision')],
        'historical_decision_changes':[r['case'] for r in historical if r['before'].get('decision')!=r['after'].get('decision')],
        'historical_positive_candidates':sum(r['after'].get('decision')=='PROPOSE' for r in historical),
        'baseline_policy_sha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
        'corrected_policy_sha256':hashlib.sha256((ROOT/'src/transcreation/stages/planning.py').read_bytes()).hexdigest(),
        'live_model_calls':0,'replay_outputs_are_not_executable_plans':True}
    save(out/'summary.json',(json.dumps(summary,indent=2)+'\n').encode())
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    print(json.dumps(replay(parser.parse_args().out),indent=2))
