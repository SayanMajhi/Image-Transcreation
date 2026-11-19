"""Independently inspect saved pixels and hashes; no editing/model implementation imports."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageCms, ImageDraw

root = Path(__file__).resolve().parents[2]
folder = root/'results/appearance_transfer_baseline'
v4 = root/'results/phase7_integration/v4_completed'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
request = json.loads((v4/'reproduce_input_A.json').read_text())
for key,field in [('source.jpg','image_sha256'),('research_mask.png','mask_sha256'),
                  ('protected_regions.png','protected_mask_sha256'),('annotations.json','annotation_sha256')]:
    assert sha(v4/key)==request[field]
original=Image.open(v4/'source.jpg').convert('RGB')
mask=Image.open(v4/'research_mask.png');protected=Image.open(v4/'protected_regions.png')
assert mask.mode==protected.mode=='L' and mask.size==protected.size==original.size
assert set(mask.tobytes())=={0,255} and set(protected.tobytes())=={0,255}
editable=np.asarray(mask)==255; excluded=np.asarray(protected)==255
assert editable.any() and not (editable&excluded).any()
final=Image.open(folder/'run/final.png');alpha=Image.open(folder/'run/alpha.png')
assert final.size==original.size and final.mode=='RGB'
a=np.asarray(original);b=np.asarray(final)
changed=np.any(a!=b,axis=2)
assert not changed[~editable].any() and not changed[excluded].any()
assert not np.asarray(alpha)[~editable].any()
rgb=ImageCms.createProfile('sRGB');lab=ImageCms.createProfile('LAB')
to_lab=lambda im: np.asarray(ImageCms.profileToProfile(im,rgb,lab,outputMode='LAB')).astype(float)
la,lb=to_lab(original),to_lab(final)
light_a=la[:,:,0]*100/255;light_b=lb[:,:,0]*100/255
gy_a,gx_a=np.gradient(light_a);gy_b,gx_b=np.gradient(light_b)
gradient_a=np.hypot(gx_a,gy_a)[editable];gradient_b=np.hypot(gx_b,gy_b)[editable]
result={'method':'DETERMINISTIC_APPEARANCE_TRANSFER_BASELINE','scope':'RESEARCH_ONLY',
 'dimensions':list(final.size),'editable_pixels':int(editable.sum()),
 'changed_inside_mask':int(changed[editable].sum()),'changed_outside_mask':int(changed[~editable].sum()),
 'changed_in_protected_regions':int(changed[excluded].sum()),
 'max_outside_channel_difference':int(np.abs(a.astype(int)-b.astype(int))[~editable].max()),
 'mean_absolute_L_difference_inside':float(np.abs(light_b-light_a)[editable].mean()),
 'mean_a_difference_inside':float((lb[:,:,1]-la[:,:,1])[editable].mean()),
 'mean_b_difference_inside':float((lb[:,:,2]-la[:,:,2])[editable].mean()),
 'luminance_gradient_magnitude_correlation_inside':float(np.corrcoef(gradient_a,gradient_b)[0,1]),
 'source_sha256':sha(v4/'source.jpg'),'mask_sha256':sha(v4/'research_mask.png'),
 'protected_sha256':sha(v4/'protected_regions.png'),'final_sha256':sha(folder/'run/final.png'),
 'no_ground_truth_scores':True,'note':'LAB/gradient differences describe appearance only, not realism or cultural quality.'}
(folder/'pixel_verification.json').write_text(json.dumps(result,indent=2))
views=[('Original: 10Rosso, CC BY 2.0',original),('SD A: visual FAIL',Image.open(v4/'A/final.png')),
 ('SD B: visual FAIL',Image.open(v4/'B/final.png')),('Deterministic appearance baseline',final)]
def comparison(path,box=None,width=None):
    panels=[]
    for label,im in views:
        p=im.crop(box) if box else im.copy()
        if width: p.thumbnail((width,10000))
        panels.append((label,p))
    w,h=panels[0][1].size
    canvas=Image.new('RGB',(w*len(panels),h+40),'white');d=ImageDraw.Draw(canvas)
    for i,(label,p) in enumerate(panels):
        canvas.paste(p,(i*w,40));d.text((i*w+5,12),label,fill='black')
    canvas.save(folder/path)
comparison('original_diffusion_baseline.png',width=800)
comparison('noodles_native.png',box=(500,700,1400,1300))
comparison('boundaries_native.png',box=(100,420,1100,1000))
# A separate original/baseline comparison retains full native resolution.
canvas=Image.new('RGB',(original.width*2,original.height+40),'white')
canvas.paste(original,(0,40));canvas.paste(final,(original.width,40))
d=ImageDraw.Draw(canvas);d.text((8,12),'Original: 10Rosso, CC BY 2.0',fill='black')
d.text((original.width+8,12),'Modified: deterministic RESEARCH_ONLY appearance baseline',fill='black')
canvas.save(folder/'original_baseline_native.png')
print(json.dumps(result,indent=2))
