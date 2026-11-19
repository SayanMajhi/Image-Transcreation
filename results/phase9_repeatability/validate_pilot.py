"""Independent pilot bookkeeping/provenance checks; no editing or model calls."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
r=Path(__file__).resolve().parent
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((r/'frozen_manifest.json').read_text(encoding='utf-8'))
assert h(r/'frozen_manifest.json')==(r/'frozen_manifest.sha256').read_text().strip()
assert [c['id'] for c in manifest['cases']]==[1,2,3,4,5,6]
assert len(set(c['category'] for c in manifest['cases']))>=2
assert len(set((c['source_culture'],c['target_culture']) for c in manifest['cases']))>=2
for asset in manifest['assets'].values():
    assert h(Path(asset['path']))==asset['sha256'],asset['path']
    assert asset['author'] and asset['license'] and asset['page'].startswith('https://')
records=json.loads((r/'all_pixel_verification.json').read_text())
assert len(records)==8
for case in manifest['cases']:
    i=case['id'];folder=r/f'case{i}'
    review=json.loads((folder/'review_summary.json').read_text())
    assert review['method']=='REFERENCE_GUIDED_COMPOSITING' and review['scope']=='RESEARCH_ONLY'
    assert review['human_review_status']==('PASS' if i==1 else 'PENDING_USER_REVIEW')
    entries=[x for x in records if x['case']==i]
    assert len(entries)==(1 if i==1 else (2 if i in (3,5) else 1))
    for record in entries:
        s=np.array(Image.open(record['source_path']).convert('RGB'))
        f=np.array(Image.open(record['output_path']).convert('RGB'))
        mask=np.array(Image.open(record['mask_path']))
        assert s.shape==f.shape and mask.shape==s.shape[:2]
        assert set(np.unique(mask))<={0,255}
        changed=np.any(s!=f,axis=2)
        assert not changed[mask==0].any()
        assert int(changed[mask>0].sum())==record['changed_inside']>0
        assert h(Path(record['source_path']))==record['source_sha256']
        assert h(Path(record['mask_path']))==record['mask_sha256']
        assert h(Path(record['output_path']))==record['output_sha256']
        assert record['protected_differences']==0
        assert record['protected_pixels']>0
assert h(r/'case1/final.png')==manifest['cases'][0]['existing_output_sha256']
print(json.dumps({'result':'PASS','cases':6,'saved_outputs_independently_reopened':len(records),'max_new_conditions_per_case':2,'outside_region_changes':0,'protected_differences':0,'frozen_manifest_verified':True,'new_human_reviews':0},indent=2))
