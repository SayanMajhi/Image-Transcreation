"""Independent saved-pixel verification; no compositor or model import."""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image
r=Path(__file__).resolve().parent
request=json.loads((r/'request_B.json').read_text())
for key in ('source','reference','selection','permitted','protected'):
    item=request[key]
    assert hashlib.sha256((r/item['path']).read_bytes()).hexdigest()==item['sha256'],key
s=np.array(Image.open(r/'source.jpg').convert('RGB'))
f=np.array(Image.open(r/'B/final.png').convert('RGB'))
m=np.array(Image.open(r/'permitted.png'))==255
p=np.array(Image.open(r/'protected.png'))==255
c=np.array(Image.open(r/'B/source_removed.png').convert('RGB'))
assert f.shape==s.shape
changed=np.any(f!=s,axis=2)
assert not changed[~m].any()
assert not changed[p].any()
assert np.all(c[m]==255)
assert np.array_equal(c[~m],s[~m])
expected=json.loads((r/'independent_pixel_verification.json').read_text())['B']
assert hashlib.sha256((r/'B/final.png').read_bytes()).hexdigest()==expected['output_sha256']
assert int(changed[m].sum())==expected['changed_inside']
print(json.dumps({'changed_inside':int(changed[m].sum()),'changed_outside':int(changed[~m].sum()),'protected_changed':int(changed[p].sum()),'dimensions':[s.shape[1],s.shape[0]],'result':'PASS'},indent=2))
