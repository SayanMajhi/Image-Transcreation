"""Independent saved-file checks; no pipeline/model imports or inference."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw


folder = Path(__file__).resolve().parent
request = json.loads((folder/'input.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = folder/'original.webp'
mask_path = folder/'research_mask.png'
protected_path = folder/'protected_regions.png'
final_path = folder/'generation/final.png'
assert sha(source) == request['image_sha256']
assert sha(mask_path) == request['mask_sha256']
assert sha(protected_path) == request['protected_mask_sha256']
assert sha(folder/'annotations.json') == request['annotation_sha256']
with Image.open(source) as im:
    original = im.convert('RGB')
with Image.open(final_path) as im:
    assert im.mode == 'RGB' and im.size == original.size
    final = im.copy()
with Image.open(mask_path) as im:
    assert im.mode == 'L' and im.size == original.size and set(im.tobytes()) <= {0,255}
    mask = im.copy()
with Image.open(protected_path) as im:
    assert im.mode == 'L' and im.size == original.size and set(im.tobytes()) <= {0,255}
    protected = np.asarray(im) == 255
a, b = np.asarray(original), np.asarray(final)
editable = np.asarray(mask) == 255
difference = np.abs(a.astype('int16')-b.astype('int16'))
changed = np.any(a != b,axis=2)
metrics = {
    'dimensions':list(final.size), 'editable_pixels':int(editable.sum()),
    'changed_inside_mask':int((changed & editable).sum()),
    'changed_outside_mask':int((changed & ~editable).sum()),
    'max_outside_mask_channel_difference':int(difference[~editable].max()),
    'protected_region_pixels':int(protected.sum()),
    'editable_protected_intersection':int((editable & protected).sum()),
    'changed_in_protected_regions':int((changed & protected).sum()),
    'image_fraction_edited':float(editable.mean()),
    'mean_rgb_before_inside':a[editable].mean(axis=0).tolist(),
    'mean_rgb_after_inside':b[editable].mean(axis=0).tolist(),
    'source_sha256':sha(source), 'mask_sha256':sha(mask_path),
    'annotation_sha256':sha(folder/'annotations.json'),
    'original_sam_reference_sha256':sha(folder/'sam_reference_mask_1.png'),
    'final_sha256':sha(final_path),
    'verification_scope':'Independent reopened PNG/WEBP RGB arrays; no model call or generation-function metrics reused.',
    'semantic_limit':'Protected geometry is an assistant annotation, not independent human pixel ground truth.'}
assert metrics['changed_outside_mask'] == 0
assert metrics['max_outside_mask_channel_difference'] == 0
assert metrics['changed_in_protected_regions'] == 0
assert metrics['editable_protected_intersection'] == 0
assert metrics['changed_inside_mask'] > 0
(folder/'independent_pixel_verification.json').write_text(json.dumps(metrics,indent=2))
overlay = Image.composite(Image.new('RGB',original.size,'lime'),original,mask.point(lambda v:115 if v else 0))
canvas=Image.new('RGB',(original.width*3,original.height+40),'white')
draw=ImageDraw.Draw(canvas)
for i,(view,label) in enumerate([(original,'original'),(overlay,'manually refined research mask'),
                                (final,'RESEARCH_ONLY: PARTIAL LOCAL TRANSFORMATION')]):
    canvas.paste(view,(i*original.width,40));draw.text((i*original.width+8,12),label,fill='black')
canvas.save(folder/'original_mask_generated.png')
box=(480,340,860,580)
detail=Image.new('RGB',(1140*2,760),'white');draw=ImageDraw.Draw(detail)
for i,(view,label) in enumerate([(original,'original noodle patch'),(final,'single generated patch; unchanged toppings')]):
    detail.paste(view.crop(box).resize((1140,720)),(i*1140,40))
    draw.text((i*1140+8,12),label,fill='black')
detail.save(folder/'generated_closeup.png')
Image.fromarray((changed*255).astype('uint8')).save(folder/'changed_pixels.png')
print(json.dumps(metrics,indent=2))
