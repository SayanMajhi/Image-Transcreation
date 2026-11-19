"""One revised-system-prompt experiment; no captioning or downstream execution."""
import ast
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

from PIL import Image
from transcreation.config import load_planner_config
from transcreation.orchestration import _planner_idle,validate_planner_audit,PipelineInput,PipelineResult,PipelineState
from transcreation.stages.ollama_planner import OllamaPlanner,SYSTEM_PROMPT,planning_result_schema,parse_planning_input

ROOT=Path(r'C:\Users\sayan\PycharmProjects\MiniProject')
OUT=ROOT/'results/phase7_integration/iteration7'
OLD=ROOT/'results/phase7_integration/iteration6_verified_source/verified_run'
SOURCE=ROOT/'data/ramen.jpg'
sha=lambda data:hashlib.sha256(data).hexdigest()


def write(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


assert json.loads((OUT/'tests_before.json').read_text())['returncode']==0
baseline_module=(OUT/'baseline_ollama_planner.py').read_text()
current_module=(ROOT/'src/transcreation/stages/ollama_planner.py').read_text()
def nonprompt_ast(text):
    tree=ast.parse(text)
    tree.body=[node for node in tree.body if not (isinstance(node,ast.Assign) and
               any(isinstance(target,ast.Name) and target.id=='SYSTEM_PROMPT' for target in node.targets))]
    return ast.dump(tree,include_attributes=False)
assert nonprompt_ast(baseline_module)==nonprompt_ast(current_module)
old_prompt=(OUT/'old_system_prompt.txt').read_bytes().decode('utf8')
assert SYSTEM_PROMPT!=old_prompt
assert planning_result_schema()==json.loads((OUT/'baseline_schema.json').read_text())
(OUT/'new_system_prompt.txt').write_bytes(SYSTEM_PROMPT.encode('utf8'))
old_audit=json.loads((OLD/'planner_audit.json').read_text(encoding='utf8'))
old_freeze=json.loads((OLD/'experiment_frozen.json').read_text(encoding='utf8'))
input_bytes=(OLD/'planning_input.json').read_bytes()
(OUT/'planning_input.json').write_bytes(input_bytes)
request=parse_planning_input(json.loads(input_bytes))
assert asdict(load_planner_config(ROOT/'configs/planner.yaml'))==old_audit['config']
assert sha((ROOT/'src/transcreation/stages/planning.py').read_bytes())==old_freeze['validator_source_sha256']
source_bytes=SOURCE.read_bytes();source_hash=sha(source_bytes)
assert source_hash==old_freeze['source_image_sha256']
with Image.open(SOURCE) as image:assert image.size==(1408,1120) and image.format=='WEBP'
(OUT/'original.webp').write_bytes(source_bytes)
for name in ('saved_caption.json','human_confirmation.json','source_preview.png'):
    (OUT/name).write_bytes((OLD/name).read_bytes())
assert request.source_caption=='A bowl of food with chopsticks and a spoon.'
assert request.verified_objects[0].description=='Japanese ramen noodles in a white bowl'
assert request.verified_objects[0].object_id=='ramen-food-1'
planner=OllamaPlanner(load_planner_config(ROOT/'configs/planner.yaml'))
model=next(v for v in planner.api('/api/tags')['models'] if v['name']==planner.config.model)
assert model['digest']==old_audit['resolved_model']['digest']
_planner_idle(planner)
expected=dict(old_audit['request'])
expected['messages']=[{'role':'system','content':SYSTEM_PROMPT},old_audit['request']['messages'][1]]
write('experiment_frozen.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
    'source_image_sha256':source_hash,'source_path':str(SOURCE),'dimensions':[1408,1120],'format':'WEBP',
    'planning_input':asdict(request),'planning_input_sha256':sha(input_bytes),
    'saved_caption_sha256':sha((OUT/'saved_caption.json').read_bytes()),
    'human_confirmation_sha256':sha((OUT/'human_confirmation.json').read_bytes()),
    'old_system_prompt_sha256':sha(old_prompt.encode()),'new_system_prompt_sha256':sha(SYSTEM_PROMPT.encode()),
    'model':model,'config':asdict(planner.config),'schema':planning_result_schema(),
    'validator_source_sha256':old_freeze['validator_source_sha256'],
    'nonprompt_adapter_ast_unchanged':True,'only_intended_inference_change':'request.messages[0].content',
    'predeclared_expected_request':expected,'maximum_generation_calls':1,'retry_limit':0,
    'procedure':'Existing OllamaPlanner.record_plan; exact saved input/caption reused, no image-captioning coordinator call.',
    'review_bridge_if_propose':'Export truthful native-format evidence with SAVED_CAPTION_REUSED provenance and real planner audit, then existing prepare tool; no model field repair or automatic acceptance.'})
real_api=planner.api;calls=[]
def observed_api(path,payload=None,**kwargs):
    t=time.perf_counter();reply=real_api(path,payload,**kwargs)
    generation=path=='/api/chat' and bool((payload or {}).get('messages'))
    if generation:write('raw_response_before_validation.json',reply)
    calls.append({'path':path,'generation':generation,'seconds':time.perf_counter()-t})
    return reply
planner.api=observed_api
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
    'frozen_sha256':sha((OUT/'experiment_frozen.json').read_bytes()),'planned_generation_calls':1,'retries_allowed':0})
worker.start()
try:
    audit=planner.record_plan(request);elapsed=time.perf_counter()-started
    write('planner_audit.json',audit)
finally:
    stop.set();worker.join(timeout=6)
    write('transport_calls.json',calls)
    write('gpu_samples.json',{'measurement':'Sampled total-device used framebuffer MiB/utilization, not per-model allocation.', 'samples':samples})
assert sum(c['generation'] for c in calls)==1
assert audit['request']==expected
assert audit['response']==json.loads((OUT/'raw_response_before_validation.json').read_text())
write('request_comparison.json',{'before':old_audit['request'],'after':audit['request'],
    'changed_paths':['messages[0].content'],'planning_input_equal':audit['input']==old_audit['input'],
    'all_other_request_fields_equal':all(old_audit['request'][key]==audit['request'][key] for key in old_audit['request'] if key!='messages'),
    'user_message_exactly_equal':old_audit['request']['messages'][1]==audit['request']['messages'][1],
    'model_digest_equal':audit['resolved_model']['digest']==old_audit['resolved_model']['digest'],
    'schema_equal':audit['request']['format']==old_audit['request']['format']})
write('invocation_result.json',{'wall_seconds':elapsed,'generation_calls':1,'retries':0,
    'SmolVLM_calls':0,'GroundingDINO_calls':0,'SAM_calls':0,'Diffusion_calls':0,
    'raw_saved_before_validation':True,'validation_status':audit['validation']['status']})
write('post_run_residency.json',real_api('/api/ps'))
if audit['validation']['status']=='valid':
    final,issues=validate_planner_audit(request,audit)
    write('validated_plan.json',{'planning_result':asdict(final),'issues':issues})
    (OUT/'raw_qwen_message.txt').write_bytes(audit['response']['message']['content'].encode('utf8'))
    if final.decision=='PROPOSE':
        # Existing review preparation needs a native-format planning bundle. Export
        # the actual saved caption and actual new audit, never a fabricated plan.
        bundle=OUT/'review_source_run';bundle.mkdir(exist_ok=False)
        registry={}
        def artifact(label,path,data):
            target=bundle/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            registry[label]={'id':sha(data),'sha256':sha(data),'path':path}
        def data(value):return (json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
        context=PipelineInput(str(SOURCE),source_hash,request.target_culture,str(bundle),'AUTOMATED_PLANNING',
            source_culture=request.source_culture,user_instructions=request.user_instructions,verified_objects=request.verified_objects)
        artifact('pipeline_input.json','pipeline_input.json',data(asdict(context)))
        artifact('source','evidence/source/ramen.jpg',source_bytes)
        artifact('caption.json','caption.json',(OUT/'saved_caption.json').read_bytes())
        artifact('planning_input.json','planning_input.json',input_bytes)
        artifact('planner_audit.json','planner_audit.json',(OUT/'planner_audit.json').read_bytes())
        artifact('validated_plan.json','validated_plan.json',(OUT/'validated_plan.json').read_bytes())
        provenance={'procedure':'Native-format export of the real planner-only run, not a fresh run_pipeline image-captioning pass.',
            'caption_origin':'Iteration 5 actual caption, reused byte-for-byte','caption_inference_this_condition':False}
        artifact('caption_reuse.json','caption_reuse.json',data(provenance))
        transitions=({'stage':'source','action':'SOURCE_HASH_VERIFIED'},
            {'stage':'caption','action':'SAVED_CAPTION_REUSED','model_inference':False},
            {'stage':'planning','action':'REAL_QWEN_COMPLETED'},
            {'stage':'validation','action':'PROPOSE_VALIDATED_UNAPPROVED'},
            {'stage':'edit_intent_review','action':'STOP','generation_permitted':False})
        result=PipelineResult('AUTOMATED_PLANNING',PipelineState.EDIT_PROPOSAL_READY,
            ('source','caption_reuse','planning','deterministic_validation'),'edit_intent_review',
            'Real final PROPOSE draft; explicit human edit-intent review required.',registry,transitions,
            tuple(final.verification_requirements))
        (bundle/'pipeline_result.json').write_bytes(data(asdict(result)))
        from scripts.review_edit_intent import prepare,verify
        pending=[]
        for index in range(len(final.candidate_edits)):
            path=prepare(bundle/'pipeline_result.json',SOURCE,index,OUT/'edit_intent_reviews'/f'candidate_{index}')
            review=verify(path);assert review['decision']=='PENDING' and review['reviewer'] is None
            assert not review['checked_user_instructions'] and not review['image_edit_authorized']
            pending.append({'candidate_index':index,'path':path.relative_to(OUT).as_posix(),'decision':'PENDING'})
        write('review_preparation.json',{'pending_reviews':pending,'accepted':False,'downstream_dispatch':False})
    else:write('review_preparation.json',{'pending_reviews':[],'accepted':False,'reason':'Final '+str(final.decision)+'; no released candidate eligible for edit-intent review.'})
    print(json.dumps({'raw':audit['raw_planning_result'],'final':asdict(final),'issues':issues},indent=2))
else:print(json.dumps(audit['validation'],indent=2))
assert sha(SOURCE.read_bytes())==source_hash
print('Exactly one Qwen generation; no retries or other model inference.')
