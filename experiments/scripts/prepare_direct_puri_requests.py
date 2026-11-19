from pathlib import Path
import hashlib,json,shutil,sys
from PIL import Image

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 root=Path(sys.argv[1]); out=root/'approved_puri_experiments'; bundle=out/'approved_mask_bundle'; bundle.mkdir()
 src=Path('data/chole_puri.jpg'); orig=root/'sam_puri_0'; corrected=root/'corrected_review/puri_mask.png'
 for n in ['original.jpg','source_detection.json','box.png','mask_1.png','mask_2.png','overlay_0.png','overlay_1.png','overlay_2.png']:
  shutil.copyfile(orig/n,bundle/n)
 shutil.copyfile(corrected,bundle/'mask_0.png')
 data=json.loads((orig/'segmentation.json').read_text())
 data['masks'][0]['filename']='mask_0.png'; data['masks'][0]['foreground_pixels']=Image.open(corrected).convert('L').histogram()[255]; data['masks'][0]['mask_box']=list(Image.open(corrected).convert('L').getbbox()); data['observations'].append({'code':'USER_APPROVED_CORRECTED_MASK','message':'Corrected puri mask approved for experimental generation only; not production authorization.'})
 seg=bundle/'segmentation.json'; seg.write_text(json.dumps(data,indent=2)+'\n')
 base={'source_image':str(src),'image_sha256':sha(src),'segmentation_file':str(seg),'segmentation_sha256':sha(seg),'mask_file':str(bundle/'mask_0.png'),'mask_sha256':sha(bundle/'mask_0.png'),'candidate_index':0,'prompt':'A realistic Japanese shrimp and vegetable tempura arrangement replacing the puri, matching the original plate, camera perspective, lighting and scale. Preserve the chickpea curry, orange sauce, plate, other food, background and utensils.','selection_note':'User-approved corrected puri mask for experimental generation only.','scope':'RESEARCH_ONLY'}
 for name,prompt in [('A',base['prompt']),('B',base['prompt']),('C','A realistic Japanese tempura serving: one recognizable golden shrimp tempura and several crisp vegetable tempura pieces replacing the puri; preserve the chickpea curry, orange sauce, plate, other food, background, lighting and perspective.')]:
  req=dict(base); req['prompt']=prompt; (out/f'direct_request_{name}.json').write_text(json.dumps(req,indent=2)+'\n')
 print(json.dumps({'bundle':str(bundle),'mask_sha256':sha(bundle/'mask_0.png'),'segmentation_sha256':sha(seg)},indent=2))
if __name__=='__main__': main()
