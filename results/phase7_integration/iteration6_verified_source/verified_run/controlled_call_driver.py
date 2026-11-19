"""One real Qwen call with the confirmed object; reuse the exact real I5 caption."""
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

from PIL import Image
from transcreation.config import load_config,load_planner_config
from transcreation.contracts import VerifiedObject
from transcreation.orchestration import _planner_idle,validate_planner_audit
from transcreation.stages.ollama_planner import OllamaPlanner,SYSTEM_PROMPT,parse_planning_input

ROOT=Path(r'C:\Users\sayan\PycharmProjects\MiniProject')
PENDING=ROOT/'results/phase7_integration/iteration6_verified_source'
OUT=PENDING/'verified_run'
OLD=ROOT/'results/phase7_integration/iteration5_ramen'
SOURCE=ROOT/'data/ramen.jpg'
sha=lambda data:hashlib.sha256(data).hexdigest()
OUT.mkdir(parents=True,exist_ok=False)


def write(name,value):
    with (OUT/name).open('x',encoding='utf8') as file:
        json.dump(value,file,indent=2,ensure_ascii=False,allow_nan=False);file.write('\n')


paths=[p for folder in ('src','scripts','tests','configs') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/'pyproject.toml',SOURCE,ROOT/'results/phase7_integration/phase7_working_report.md']
paths += [p for p in (ROOT/'results/phase7_integration').rglob('*') if p.is_file() and not p.is_relative_to(OUT)]
write('preservation_before.json',{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in paths})
(OUT/'working_report_before.txt').write_bytes((ROOT/'results/phase7_integration/phase7_working_report.md').read_bytes())
status=subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True)
write('git_before.json',{'status':status.stdout})
source_data=SOURCE.read_bytes();source_hash=sha(source_data)
assert source_hash=='37e9b669cac70fb782a7ea7637c27ffd20726dcb1e88ad3f3d54c2f7f38ffee0'
with Image.open(SOURCE) as image:
    image.load();assert image.size==(1408,1120) and image.format=='WEBP'
(OUT/'original.webp').write_bytes(source_data)
(OUT/'source_preview.png').write_bytes((PENDING/'source_preview.png').read_bytes())
confirmation='''I have personally inspected the exact photograph `data/ramen.jpg`, SHA-256 `37e9b669cac70fb782a7ea7637c27ffd20726dcb1e88ad3f3d54c2f7f38ffee0`.

I confirm:
- Original object: Japanese ramen noodles in a white bowl.
- Editable content: Noodles and relevant food contents.
- Protected object: The white bowl itself.
- Target culture: Indian.
- Intended transformation: Indian-style masala noodles.
- Preserve: Bowl, tabletop, camera angle, lighting and background.

This is my explicit image-bound user confirmation. Record it as user-provided evidence, not independent proof of the dish's origin or authorization to edit the image.'''
obj=VerifiedObject('ramen-food-1','Japanese ramen noodles in a white bowl')
write('human_confirmation.json',{'evidence_type':'ACTUAL_USER_MESSAGE','source_image_sha256':source_hash,
    'verbatim_user_confirmation':confirmation,'confirmed_object':asdict(obj),
    'editable_content':'Noodles and relevant food contents.','protected_object':'The white bowl itself.',
    'target_culture':'Indian','intended_transformation':'Indian-style masala noodles.',
    'preserve':'Bowl, tabletop, camera angle, lighting and background.',
    'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'timestamp_meaning':'System time of recording this received confirmation, not an invented inspection time.',
    'inspection_time_supplied_by_user':None,'named_reviewer_identity':None,
    'source_verification_provided_by_actual_user':True,'independent_cultural_origin_proven':False,
    'image_edit_authorized':False,'edit_intent_accepted':False})
before_bytes=(OLD/'run/planning_input.json').read_bytes()
before=json.loads(before_bytes);old_request=parse_planning_input(before)
request=replace(old_request,verified_objects=(obj,))
after=json.loads(json.dumps(asdict(request)))
changed=[key for key in before if before[key]!=after[key]]
assert changed==['verified_objects'] and set(before)==set(after)
(OUT/'planning_input_before.json').write_bytes(before_bytes)
write('planning_input.json',asdict(request))
write('input_comparison.json',{'before':before,'after':after,'changed_fields':changed,
    'all_other_fields_exactly_equal':all(before[k]==after[k] for k in before if k!='verified_objects'),
    'user_instructions_unchanged':before['user_instructions']==after['user_instructions'],
    'note':'The confirmation mentions a white bowl; the exact confirmed wording is used only inside the added VerifiedObject. The older instructions/declaration are intentionally not edited.'})
caption_bytes=(OLD/'run/caption.json').read_bytes();caption=json.loads(caption_bytes)
assert caption['input_sha256']==source_hash and caption['caption']==request.source_caption
assert caption['eos_reached'] and not caption['token_ceiling_reached'] and request.caption_status=='COMPLETE'
(OUT/'saved_caption.json').write_bytes(caption_bytes)
frozen_old=json.loads((OLD/'experiment_frozen.json').read_text(encoding='utf8'))
planner_config=load_planner_config(ROOT/'configs/planner.yaml')
assert asdict(planner_config)==frozen_old['qwen_configuration']
assert asdict(load_config(ROOT/'configs/models.yaml'))==frozen_old['smolvlm_configuration']
assert sha(SYSTEM_PROMPT.encode())==frozen_old['system_prompt_sha256']
assert sha((ROOT/'src/transcreation/stages/planning.py').read_bytes())==frozen_old['validator_source_sha256']
planner=OllamaPlanner(planner_config)
tags=planner.api('/api/tags');model=next(v for v in tags['models'] if v['name']==planner_config.model)
assert model['digest']==frozen_old['resolved_installed_qwen']['digest']
_planner_idle(planner)
write('experiment_frozen.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'source_path':str(SOURCE),
    'source_image_sha256':source_hash,'dimensions':[1408,1120],'actual_format':'WEBP','verified_object':asdict(obj),
    'confirmation_sha256':sha((OUT/'human_confirmation.json').read_bytes()),'planning_input':asdict(request),
    'changed_planning_input_fields':changed,'only_verified_objects_changed':True,
    'caption_reused_from':'results/phase7_integration/iteration5_ramen/run/caption.json','caption_file_sha256':sha(caption_bytes),
    'smolvlm_rerun':False,'qwen_configuration':asdict(planner_config),'resolved_installed_model':model,
    'qwen_system_prompt':SYSTEM_PROMPT,'system_prompt_sha256':sha(SYSTEM_PROMPT.encode()),
    'validator_source_sha256':frozen_old['validator_source_sha256'],'condition_limit':1,'retry_limit':0,
    'call_path':'Existing OllamaPlanner.record_plan with unchanged parser/validator; caption artifact reused, no run_pipeline image-captioning pass.',
    'expected_checks':['Copy exact confirmed description/id','Localization refers to original ramen, not masala noodles',
        'Preserve original-scene summary and complete original instructions','Retain all independent blocking checks',
        'Distinguish human-verification warnings from rejection','PROPOSE only permits preparation of PENDING intent',
        'No source verification or cultural intent authorizes image editing','No SmolVLM, grounding, SAM or diffusion calls']})
# Transparent transport observation: archive the actual response before the existing
# planner parses/validates it. Requests/responses are passed through unchanged.
real_api=planner.api;calls=[]
def archived_api(path,payload=None,**kwargs):
    start=time.perf_counter();response=real_api(path,payload,**kwargs)
    is_generation=path=='/api/chat' and bool((payload or {}).get('messages'))
    if is_generation:
        write('raw_response_before_validation.json',response)
    calls.append({'path':path,'generation':is_generation,'seconds':time.perf_counter()-start,
                  'request_payload_sha256':sha(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()) if payload is not None else None})
    return response
planner.api=archived_api
stop=threading.Event();samples=[];started=time.perf_counter()
def monitor():
    while not stop.is_set():
        try:
            p=subprocess.run(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],
                capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            samples.append({'seconds':time.perf_counter()-started,'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()})
        except Exception as exc:samples.append({'seconds':time.perf_counter()-started,'error':str(exc)})
        stop.wait(1)
worker=threading.Thread(target=monitor,daemon=True)
write('invocation_started.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),
    'planner_call_count_planned':1,'frozen_sha256':sha((OUT/'experiment_frozen.json').read_bytes()),'retries_allowed':0})
worker.start()
try:
    record=planner.record_plan(request)
    elapsed=time.perf_counter()-started
    write('planner_audit.json',record)
finally:
    stop.set();worker.join(timeout=6)
    write('transport_calls.json',calls)
    write('gpu_samples.json',{'measurement':'Sampled total-device framebuffer MiB/utilization; includes other processes, not per-model allocation.', 'samples':samples})
assert sum(v['generation'] for v in calls)==1
write('invocation_result.json',{'planner_calls':1,'retry_count':0,'wall_seconds':elapsed,
    'SmolVLM_calls':0,'GroundingDINO_calls':0,'SAM_calls':0,'Diffusion_calls':0,
    'source_image_sha256':source_hash,'raw_response_archived_before_validation':True,
    'planner_validation_status':record.get('validation',{}).get('status')})
if record.get('validation',{}).get('status')=='valid':
    final,issues=validate_planner_audit(request,record)
    write('validated_plan.json',{'planning_result':asdict(final),'issues':issues})
    print(json.dumps({'raw':record['raw_planning_result'],'final':asdict(final),'issues':issues},indent=2))
else:
    print(json.dumps(record.get('validation'),indent=2))
write('post_run_residency.json',real_api('/api/ps'))
assert sha(SOURCE.read_bytes())==source_hash
print('One real Qwen call completed; no other model called.')
