"""Offline verification of the one saved source-anchor experiment; no model calls."""
import ast
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from PIL import Image
from transcreation.orchestration import validate_planner_audit
from transcreation.stages.ollama_planner import parse_planning_input,planning_result_schema


def verify(folder):
    def read(name):return json.loads((folder/name).read_text(encoding='utf8'))
    old=read('../iteration6_verified_source/verified_run/planner_audit.json')
    audit=read('planner_audit.json');frozen=read('experiment_frozen.json');saved=read('validated_plan.json')
    assert audit['input']==old['input']==read('planning_input.json')
    assert set(audit['request'])==set(old['request'])
    for key in old['request']:
        if key!='messages':assert old['request'][key]==audit['request'][key]
    assert old['request']['messages'][1]==audit['request']['messages'][1]
    assert old['request']['messages'][0]['content']!=audit['request']['messages'][0]['content']
    assert audit['request']['messages'][0]['content']==(folder/'new_system_prompt.txt').read_bytes().decode()
    assert old['request']['messages'][0]['content']==(folder/'old_system_prompt.txt').read_bytes().decode()
    assert audit['resolved_model']['digest']==old['resolved_model']['digest']
    assert audit['request']['format']==read('baseline_schema.json')==planning_result_schema()
    root=folder.parents[2]
    trees=[ast.parse((folder/'baseline_ollama_planner.py').read_text()),
           ast.parse((root/'src/transcreation/stages/ollama_planner.py').read_text())]
    for tree in trees:
        tree.body=[node for node in tree.body if not (isinstance(node,ast.Assign) and
            any(isinstance(target,ast.Name) and target.id=='SYSTEM_PROMPT' for target in node.targets))]
    assert ast.dump(trees[0],include_attributes=False)==ast.dump(trees[1],include_attributes=False)
    assert hashlib.sha256((root/'src/transcreation/stages/planning.py').read_bytes()).hexdigest()==frozen['validator_source_sha256']
    final,issues=validate_planner_audit(parse_planning_input(audit['input']),audit)
    assert json.loads(json.dumps(asdict(final)))==saved['planning_result'] and issues==saved['issues']
    assert read('raw_response_before_validation.json')==audit['response']
    assert (folder/'raw_qwen_message.txt').read_bytes().decode()==audit['response']['message']['content']
    assert hashlib.sha256((folder/'original.webp').read_bytes()).hexdigest()==frozen['source_image_sha256']
    assert hashlib.sha256((folder/'planning_input.json').read_bytes()).hexdigest()==frozen['planning_input_sha256']
    assert hashlib.sha256((folder/'saved_caption.json').read_bytes()).hexdigest()==frozen['saved_caption_sha256']
    with Image.open(folder/'original.webp') as image:assert image.size==(1408,1120) and image.format=='WEBP'
    assert sum(c['generation'] for c in read('transport_calls.json'))==1
    candidate=audit['raw_planning_result']['candidate_edits'][0];verified=audit['input']['verified_objects'][0]
    assert candidate['object_description']==verified['description']
    assert candidate['verified_object_id']==verified['object_id']
    assert candidate['localization_phrase']==verified['description']
    assert final.decision=='REVIEW' and not final.candidate_edits
    return {'only_changed_request_path':'messages[0].content','planning_input_unchanged':True,
        'model_digest_and_schema_unchanged':True,'raw_and_final_preserved':True,'source_fields_exactly_match_verified_object':True,
        'raw_decision':audit['raw_planning_result']['decision'],'final_decision':final.decision,
        'released_candidates':0,'issue_codes':[i['code'] for i in issues],'verification_model_calls':0}


if __name__=='__main__':print(json.dumps(verify(Path(__file__).resolve().parent),indent=2))
