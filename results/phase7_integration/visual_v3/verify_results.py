"""Independent full-resolution saved-pixel verification and comparison figures."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw


folder=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with Image.open(folder/'original.webp') as im:
    original=im.convert('RGB')
with Image.open(folder/'research_mask.png') as im:
    assert im.mode=='L' and im.size==original.size and set(im.tobytes())<={0,255}
    editable=np.asarray(im)==255
with Image.open(folder/'protected_regions.png') as im:
    assert im.mode=='L' and im.size==original.size and set(im.tobytes())<={0,255}
    protected=np.asarray(im)==255
assert editable.any() and not (editable & protected).any()
old=folder.parent/'refined_demo/generation/final.png'
with Image.open(old) as im:
    previous=im.convert('RGB')
views=[('Original',original),('V2 text-like failure',previous)]
annotations=json.loads((folder/'annotations.json').read_text())
for name in ('A','B'):
    final_path=folder/name/'final.png'
    if not final_path.exists():continue
    request=json.loads((folder/f'input_{name}.json').read_text())
    assert sha(folder/'original.webp')==request['image_sha256']
    assert sha(folder/'research_mask.png')==request['mask_sha256']
    assert sha(folder/'annotations.json')==request['annotation_sha256']
    assert sha(folder/'protected_regions.png')==request['protected_mask_sha256']
    with Image.open(final_path) as im:
        assert im.size==original.size and im.mode=='RGB'
        final=im.copy()
    a,b=np.asarray(original),np.asarray(final)
    change=np.any(a!=b,axis=2)
    differences=np.abs(a.astype('int16')-b.astype('int16'))
    regions=[]
    for region in annotations['editable_polygons']:
        layer=Image.new('L',original.size)
        ImageDraw.Draw(layer).polygon([tuple(p) for p in region['points']],fill=255)
        pixels=(np.asarray(layer)==255)&editable
        regions.append({'label':region['label'],'editable_pixels':int(pixels.sum()),
                        'changed_pixels':int((change & pixels).sum())})
    result={'experiment':name,'dimensions':list(final.size),'editable_pixels':int(editable.sum()),
        'changed_inside_mask':int((change & editable).sum()),'changed_outside_mask':int((change & ~editable).sum()),
        'maximum_outside_channel_difference':int(differences[~editable].max()),
        'changed_in_protected_regions':int((change & protected).sum()),
        'protected_region_pixels':int(protected.sum()),'protected_editable_intersection':0,
        'source_image_percent_editable':float(editable.mean()*100),'noodle_coverage_percentage':None,
        'regions':regions,'hashes':{p.name:sha(p) for p in [folder/'original.webp',folder/'research_mask.png',folder/'annotations.json',folder/'protected_regions.png',final_path]},
        'verification':'All reopened decoded RGB pixels; independent from generation/compositing implementation.',
        'semantic_limit':'Exclusions are assistant operator annotations, not independent pixel ground truth.'}
    assert result['changed_inside_mask']>0 and result['changed_outside_mask']==0
    assert result['changed_in_protected_regions']==0 and result['maximum_outside_channel_difference']==0
    (folder/f'{name}_pixel_verification.json').write_text(json.dumps(result,indent=2))
    views.append((f'Experiment {name}: RESEARCH_ONLY',final))
    print(json.dumps({k:result[k] for k in ['experiment','changed_inside_mask','changed_outside_mask','changed_in_protected_regions']},indent=2))
width,height=original.size
canvas=Image.new('RGB',(width*len(views),height+40),'white');draw=ImageDraw.Draw(canvas)
for index,(label,view) in enumerate(views):
    canvas.paste(view,(index*width,40));draw.text((index*width+8,12),label,fill='black')
canvas.save(folder/'original_v2_A_B_comparison.png')
for name,box in [('central',(480,340,970,710)),('lower_left',(320,665,475,885))]:
    w,h=box[2]-box[0],box[3]-box[1]
    detail=Image.new('RGB',(w*len(views),h+40),'white');draw=ImageDraw.Draw(detail)
    for index,(label,view) in enumerate(views):
        detail.paste(view.crop(box),(index*w,40))
        draw.text((index*w+4,12),['Original','V2 failure','Experiment A','Experiment B'][index],fill='black')
    detail.save(folder/(name+'_native_comparison.png'))
