"""Verify this saved real experiment without invoking any model or service."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from PIL import Image
from transcreation.orchestration import validate_planner_audit
from transcreation.stages.ollama_planner import parse_planning_input


def verify(folder):
    def read(name):
        return json.loads((folder/name).read_text(encoding='utf8'))
    before=read('planning_input_before.json');after=read('planning_input.json')
    changes=[key for key in before if before[key]!=after[key]]
    assert changes==['verified_objects'] and set(before)==set(after)
    confirmed=read('human_confirmation.json')['confirmed_object']
    assert after['verified_objects']==[confirmed]
    assert confirmed=={'object_id':'ramen-food-1','description':'Japanese ramen noodles in a white bowl'}
    audit=read('planner_audit.json');saved=read('validated_plan.json')
    final,issues=validate_planner_audit(parse_planning_input(after),audit)
    assert json.loads(json.dumps(asdict(final)))==saved['planning_result'] and issues==saved['issues']
    response=read('raw_response_before_validation.json')
    assert response==audit['response']
    assert (folder/'raw_qwen_message.txt').read_bytes().decode('utf8')==response['message']['content']
    frozen=read('experiment_frozen.json')
    assert hashlib.sha256((folder/'original.webp').read_bytes()).hexdigest()==frozen['source_image_sha256']
    assert hashlib.sha256((folder/'saved_caption.json').read_bytes()).hexdigest()==frozen['caption_file_sha256']
    assert hashlib.sha256((folder/'human_confirmation.json').read_bytes()).hexdigest()==frozen['confirmation_sha256']
    with Image.open(folder/'original.webp') as image:
        assert image.size==(1408,1120) and image.format=='WEBP'
    assert sum(call['generation'] for call in read('transport_calls.json'))==1
    assert final.decision=='REVIEW' and not final.candidate_edits
    assert read('invocation_result.json')['SmolVLM_calls']==0
    return {'input_changes':changes,'raw_decision':audit['raw_planning_result']['decision'],
        'final_decision':final.decision,'released_candidates':len(final.candidate_edits),
        'issue_codes':[i['code'] for i in issues],'raw_response_and_hashes_valid':True,
        'actual_saved_qwen_generation_calls':1,'verification_model_calls':0}


if __name__=='__main__':
    print(json.dumps(verify(Path(__file__).resolve().parent),indent=2))
