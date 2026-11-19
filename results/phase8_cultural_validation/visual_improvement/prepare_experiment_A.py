"""One fixed researcher-provided geometry/mask condition; no model or ground truth."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
from types import SimpleNamespace

import cv2
import numpy as np
from PIL import Image,ImageDraw
from huggingface_hub import snapshot_download
from transformers import CLIPTokenizer
from transcreation.stages.inpainting import prepare_crop
from transcreation.stages.instruction_editor import InstructionEditInput,validate_edit

p=Path(__file__).resolve().parent
old=p.parent/'case1'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(old/'source.jpg')=='06d784865dd559ff33ff54a9d66759c478f74c75a5fdf121a30c6313463fc3b8'
assert not (p/'request_A.json').exists(), 'frozen experiment inputs cannot be overwritten'
for name,dest in [('source.jpg','source.jpg'),('seed43/final.png','previous_seed43.png'),
                  ('seed42/final.png','previous_seed42.png'),('target_shape_prototype.png','previous_geometry.png'),
                  ('control_canny.png','previous_canny.png'),('edit_region.png','previous_edit_region.png'),
                  ('protected_regions.png','previous_protected_regions.png')]:
    shutil.copy2(old/name,p/dest)
image=Image.open(p/'source.jpg').convert('RGB');sam=Image.open(old/'sam/segmentation/mask_0.png')
old_mask=np.asarray(Image.open(old/'edit_region.png'))==255
original_pastry=[(60,345),(75,305),(115,280),(180,278),(250,272),(310,253),(400,252),
 (460,265),(510,252),(550,220),(600,200),(665,198),(730,203),(780,229),(815,275),
 (840,330),(885,365),(940,410),(990,458),(1030,485),(1080,495),(1120,520),
 (1160,562),(1180,610),(1188,666),(1180,710),(1160,740),(1120,742),(1075,732),
 (1030,735),(965,725),(900,715),(830,695),(765,690),(700,665),(635,665),
 (565,637),(500,620),(430,590),(355,570),(295,548),(240,525),(205,503),
 (170,498),(130,481),(100,454),(75,425),(55,395),(55,365)]
original_shadow=[(145,438),(260,480),(445,555),(660,620),(890,690),(1155,690),
 (1200,740),(1170,780),(1030,775),(870,745),(675,708),(500,658),(340,604),(230,550),(155,490)]
target_clearance=[(610,232),(690,275),(820,345),(960,425),(1070,490),(1140,540),
 (1150,585),(1090,642),(1000,715),(930,738),(760,724),(590,698),(420,673),
 (270,650),(267,620),(345,515),(435,407),(520,300),(580,245)]
target_shadow=[(280,620),(930,690),(1120,550),(1160,590),(1115,665),(1020,737),
 (900,765),(680,742),(480,710),(300,685),(255,665)]
polygons=[('original_pastry_boundary_allowance',original_pastry),('original_contact_shadow',original_shadow),
          ('target_pyramidal_envelope_clearance',target_clearance),('target_contact_shadow',target_shadow)]
mask=sam.copy();draw=ImageDraw.Draw(mask)
for _,points in polygons:draw.polygon(points,fill=255)
editable=(np.asarray(mask)==255)&old_mask
assert np.all(editable[np.asarray(sam)==255]),'original SAM pastry must not be left behind'
mask=Image.fromarray((editable*255).astype('uint8'));protected=Image.fromarray((~editable*255).astype('uint8'))
mask.save(p/'edit_region.png');protected.save(p/'protected_regions.png')
silhouette=[(610,250),(655,280),(720,318),(785,356),(845,390),(915,430),(980,469),
 (1050,508),(1120,552),(1112,575),(1080,605),(1045,630),(1000,670),(925,715),
 (845,705),(765,697),(680,685),(595,674),(510,662),(425,651),(350,641),(288,628),
 (320,585),(360,535),(405,480),(450,425),(495,367),(540,310),(585,263)]
ridge=[(610,250),(640,305),(675,360),(710,415),(745,470),(782,525),(820,580),
       (855,635),(890,680),(925,715)]
base_fold=[(310,618),(380,631),(450,639),(530,650),(610,660),(690,670),(770,683),
           (850,694),(925,700),(975,658),(1030,615),(1090,560)]
prototype=Image.new('RGB',image.size,'white');d=ImageDraw.Draw(prototype)
d.polygon(silhouette,fill=(160,160,160))
side=[*ridge,(1000,670),(1045,630),(1080,605),(1112,575),(1120,552),(1050,508),
      (980,469),(915,430),(845,390),(785,356),(720,318),(655,280)]
d.polygon(side,fill=(105,105,105));d.line(base_fold,fill=(75,75,75),width=3)
prototype.save(p/'geometry_prototype.png')
edges=cv2.Canny(np.asarray(prototype),100,200)
assert not edges[~editable].any(),'all target geometry must lie in the permitted edit region'
control=Image.fromarray(np.repeat(edges[:,:,None],3,axis=2));control.save(p/'control_canny.png')
overlay=Image.blend(image,Image.composite(Image.new('RGB',image.size,'lime'),image,mask),.25)
overlay.save(p/'mask_overlay.png')
guide_overlay=image.copy();gd=ImageDraw.Draw(guide_overlay);gd.line([*silhouette,silhouette[0]],fill='red',width=3)
gd.line(ridge,fill='blue',width=3);gd.line(base_fold,fill='magenta',width=3);guide_overlay.save(p/'geometry_overlay.png')
diff=Image.fromarray(np.where(old_mask&~editable,255,0).astype('uint8'));diff.save(p/'newly_protected_pixels.png')
config=json.loads((old/'editor_config.json').read_text());config['candidate_seeds']=[43];config['max_candidates']=1
positive='A single photorealistic Indian samosa, three-dimensional pyramidal triangular fried pastry, naturally folded and sealed dough edges, realistic golden-brown bubbly fried crust, subtle surface imperfections, physically plausible volume, natural contact shadow, consistent camera perspective and lighting, one pastry only, unchanged surrounding scene.'
negative='flat illustration, 2D, paper cutout, cartoon, CGI, plastic texture, smooth artificial surface, geometric drawing, extra food, multiple pastries, chutney, lime, salad, garnish, vegetables, additional objects, packaging, text, logo, floating pastry, unnatural shadow, distorted edges'
config['negative_prompt']=negative
(p/'config_A.json').write_text(json.dumps(config,indent=2))
spec={'scope':'RESEARCH_ONLY','human_approved':False,'source_image_sha256':sha(p/'source.jpg'),
 'source_object':'one croissant on white background','target_object':'ONE closed Indian samosa with credible volume and fried crust',
 'must_preserve':['all pixels outside revised original-coordinate region','surrounding white scene, no added props',
                  'camera composition and viewpoint','original lighting direction'],
 'visual_requirements':['recognizable closed pyramidal samosa','three-dimensional thickness','sealed folded pastry edges',
  'naturally uneven golden crust with small fried bubbles','natural contact shadow','no extra food, garnish, utensils or containers'],
 'research_origin':'user-requested guided visual correction; no accepted Qwen plan or new human mask approval',
 'region_method':'union of original SAM0, recorded pastry/target/shadow polygons, intersected with former permitted rectangle',
 'mask_sha256':sha(p/'edit_region.png'),'protected_sha256':sha(p/'protected_regions.png'),
 'sam_reference_sha256':sha(old/'sam/segmentation/segmentation.json'),
 'polygons':[{'label':label,'points':points} for label,points in polygons],
 'guide':{'origin':'researcher-provided 2D perspective envelope, not measured depth or autonomous Qwen output',
          'silhouette':silhouette,'ridge':ridge,'base_fold':base_fold,'Canny_thresholds':[100,200],
          'limitation':'Canny transmits projected edges, not the grayscale face shading or actual physical depth'}}
(p/'edit_specification.json').write_text(json.dumps(spec,indent=2))
working,wm,geometry=prepare_crop(image,mask,SimpleNamespace(processing_size=512,context_margin=32))
working.save(p/'processing_preview.png');wm.save(p/'processing_mask_preview.png')
request={'source_image':str(p/'source.jpg'),'source_sha256':sha(p/'source.jpg'),
 'specification_file':str(p/'edit_specification.json'),'specification_sha256':sha(p/'edit_specification.json'),
 'mask_file':str(p/'edit_region.png'),'mask_sha256':sha(p/'edit_region.png'),
 'protected_file':str(p/'protected_regions.png'),'protected_sha256':sha(p/'protected_regions.png'),
 'crop_box':geometry['crop_box_xyxy'],'prompt':positive,'seed':43,'scope':'RESEARCH_ONLY',
 'control_file':str(p/'control_canny.png'),'control_sha256':sha(p/'control_canny.png')}
(p/'request_A.json').write_text(json.dumps(request,indent=2))
validate_edit(InstructionEditInput(**request),config)
folder=snapshot_download(config['model_id'],revision=config['revision'],local_files_only=True)
tokens={}
for name in ['tokenizer','tokenizer_2']:
    t=CLIPTokenizer.from_pretrained(folder,subfolder=name,local_files_only=True)
    counts={'positive':len(t(positive).input_ids),'negative':len(t(negative).input_ids),'limit':t.model_max_length}
    assert counts['positive']<=counts['limit'] and counts['negative']<=counts['limit'];tokens[name]=counts
metrics={'dimensions':list(image.size),'old_editable_pixels':int(old_mask.sum()),'new_editable_pixels':int(editable.sum()),
 'newly_protected_pixels':int((old_mask&~editable).sum()),'new_pixels_outside_previous_edit_region':int((editable&~old_mask).sum()),
 'missing_original_SAM0_pixels':int(((np.asarray(sam)==255)&~editable).sum()),'editable_protected_overlap':0,
 'geometry':geometry,'mask_sha256':sha(p/'edit_region.png'),'source_sha256':sha(p/'source.jpg')}
(p/'mask_checks_before_generation.json').write_text(json.dumps(metrics,indent=2))
frozen={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'maximum_new_generations':2,
 'experiment_A':{'seed':43,'request_sha256':sha(p/'request_A.json'),'config_sha256':sha(p/'config_A.json'),
  'specification_sha256':sha(p/'edit_specification.json'),'control_sha256':sha(p/'control_canny.png'),
  'tokens':tokens,'changes_from_previous_seed43':['perspective geometry guide','tighter edit region and derived crop','positive prompt','negative prompt'],
  'unchanged':['original photo','checkpoint revisions','512 processing','FP16/offload','24 steps','strength .99','guidance 5','control scale .5','seed43','hard compositor']},
 'experiment_B':'not selected until a specific A failure and single corrective change are documented',
 'causal_limit':'A changes multiple conditions together; cannot identify which change caused any improvement'}
(p/'preregistration_A.json').write_text(json.dumps(frozen,indent=2));print(json.dumps(metrics,indent=2))
