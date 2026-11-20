from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
p=Path('results/phaseB_mask_review_20261120_01/controlled_diffusion'); src=Image.open('data/chole_puri.jpg').convert('RGB'); mask=Image.open(p.parent/'corrected_review/puri_mask.png'); m=np.asarray(mask)>0; a=np.asarray(src)
outer=(np.asarray(mask.filter(ImageFilter.MaxFilter(5)))>0)&~m
inner=m&~(np.asarray(mask.filter(ImageFilter.MinFilter(5)))>0)
over=a.copy(); over[m]=(over[m]*0.5+np.array([255,0,0])*0.5).astype('uint8')
items=[('Original',src),('Approved puri mask',Image.fromarray(over))]; rows=[]
for n in ['A','B','C','historical_A']:
 f=(p.parent/'approved_puri_experiments/run_A/inpainting.json') if n=='historical_A' else p/f'run_{n}/inpainting.json'
 if not f.exists(): continue
 r=json.loads(f.read_text()); entry={'run':n,'status':r['status'],'prompt':r['request']['prompt'],'settings':r['settings'],'runtime':r['timing'],'VRAM':r['memory'],'visual_assessment':'PENDING_USER_REVIEW','cultural_assessment':'PENDING_USER_REVIEW'}
 if r['status']=='COMPLETED':
  im=Image.open(f.parent/'final.png').convert('RGB'); diff=np.any(np.asarray(im)!=a,axis=2)
  entry.update(changed_protected_pixels=int(diff[~m].sum()),changed_outer_boundary_pixels=int(diff[outer].sum()),changed_inner_boundary_pixels=int(diff[inner].sum()),output_sha256=hashlib.sha256((f.parent/'final.png').read_bytes()).hexdigest(),technical_validation='PASS' if not diff[~m].any() else 'FAIL')
  items.append((f'{n}: '+entry['technical_validation'],im)); items.append((f'{n}: edited object crop',im.crop(mask.getbbox()))); items.append((f'{n}: boundary close-up',im.crop((1700,700,2100,1100))))
 rows.append(entry)
w=1200; cellw=400; cellh=310; sheet=Image.new('RGB',(w,cellh*((len(items)+2)//3)),'white'); d=ImageDraw.Draw(sheet)
for i,(label,im) in enumerate(items):
 x=(i%3)*cellw;y=(i//3)*cellh; im=im.copy();im.thumbnail((390,275));sheet.paste(im,(x,y+30));d.text((x+5,y+8),label,fill='black')
sheet.save(p/'comparison_sheet.png')
(p/'technical_validation.json').write_text(json.dumps(rows,indent=2))
text=['# Controlled SD 1.5 experiments','Research only. All generated-image visual and cultural assessments: PENDING_USER_REVIEW.','A: baseline. B: only steps changed from 20 to 30. C: only object-level prompt changed. Fixed seed 42, guidance 7.5, strength 0.9, 512-square padded processing crop; final 4000 x 2252. Exact prompts, scheduler settings, runtime, VRAM, boundary counts and output hashes are in technical_validation.json and each run/inpainting.json.','Approval and source/mask hashes: approval_record.json. No mask expansion.','The historical A is excluded from this controlled set because its corrected mask was labeled as a SAM candidate. New runs use the refined-mask route.','Execution issue: the relocated virtualenv launcher pointed to a missing old path. Used the bundled Python interpreter with the existing environment packages.']
for r in rows: text.append(f"Run {r['run']}: {r['status']}; validation {r.get('technical_validation','N/A')}; protected changed {r.get('changed_protected_pixels','N/A')}; runtime {r['runtime']}; VRAM {r['VRAM']}")
text+=['New A/B/C failed before inference: pinned SD1.5 model absent from cache. Online retrieval also failed with Windows socket permission error 10013. No new generated candidates. Historical A is shown separately and independently pixel-validated; it is not a newly generated candidate. Restore the pinned model cache before repeating A/B/C.','D not performed: curry replacement target is unspecified; clarification requested. Separate curry results must precede combined editing.','Model limitations: processing downsamples a large source crop to 512 square; exact protected pixels are enforced by final compositing and do not establish natural boundaries, recognizable tempura or cultural correctness. One seed cannot establish robustness.','Recommended next experiment: after human inspection, specify the curry target and run curry-only before comparing sequential and combined-mask edits at fixed settings.','![Comparison](comparison_sheet.png)']
(p/'report.md').write_text('\n\n'.join(text))
print(json.dumps(rows,indent=2))

