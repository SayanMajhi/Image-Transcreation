"""Independent reopening/pixel verification. No editor, compositor or model imports."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image,ImageDraw

p=Path(__file__).resolve().parent;c=p/'case1'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(c/'source.jpg')=='06d784865dd559ff33ff54a9d66759c478f74c75a5fdf121a30c6313463fc3b8'
source=Image.open(c/'source.jpg').convert('RGB');a=np.asarray(source)
mask=Image.open(c/'edit_region.png');protected=Image.open(c/'protected_regions.png')
assert mask.mode==protected.mode=='L' and mask.size==protected.size==source.size
assert set(mask.tobytes())==set(protected.tobytes())=={0,255}
editable=np.asarray(mask)==255;excluded=np.asarray(protected)==255
assert editable.any() and not (editable&excluded).any()
region=json.loads((c/'region_provenance.json').read_text())
assert sha(c/'edit_region.png')==region['mask_sha256'] and sha(c/'protected_regions.png')==region['protected_sha256']
assert sha(c/'control_canny.png')==region['control_sha256']
results=[];views=[('Original: Petr Kratochvil, CC0',source)]
for name,title in [('seed42','SDXL seed42'),('seed43','SDXL seed43'),('matched_appearance_baseline','Matched appearance baseline')]:
    path=c/name/'final.png'
    if not path.exists():continue
    image=Image.open(path);assert image.mode=='RGB' and image.size==source.size
    b=np.asarray(image);changed=np.any(a!=b,axis=2);delta=np.abs(a.astype('int16')-b.astype('int16'))
    result={'condition':name,'dimensions':list(image.size),'editable_pixels':int(editable.sum()),
        'image_fraction_editable':float(editable.mean()),'changed_inside_mask':int((changed&editable).sum()),
        'changed_outside_mask':int((changed&~editable).sum()),'protected_differences':int((changed&excluded).sum()),
        'maximum_outside_channel_difference':int(delta[~editable].max()),
        'changed_original_near_white_pixels_inside':int((changed&editable&np.all(a>=245,axis=2)).sum()),
        'source_sha256':sha(c/'source.jpg'),'mask_sha256':sha(c/'edit_region.png'),'output_sha256':sha(path),
        'cultural_score':None,'ground_truth_segmentation_accuracy':None,'scope':'RESEARCH_ONLY'}
    assert result['changed_inside_mask']>0 and result['changed_outside_mask']==result['protected_differences']==0
    if name.startswith('seed'):
        record=json.loads((c/name/'result.json').read_text())
        assert record['status']=='COMPLETED' and record['scope']=='RESEARCH_ONLY' and record['human_approved'] is False
        assert record['output_sha256']==sha(path)
        assert record['geometry']==region['geometry']
        assert Image.open(c/name/'raw.png').size==(512,512)
    (c/f'{name}_independent_pixels.json').write_text(json.dumps(result,indent=2))
    results.append(result);views.append((title,image.copy()))
(p/'independent_verification.json').write_text(json.dumps({'results':results,
    'interpretation':'Locality is numerical only; semantic damage can still occur inside the editable rectangle.'},indent=2))
for filename,box,width in [('comparison.png',None,640),('object_native.png',(200,180,1120,780),None),
                           ('boundary_native.png',(10,130,610,430),None)]:
    panels=[]
    for title,image in views:
        panel=image.crop(box) if box else image.copy()
        if width:panel.thumbnail((width,10000))
        panels.append((title,panel))
    w,h=panels[0][1].size
    canvas=Image.new('RGB',(w*len(panels),h+36),'white');d=ImageDraw.Draw(canvas)
    for i,(title,image) in enumerate(panels):canvas.paste(image,(i*w,36));d.text((i*w+5,10),title,fill='black')
    canvas.save(c/filename)
print(json.dumps(results,indent=2))
