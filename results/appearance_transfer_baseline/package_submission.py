"""Create the final evidence package; no model execution or historical-file writes."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

root=Path(__file__).resolve().parents[2]
folder=root/'results/appearance_transfer_baseline'
v4=root/'results/phase7_integration/v4_completed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((folder/'preservation_before.json').read_text())
changed=[p for p,h in before.items() if not (root/p).exists() or sha(root/p)!=h]
assert not changed, changed
(folder/'preservation_verification.json').write_text(json.dumps({
    'previous_files_checked':len(before),'modified_or_missing':changed,
    'model_config_policy_and_historical_evidence':'all prior snapshotted bytes unchanged',
    'documents_updated':['README.md','reports/final_project_report.md'],
    'document_originals_saved':['README_before.md','final_project_report_before.md'],
    'new_implementation':['src/transcreation/stages/appearance_transfer.py','scripts/appearance_transfer.py'],
    'new_tests':['tests/test_appearance_transfer.py'],
    'new_model_calls':0,'new_parameter_conditions':1},indent=2))
git=subprocess.run(['git','diff','--stat'],cwd=root,capture_output=True,text=True)
(folder/'git_diff_stat.txt').write_text(git.stdout)
(folder/'visual_assessment.json').write_text(json.dumps({
 'assessment_type':'assistant qualitative visual inspection, not human approval or ground truth',
 'inspected':['run/final.png','original_diffusion_baseline.png','boundaries_native.png','noodles_native.png'],
 'geometry_and_highlights':'original strands/detail preserved; better coherence than SD A/B',
 'appearance':'mainly yellow/orange warming, insufficient reddish-brown coating',
 'seams':'faint protected-rectangle transition traces remain',
 'new_objects_or_text':'none synthesized by this non-generative transform',
 'cultural_food_target':'FAIL','appearance_baseline_technical':'PASS',
 'authenticity':'not established','additional_tuning':False},indent=2))

selected={}
def add(p):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.zip'):
        selected[p.relative_to(root).as_posix()]=p.read_bytes()
for name in ('src','scripts','configs','tests'):
    for p in (root/name).rglob('*'):add(p)
for name in ('README.md','pyproject.toml','reports/final_project_report.md'):add(root/name)
for p in folder.rglob('*'):
    if p.name not in ('package_receipt.json','portable_verification.json'):add(p)
for name in ('source.jpg','ATTRIBUTION.md','source_and_license.json','environment.json',
             'reproduce_input_A.json','reproduce_input_B.json','annotations.json','research_mask.png',
             'protected_regions.png','mask_overlay.png','protected_overlay.png','mask_checks.json',
             'A_pixel_verification.json','B_pixel_verification.json','A_execution.json','B_execution.json',
             'automated_execution.json','localization_execution.json','segmentation_execution.json',
             'historical_decision_preservation.json'):
    add(v4/name)
for directory in ('automated','sam/segmentation','localization/grounding'):
    for p in (v4/directory).rglob('*'):add(p)
for condition in ('A','B'):
    for name in ('final.png','raw_generated_crop.png','processing_image.png','processing_mask.png','inpainting.json'):
        add(v4/condition/name)

reproduction='''# Final submission reproduction

Extract this ZIP and work from its root. Install Python 3.11 and the recorded dependencies.
For same-environment PNG hashes use Pillow 13.0.0 / LittleCMS 2.19.

```powershell
python -m pip install -e ".[inpainting]"
$env:PYTHONPATH = (Resolve-Path src).Path
python -B -m scripts.appearance_transfer --refined-input results/phase7_integration/v4_completed/reproduce_input_A.json --out outputs/appearance_reproduction
python -B results/appearance_transfer_baseline/verify_saved.py
$env:HF_HUB_OFFLINE = "1"
python -B -m unittest discover -s tests -v
```

No model weights or Ollama are needed for the classical run. Compare the reproduced final PNG SHA-256 against `results/appearance_transfer_baseline/pixel_verification.json`. Never rerun into existing output folders. The verification script reopens the INCLUDED saved baseline; the reproduction hash check is separate.

The request's old positive prompt is immutable diffusion provenance and is ignored by the classical treatment. Numerical settings are frozen in the appearance module and recorded before processing. No review authorization is inferred.

Original source: Spaghetti aglio e olio, 10Rosso, CC BY 2.0. See included attribution. Appearance/diffusion/comparison images are modified derivatives, no endorsement implied.

The current baseline is more structurally coherent but FAILS the full masala-coating objective. Historical SD A/B FAIL. Automated planning remains REVIEW/zero released candidates. No new models ran in stabilization.

The submission contains selected real V4 A/B final/raw/processing files and metadata, not duplicate historical ZIPs or every duplicate evidence copy. Unchanged full SAM/localization/automated bundles establish baseline provenance. `inpainting.json` also records hashes of duplicate diffusion evidence copies not all repeated here; original complete V4 evidence remains preserved locally and in the prior V4 review ZIP. Old path strings are retained for audit; baseline reproduction uses the included normalized request and local SAM bundle rather than those historical paths.

The historical human decision summary is not a new review. All original private ramen evidence remains unchanged locally. No archived reviewer decision has been cleared.
'''
selected['REPRODUCTION.md']=reproduction.encode()

with tempfile.TemporaryDirectory(prefix='transcreation_submission_') as temp:
    extracted=Path(temp)
    for name,data in selected.items():
        target=extracted/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    env={**os.environ,'PYTHONPATH':str(extracted/'src'),'HF_HUB_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
    def run(args):
        result=subprocess.run([sys.executable,'-B',*args],cwd=extracted,env=env,capture_output=True,text=True)
        assert result.returncode==0,(args,result.stdout[-1000:],result.stderr[-3000:])
        return {'command':args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    reproduced=run(['-m','scripts.appearance_transfer','--refined-input',
        'results/phase7_integration/v4_completed/reproduce_input_A.json','--out','outputs/appearance_reproduction'])
    assert sha(extracted/'outputs/appearance_reproduction/final.png')==sha(folder/'run/final.png')
    pixels=run(['results/appearance_transfer_baseline/verify_saved.py'])
    tests=run(['-m','unittest','discover','-s','tests','-v'])
    assert 'Ran 420 tests' in tests['stderr'] and '\nOK' in tests['stderr']
    help_result=run(['-m','scripts.appearance_transfer','--help'])
    links=[];broken=[]
    for filename in ('README.md','reports/final_project_report.md'):
        p=extracted/filename
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            target=(p.parent/link.split('#')[0]).resolve()
            links.append([filename,link])
            if not target.exists():broken.append([filename,link])
    assert not broken,broken
    result={'reproduction':reproduced,'saved_pixels':pixels,'full_tests':tests,
       'cli_help':help_result,'byte_identical_final':True,'links_checked':len(links),'broken_links':broken,
       'new_model_calls':0,'source_import_root':str(extracted/'src'),
       'note':'Temporary-root CLI reproduction is deterministic verification, not a second parameter condition.'}
    (folder/'portable_verification.json').write_text(json.dumps(result,indent=2))
    selected['results/appearance_transfer_baseline/portable_verification.json']=(folder/'portable_verification.json').read_bytes()

manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(selected.items())}
selected['SHA256_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
output=root/'results/final_project_submission.zip'
with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,data in sorted(selected.items()):archive.writestr(name,data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist())==len(set(archive.namelist()))
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==h for name,h in manifest.items())
receipt={'path':output.relative_to(root).as_posix(),'sha256':sha(output),'bytes':output.stat().st_size,
    'members':len(selected),'crc_and_manifest':'PASS','portable_tests_passed':420,
    'deterministic_reproduction':'PNG SHA-256 identical','locality':'0 outside / 0 protected changes',
    'baseline_visual':'better structure; full cultural-food target FAIL',
    'new_model_calls':0,'previous_files_changed':changed,'no_commit_or_push':True}
(folder/'package_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
