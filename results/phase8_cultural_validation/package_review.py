"""Seal Phase 8 evidence and verify extracted offline execution; never rerun models."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

root=Path(__file__).resolve().parents[2];p=root/'results/phase8_cultural_validation'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=json.loads((p/'preservation_before.json').read_text())
changed=[name for name,h in before.items() if not (root/name).is_file() or sha(root/name)!=h]
assert not changed,changed
protocol=json.loads((p/'preregistration.json').read_text());c=p/'case1'
assert sha(c/'edit_specification.json')==protocol['case_specification_sha256']
assert sha(c/'editor_config.json')==protocol['configuration_sha256']
assert sha(c/'region_provenance.json')==protocol['region_provenance_sha256']
for seed in [42,43]:assert sha(c/f'request_seed_{seed}.json')==protocol['request_hashes'][str(seed)]
assert sha(p/'human_protocol_preregistration.json')==protocol['human_acceptance_protocol_sha256']
assert sha(root/'data/ramen.jpg')=='37e9b669cac70fb782a7ea7637c27ffd20726dcb1e88ad3f3d54c2f7f38ffee0'
old_zip_receipts=[]
for receipt_path in ['results/appearance_transfer_baseline/package_receipt.json',
                     'results/phase7_integration/v4_completed/package_verification.json']:
    receipt=json.loads((root/receipt_path).read_text());name=receipt.get('path',receipt.get('zip'))
    assert sha(root/name)==receipt['sha256'];old_zip_receipts.append(name)
audit=json.loads((c/'automated/validated_plan.json').read_text())
assert audit['planning_result']['decision']=='REVIEW' and not audit['planning_result']['candidate_edits']
human=json.loads((p/'human_evaluation/status.json').read_text());assert human['actual_reviewer_count']==0 and not human['actual_ratings']
preservation={'prior_files_checked':len(before),'modified_or_missing':changed,
    'original_ramen_hash_unchanged':True,'previous_final_zip_receipts_matched':old_zip_receipts,
    'preregistered_input_configuration_specification_and_region_hashes':'all unchanged',
    'existing_validator_models_and_review_code':'unchanged',
    'new_implementation':['src/transcreation/stages/instruction_editor.py','scripts/instruction_edit.py',
                          'tests/test_instruction_editor.py'],
    'other_authorized_changes':['README Phase8 status/link','pyproject optional cultural-validation extra'],
    'new_editor_calls':2,'hidden_generation_retries':0,'new_SD15_calls':0,'old_human_decisions_changed':False}
(p/'preservation_verification.json').write_text(json.dumps(preservation,indent=2))
status={'technical_execution':'two real SDXL+ControlNet calls completed on local RTX3050 4GB',
    'primary_FLUX_execution':'NOT_EXECUTED','T4_execution':'NOT_EXECUTED',
    'automated_decision':'REVIEW','released_candidates':0,'guided_scope':'RESEARCH_ONLY',
    'seed42_visual':'FAIL: added props and flat pastry','seed43_visual':'PROVISIONAL_SAMOSA_LIKE; needs cultural/realism review',
    'outside_and_protected_differences':0,'actual_human_reviewers':0,'cultural_pass':'PENDING_HUMAN_EVALUATION',
    'six_case_pilot_completed':0,'model_generations':2,'new_SD15_generations':0,
    'tests_before':420,'tests_after':440,'historical_results_preserved':True}
(p/'final_status.json').write_text(json.dumps(status,indent=2))
payload={}
def add(file):
    if file.is_file() and '__pycache__' not in file.parts and file.suffix not in ('.pyc','.zip','.pdf','.whl'):
        payload[file.relative_to(root).as_posix()]=file.read_bytes()
for folder in ['src','scripts','configs','tests']:
    for f in (root/folder).rglob('*'):add(f)
add(root/'pyproject.toml');add(root/'reports/cultural_transcreation_validation.md')
for f in p.rglob('*'):
    if f.name in ('package_receipt.json','portable_verification.json','README_before.md','previous_REPRODUCTION.md'):continue
    if f.suffix in ('.html','.txt') and f.parent==p/'research':continue
    add(f)
payload['README.md']=(p/'REPRODUCTION.md').read_bytes()
with tempfile.TemporaryDirectory(prefix='cultural_validation_review_') as temp:
    extracted=Path(temp)
    for name,data in payload.items():
        target=extracted/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    env={**os.environ,'PYTHONPATH':str(extracted/'src'),'HF_HUB_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
    def run(args):
        result=subprocess.run([sys.executable,'-B',*args],cwd=extracted,env=env,capture_output=True,text=True)
        assert result.returncode==0,(args,result.stdout[-1000:],result.stderr[-3000:])
        return {'command':args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    tests=run(['-m','unittest','discover','-s','tests','-v'])
    assert 'Ran 440 tests' in tests['stderr'] and '\nOK' in tests['stderr']
    pixels=run(['results/phase8_cultural_validation/verify_outputs.py'])
    cli=run(['-m','scripts.instruction_edit','--help'])
    provenance=run(['-c',
        "from pathlib import Path;import json;from transcreation.stages.instruction_editor import InstructionEditInput,validate_edit;"
        "p=Path('results/phase8_cultural_validation/case1');"
        "r=InstructionEditInput(**json.loads((p/'reproduce_request_seed_42.json').read_text()));"
        "a=validate_edit(r,json.loads((p/'editor_config.json').read_text()));"
        "print(a[0].size,a[5]);assert a[0].size==(1280,853)"])
    broken=[];links=[]
    report=extracted/'reports/cultural_transcreation_validation.md'
    for link in re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
        if '://' in link or link.startswith('#'):continue
        target=(report.parent/link.split('#')[0]).resolve();links.append(link)
        if not target.exists():broken.append(link)
    assert not broken,broken
    portable={'full_tests':tests,'independent_saved_pixels':pixels,'CLI_help':cli,'source_mask_control_and_crop_provenance':provenance,
        'report_links_checked':len(links),'broken_report_links':broken,'new_model_inference_calls':0,
        'note':'Extracted offline tests/pixel checks; no third live model generation or bit-exact GPU reproduction claim.'}
    (p/'portable_verification.json').write_text(json.dumps(portable,indent=2))
    payload['results/phase8_cultural_validation/portable_verification.json']=(p/'portable_verification.json').read_bytes()
manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(payload.items())}
payload['SHA256_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
output=root/'results/cultural_validation_review.zip'
with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,data in sorted(payload.items()):archive.writestr(name,data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None and len(archive.namelist())==len(set(archive.namelist()))
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==h for name,h in manifest.items())
receipt={'path':output.relative_to(root).as_posix(),'bytes':output.stat().st_size,'sha256':sha(output),
    'entries':len(payload),'CRC_and_manifest':'PASS','portable_full_suite_passed':440,
    'portable_pixel_provenance_checks':'PASS','broken_report_links':0,'new_model_calls_in_package_validation':0,
    'human_evaluation':'PENDING_HUMAN_EVALUATION','six_case_pilot':0,'historical_changes':changed}
(p/'package_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
