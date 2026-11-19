"""Independent decoded-image verification; no model or pipeline imports."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw


folder=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='062eb9f18e0175dec675f9e1edefd3ef1238837e627727e58b9d9c309fa49d0e'
assert sha(folder/'source.jpg')==expected
with Image.open(folder/'source.jpg') as im: original=im.convert('RGB')
with Image.open(folder/'research_mask.png') as im:
    assert im.mode=='L' and im.size==original.size and set(im.tobytes())<={0,255}
    editable=np.asarray(im)==255
with Image.open(folder/'protected_regions.png') as im:
    assert im.mode=='L' and im.size==original.size and set(im.tobytes())<={0,255}
    protected=np.asarray(im)==255
assert editable.any() and not (editable & protected).any()
views=[('Original: 10Rosso, CC BY 2.0',original)]
for condition in ('A','B'):
    final_path=folder/condition/'final.png'
    if not final_path.exists():continue
    request=json.loads((folder/f'input_{condition}.json').read_text())
    assert request['image_sha256']==expected
    for field,name in [('mask_sha256','research_mask.png'),('annotation_sha256','annotations.json'),
                       ('protected_mask_sha256','protected_regions.png')]:
        assert sha(folder/name)==request[field]
    with Image.open(final_path) as im:
        assert im.mode=='RGB' and im.size==original.size
        final=im.copy()
    a,b=np.asarray(original),np.asarray(final)
    delta=np.abs(a.astype('int16')-b.astype('int16'));changed=np.any(a!=b,axis=2)
    result={'condition':condition,'dimensions':list(final.size),'editable_pixels':int(editable.sum()),
        'changed_inside_mask':int((changed & editable).sum()),'changed_outside_mask':int((changed & ~editable).sum()),
        'maximum_outside_channel_difference':int(delta[~editable].max()),
        'changed_in_protected_regions':int((changed & protected).sum()),'protected_pixels':int(protected.sum()),
        'editable_protected_intersection':int((editable & protected).sum()),
        'image_fraction_editable':float(editable.mean()),'ground_truth_noodle_coverage':None,
        'source_sha256':expected,'mask_sha256':sha(folder/'research_mask.png'),'final_sha256':sha(final_path),
        'verification':'All reopened decoded RGB pixels; independent of diffusion/compositor code.',
        'annotation_limit':'Protected polygons are operator research geometry, not independent pixel ground truth.'}
    assert result['changed_inside_mask']>0
    assert result['changed_outside_mask']==0 and result['maximum_outside_channel_difference']==0
    assert result['changed_in_protected_regions']==0
    (folder/f'{condition}_pixel_verification.json').write_text(json.dumps(result,indent=2))
    views.append((f'Experiment {condition}: RESEARCH_ONLY modified photograph',final))
    print(json.dumps({k:result[k] for k in ['condition','changed_inside_mask','changed_outside_mask','changed_in_protected_regions']},indent=2))
w,h=original.size
comparison=Image.new('RGB',(w*len(views),h+48),'white');draw=ImageDraw.Draw(comparison)
for index,(label,view) in enumerate(views):
    comparison.paste(view,(index*w,48));draw.text((index*w+8,14),label,fill='black')
comparison.save(folder/'original_generated_comparison.png')
for name,box in [('food_native',(500,700,1400,1300)),('boundary_native',(100,420,1100,1000))]:
    cw,ch=box[2]-box[0],box[3]-box[1]
    detail=Image.new('RGB',(cw*len(views),ch+40),'white');draw=ImageDraw.Draw(detail)
    for index,(label,view) in enumerate(views):
        detail.paste(view.crop(box),(index*cw,40));draw.text((index*cw+8,12),label,fill='black')
    detail.save(folder/(name+'_comparison.png'))
