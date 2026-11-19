"""Reopen saved source, masks and outputs; independent of editor/compositor code."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw

p=Path(__file__).resolve().parent;old=p.parent/'case1'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(p/'source.jpg')==sha(old/'source.jpg')=='06d784865dd559ff33ff54a9d66759c478f74c75a5fdf121a30c6313463fc3b8'
assert sha(p/'previous_seed43.png')==sha(old/'seed43/final.png')
with Image.open(p/'source.jpg') as im:source=im.convert('RGB')
a=np.asarray(source)
if not (p/'source_decoded.png').exists():source.save(p/'source_decoded.png')
assert np.array_equal(np.asarray(Image.open(p/'source_decoded.png')),a)
with Image.open(p/'edit_region.png') as im:mask=im.copy()
with Image.open(p/'protected_regions.png') as im:protected=im.copy()
assert mask.mode==protected.mode=='L' and mask.size==protected.size==source.size
assert set(mask.tobytes())==set(protected.tobytes())=={0,255}
editable=np.asarray(mask)==255;excluded=np.asarray(protected)==255
previous=np.asarray(Image.open(p/'previous_edit_region.png'))==255
assert editable.any() and not (editable&excluded).any() and not (editable&~previous).any()
spec=json.loads((p/'edit_specification.json').read_text())
assert spec['source_image_sha256']==sha(p/'source.jpg') and spec['mask_sha256']==sha(p/'edit_region.png')
assert spec['protected_sha256']==sha(p/'protected_regions.png')
views=[('Original: Petr Kratochvil, CC0',source),('Previous seed43: user realism 2/5',Image.open(p/'previous_seed43.png').copy())]
results=[]
for condition in ['A','B']:
    final_path=p/condition/'final.png'
    if not final_path.exists():continue
    request=json.loads((p/f'request_{condition}.json').read_text());config=json.loads((p/f'config_{condition}.json').read_text())
    assert request['source_sha256']==sha(p/'source.jpg') and request['mask_sha256']==sha(p/'edit_region.png')
    assert request['protected_sha256']==sha(p/'protected_regions.png') and request['control_sha256']==sha(p/'control_canny.png')
    report=json.loads((p/condition/'result.json').read_text())
    assert report['status']=='COMPLETED' and report['scope']=='RESEARCH_ONLY' and report['human_approved'] is False
    with Image.open(final_path) as im:
        assert im.mode=='RGB' and im.size==source.size;final=im.copy()
    changed=np.any(a!=np.asarray(final),axis=2);delta=np.abs(a.astype('int16')-np.asarray(final).astype('int16'))
    assert not changed[~editable].any() and not changed[excluded].any()
    assert report['output_sha256']==sha(final_path)
    assert Image.open(p/condition/'raw.png').size==(config['processing_size'],)*2
    result={'condition':condition,'dimensions':list(source.size),'mask_dimensions':list(mask.size),
        'editable_pixels':int(editable.sum()),'changed_inside_mask':int(changed[editable].sum()),
        'changed_outside_mask':int(changed[~editable].sum()),'changed_protected_pixels':int(changed[excluded].sum()),
        'maximum_outside_channel_difference':int(delta[~editable].max()),
        'changes_outside_old_allowed_rectangle':int(changed[~previous].sum()),
        'source_sha256':sha(p/'source.jpg'),'mask_sha256':sha(p/'edit_region.png'),
        'protected_sha256':sha(p/'protected_regions.png'),'control_sha256':sha(p/'control_canny.png'),
        'final_sha256':sha(final_path),'raw_sha256':sha(p/condition/'raw.png'),
        'new_background_region_is_not_ground_truth':True,'pixel_integrity_is_not_a_realism_score':True}
    assert result['changed_inside_mask']>0
    (p/f'{condition}_independent_pixels.json').write_text(json.dumps(result,indent=2));results.append(result)
    views.append((f'New {condition}: RESEARCH_ONLY, awaiting user review',final))
(p/'independent_verification.json').write_text(json.dumps(results,indent=2))
for filename,box,width in [('comparison.png',None,640),('object_native.png',(220,190,1230,800),None),
                           ('texture_native.png',(550,360,900,620),None),('boundary_native.png',(70,430,570,780),None)]:
    panels=[]
    for title,im in views:
        panel=im.crop(box) if box else im.copy()
        if width:panel.thumbnail((width,10000))
        panels.append((title,panel))
    w,h=panels[0][1].size;canvas=Image.new('RGB',(w*len(panels),h+40),'white');d=ImageDraw.Draw(canvas)
    for index,(title,im) in enumerate(panels):canvas.paste(im,(index*w,40));d.text((index*w+5,12),title,fill='black')
    canvas.save(p/filename)
print(json.dumps(results,indent=2))
