"""Package an explicitly incomplete human-analysis record; do not parse the key."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

root=Path(__file__).resolve().parents[3]
folder=root/'results/phase8_cultural_validation/human_evaluation_analysis'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=json.loads((folder/'preservation_before.json').read_text())
changed=[name for name,h in before.items() if not (root/name).is_file() or sha(root/name)!=h]
assert not changed,changed
summary=json.loads((folder/'evaluation_summary.json').read_text())
assert summary['actual_completed_response_files_imported']==0 and summary['private_key_parsed'] is False
assert all(x['decision']=='INSUFFICIENT_EVIDENCE' and x['cultural_relevance_ratings'] is None for x in summary['candidates'])
tests=json.loads((folder/'regression_tests.json').read_text())
assert tests['returncode']==0 and 'Ran 440 tests' in tests['stderr'] and '\nOK' in tests['stderr']
(folder/'preservation_verification.json').write_text(json.dumps({'original_phase8_files_checked':len(before),
    'original_files_changed':changed,'report_original_prefix_preserved':(root/'reports/cultural_transcreation_validation.md').read_bytes().startswith((folder/'report_before.md').read_bytes()),
    'raw_reviewer_response_files_received':0,'private_key_parsed':False,'candidate_conditions_unblinded_for_analysis':False,
    'models_or_policies_changed':False,'new_model_calls':0},indent=2))
payload={}
prior=root/'results/cultural_validation_review.zip'
with zipfile.ZipFile(prior) as archive:
    manifest=json.loads(archive.read('SHA256_MANIFEST.json'))
    for name,h in manifest.items():
        # Historical labeled evidence is retained for the mentor, not the blinded reviewers.
        # The private key itself stays local until response finalization.
        if name.endswith('/admin/blinding_key.json') or name in ('README.md','reports/cultural_transcreation_validation.md'):continue
        payload[name]=archive.read(name)
        assert hashlib.sha256(payload[name]).hexdigest()==h
payload['reports/cultural_transcreation_validation.md']=(root/'reports/cultural_transcreation_validation.md').read_bytes()
for f in folder.rglob('*'):
    if f.is_file() and f.name not in ('package_receipt.json',) and '__pycache__' not in f.parts:
        payload[f.relative_to(root).as_posix()]=f.read_bytes()
readme='''# Human-evaluation analysis: INSUFFICIENT_EVIDENCE

No genuine completed reviewer forms were provided. Only the header-only template exists. No raw response files were imported, no reviewer identity/expertise/inspection/rating was invented, and missing values were not scored as zero.

Read reports/cultural_transcreation_validation.md section 15 and results/phase8_cultural_validation/human_evaluation_analysis/evaluation_summary.md.

All three blinded candidates are INSUFFICIENT_EVIDENCE. The original threshold is retained verbatim; no ranking, mean, agreement metric or cultural PASS/FAIL is inferred from absent data. No six-case pilot proposal was created.

The original private key was located and its SHA-256 verified without parsing. Candidate-to-condition analysis is withheld until all actual responses are finalized, as required by the user. Accordingly the key/mapping is NOT included in this incomplete packet; its original local path and hash are recorded. This is an explicit missing deliverable, not a completed unblinded evaluation.

This is an ANALYST/MENTOR bundle. It includes unchanged historical labeled outputs and research documentation to preserve report links and provenance. Do not send the full bundle to blinded reviewers. Give them ONLY results/phase8_cultural_validation/human_evaluation/reviewer_materials/. Its candidate IDs, instructions and images are unchanged.

Original templates are under reviewer_materials, never counted as completed responses. The raw response import manifest is empty. No actual ratings are present. To continue, the user must provide genuine finalized response-file paths from three distinct independent reviewers; earlier unrelated human reviews cannot substitute.

440 offline regressions passed. No new model inference or application/policy changes occurred. Historical reproduction scripts are retained as evidence only: DO NOT RUN THEIR IMAGE-GENERATION COMMANDS for this human-analysis milestone. SHA256_MANIFEST.json covers every other ZIP member.
'''
payload['README.md']=readme.encode('utf-8')
broken=[];count=0
for link in re.findall(r'\]\(([^)]+)\)',payload['reports/cultural_transcreation_validation.md'].decode('utf-8')):
    if '://' in link or link.startswith('#'):continue
    # Resolve paths without requiring a second physical copy of all historical images.
    import posixpath
    name=posixpath.normpath(posixpath.join('reports',link.split('#')[0]));count+=1
    if name not in payload and not any(x.startswith(name.rstrip('/')+'/') for x in payload):broken.append(name)
assert not broken,broken
payload['documentation_verification.json']=json.dumps({'updated_report_local_links_checked':count,'broken_links':broken,
    'private_key_deliberately_not_distributed':True,'actual_completed_raw_responses_included':0},indent=2).encode()
manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(payload.items())}
payload['SHA256_MANIFEST.json']=json.dumps(manifest,indent=2).encode()
output=root/'results/cultural_human_evaluation_review.zip'
with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,data in sorted(payload.items()):archive.writestr(name,data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist())==len(set(archive.namelist()))
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==h for name,h in manifest.items())
receipt={'path':output.relative_to(root).as_posix(),'bytes':output.stat().st_size,'sha256':sha(output),
    'manifest_entries_verified':len(manifest),'CRC_and_hash_verification':'PASS','tests_passed':440,
    'analysis_status':'BLOCKED_MISSING_GENUINE_RESPONSES','all_candidates':'INSUFFICIENT_EVIDENCE',
    'raw_completed_response_files':0,'unblinded_for_analysis':False,'private_key_included':False,
    'historical_phase8_files_changed':changed,'new_model_calls':0,'broken_report_links':broken}
(folder/'package_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
