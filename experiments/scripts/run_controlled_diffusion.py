from pathlib import Path
import json, hashlib
from dataclasses import replace
from PIL import Image
import numpy as np
from transcreation.config import load_inpainting_config
from transcreation.stages.refined_inpainting import RefinedMaskInput, run_refined_inpainting
root=Path('results/phaseB_mask_review_20261120_01'); old=root/'approved_puri_experiments'; out=root/'controlled_diffusion'; out.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=Path('data/chole_puri.jpg')
record={'decision':'APPROVED_FOR_EXPERIMENTAL_IMAGE_GENERATION_ONLY','date':'2026-11-20','source_image':str(source),'source_sha256':sha(source),'approved_masks':{str(root/'corrected_review'/n):sha(root/'corrected_review'/n) for n in ['puri_mask.png','curry_mask.png']},'scope':'Corrected masks only; Japan; preserve all non-target pixels; no production promotion','limitations':['Generated-image visual and cultural assessments PENDING_USER_REVIEW','No mask expansion approved'],'approval_evidence':{'path':r'C:\Users\justg\Downloads\Pasted text.txt','sha256':sha(r'C:\Users\justg\Downloads\Pasted text.txt')}}
(out/'approval_record.json').write_text(json.dumps(record,indent=2))
ann=json.loads((old/'annotation.json').read_text())
m=np.asarray(Image.open(root/'corrected_review/puri_mask.png'))==255
def polys(a):
 result=[]
 for y,row in enumerate(a):
  edges=np.flatnonzero(np.diff(np.r_[False,row,False]))
  for start,end in zip(edges[::2],edges[1::2]):
   result.append({'label':'exact approved raster run','points':[[int(start),y],[int(end-1),y],[int(start),y]]})
 return result
ann['editable_polygons']=polys(m); ann['protected_polygons']=polys(~m)
ap=out/'annotation.json'; ap.write_text(json.dumps(ann))
config=load_inpainting_config(Path('configs/inpainting.yaml'))
for name in ['A','B','C']:
 req=json.loads((old/'request_A.json').read_text()); req['annotation_file']=str(ap); req['annotation_sha256']=sha(ap)
 req['prompt']=json.loads((old/f'direct_request_{name}.json').read_text())['prompt']
 (out/f'request_{name}.json').write_text(json.dumps(req,indent=2))
 cfg=replace(config,steps=30) if name=='B' else config
 print(name,flush=True)
 result=run_refined_inpainting(RefinedMaskInput(**req),cfg,out/f'run_{name}',max_attempts=1)
 print(result['status'],flush=True)
