"""Package the bounded visual correction; verify only, never call a model."""
from pathlib import Path
import hashlib
import json
import re
import posixpath
import zipfile

root=Path(__file__).resolve().parents[3];p=root/'results/phase8_cultural_validation/visual_improvement'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=json.loads((p/'preservation_before.json').read_text())
changed=[name for name,h in before.items() if not (root/name).is_file() or sha(root/name)!=h]
assert {name.replace('\\','/') for name in changed}<= {'reports/cultural_transcreation_validation.md'},changed
assert (root/'reports/cultural_transcreation_validation.md').read_bytes().startswith((p/'report_before.md').read_bytes())
frozen=json.loads((p/'preregistration_A.json').read_text())['experiment_A']
assert sha(p/'request_A.json')==frozen['request_sha256'] and sha(p/'config_A.json')==frozen['config_sha256']
assert sha(p/'edit_specification.json')==frozen['specification_sha256'] and sha(p/'control_canny.png')==frozen['control_sha256']
if (p/'preregistration_B.json').exists():
    b=json.loads((p/'preregistration_B.json').read_text())
    assert sha(p/'config_B.json')==b['config_B_sha256'] and sha(p/'request_B.json')==b['request_B_sha256']
    ca=json.loads((p/'config_A.json').read_text());cb=json.loads((p/'config_B.json').read_text())
    assert [key for key in ca if ca[key]!=cb[key]]==['control_scale']
tests=json.loads((p/'tests.json').read_text());assert tests['returncode']==0 and 'Ran 440 tests' in tests['stderr']
completed=[];attempted=0
for condition in ['A','B']:
    result=p/condition/'result.json'
    if result.exists():
        record=json.loads(result.read_text());attempted+=record['calls_attempted']
        if record['status']=='COMPLETED':
            pixels=json.loads((p/f'{condition}_independent_pixels.json').read_text())
            assert pixels['changed_outside_mask']==pixels['changed_protected_pixels']==0
            completed.append(condition)
assert 1<=attempted<=2
(p/'preservation_verification.json').write_text(json.dumps({'prior_files_checked':len(before),
 'changed_old_files':changed,'only_report_append_allowed':True,'model_policy_and_historical_evidence_unchanged':True,
 'source_sha256':sha(p/'source.jpg'),'completed_conditions':completed,'actual_new_generation_calls':attempted,
 'direct_human_review_of_new_outputs':'PENDING','independent_three_person_panel_claimed':False},indent=2))
payload={}
def add(f):
    if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.zip'):
        payload[f.relative_to(root).as_posix()]=f.read_bytes()
for name in ['src','scripts','configs','tests']:
    for f in (root/name).rglob('*'):add(f)
for name in ['pyproject.toml','reports/cultural_transcreation_validation.md']:add(root/name)
for f in p.rglob('*'):
    if f.name not in ('package_receipt.json',):add(f)
for name in ['environment.json','hardware.json','weight_checksums.json']:
    add(p.parent/name)
for folder in ['sam/segmentation','automated']:
    for f in (p.parent/'case1'/folder).rglob('*'):add(f)
payload['README.md']=(p/'REPRODUCTION.md').read_bytes()
broken=[];links=0
# Older report sections are retained verbatim. Supply referenced prior evidence from the verified Phase8 bundle.
with zipfile.ZipFile(root/'results/cultural_human_evaluation_review.zip') as previous:
    names=previous.namelist()
    for target in re.findall(r'\]\(([^)]+)\)',payload['reports/cultural_transcreation_validation.md'].decode('utf-8')):
        if '://' in target or target.startswith('#'):continue
        name=posixpath.normpath(posixpath.join('reports',target.split('#')[0]));links+=1
        if name in payload or any(x.startswith(name.rstrip('/')+'/') for x in payload):continue
        matches=[x for x in names if x==name or x.startswith(name.rstrip('/')+'/')]
        if not matches:broken.append(name)
        for member in matches:
            if not member.endswith('/') and not member.endswith('.zip'):payload[member]=previous.read(member)
assert not broken,broken
payload['documentation_verification.json']=json.dumps({'report_links_checked':links,'broken_links':broken,
 'old_report_sections_preserved':True,'new_framework_or_model_changes':False},indent=2).encode()
manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(payload.items())}
payload['SHA256_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
output=root/'results/cultural_visual_improvement_review.zip'
with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,data in sorted(payload.items()):archive.writestr(name,data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None and len(archive.namelist())==len(set(archive.namelist()))
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==h for name,h in manifest.items())
receipt={'path':output.relative_to(root).as_posix(),'bytes':output.stat().st_size,'sha256':sha(output),
 'manifest_members_verified':len(manifest),'CRC':'PASS','tests_passed':440,'completed_conditions':completed,
 'actual_new_generation_calls':attempted,'outside_mask_changes':0,'protected_changes':0,
 'new_output_human_review':'PENDING','broken_report_links':broken,'historical_changes_other_than_report':[]}
(p/'package_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
