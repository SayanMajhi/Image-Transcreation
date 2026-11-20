"""Prepare approved-mask SD1.5 research requests without changing production policy."""
from pathlib import Path
import hashlib, json, shutil, sys
import cv2
import numpy as np
from PIL import Image

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def runs_to_polygons(mask):
    polygons=[]
    for y,row in enumerate(mask):
        x=0
        while x<row.size:
            if not row[x]: x+=1; continue
            start=x
            while x<row.size and row[x]: x+=1
            polygons.append({"label":"approved binary mask run", "points":[[start,y],[x,y],[x,y+1],[start,y+1]]})
    return polygons

def main():
    root=Path(sys.argv[1]); out=root/'approved_puri_experiments'; out.mkdir()
    source=Path('data/chole_puri.jpg'); mask=Path(root/'corrected_review/puri_mask.png')
    seg=Path(root/'sam_puri_0/segmentation.json')
    source_img=Image.open(source).convert('RGB'); m=np.asarray(Image.open(mask).convert('L'))==255
    protected=~m
    protected_path=out/'protected_exclusions.png'; Image.fromarray((protected*255).astype('uint8'),'L').save(protected_path)
    annotation={"scope":"RESEARCH_ONLY","mask_origin":"RESEARCH_MASK_MANUALLY_REFINED",
      "annotation_method":"operator_polygon_trace_with_protected_exclusions","operator":"user-approved research mask; machine-bound exact raster runs",
      "human_approved":False,"cultural_edit_authorized":False,"source_image_sha256":sha(source),
      "original_dimensions":list(source_img.size),"sam_result_sha256":sha(seg),"sam_reference_index":0,
      "sam_reference_mask_sha256":sha(root/'sam_puri_0/mask_0.png'),"target_definition":"Replace puri with recognizable Japanese shrimp and vegetable tempura; preserve all other scene content",
      "boundary_reason":"Use the user-approved corrected puri raster and exact complement as protected exclusion; no expansion beyond the approved mask",
      "editable_polygons":runs_to_polygons(m),"protected_polygons":runs_to_polygons(protected)}
    ann=out/'annotation.json'; ann.write_text(json.dumps(annotation),encoding='utf-8')
    approval={"decision":"APPROVED_FOR_EXPERIMENTAL_IMAGE_GENERATION_ONLY","date":"2026-11-20","scope":"Corrected puri mask only; SD1.5 research runs; no production promotion","source_image":str(source),"source_image_sha256":sha(source),"approved_mask":str(mask),"approved_mask_sha256":sha(mask),"limitations":["Approval does not establish cultural correctness, recognizability, realism, or semantic consistency.","Chickpea curry, orange sauce, plate, background, utensils and unrelated food remain protected.","All outputs remain RESEARCH_ONLY and require human visual assessment."],"approval_recorded":True}
    (out/'approval_record.json').write_text(json.dumps(approval,indent=2)+'\n',encoding='utf-8')
    base={"source_image":str(source),"image_sha256":sha(source),"segmentation_file":str(seg),"segmentation_sha256":sha(seg),"mask_file":str(mask),"mask_sha256":sha(mask),"candidate_index":0,"selection_note":"User-approved corrected puri mask for experimental generation only.","scope":"RESEARCH_ONLY","annotation_file":str(ann),"annotation_sha256":sha(ann),"protected_mask_file":str(protected_path),"protected_mask_sha256":sha(protected_path),"mask_origin":"RESEARCH_MASK_MANUALLY_REFINED","negative_prompt":None}
    prompts=[("A","A realistic Japanese shrimp and vegetable tempura arrangement replacing the puri, matching the original plate, camera perspective, lighting and scale."),("B","A realistic Japanese shrimp and vegetable tempura arrangement replacing the puri, matching the original plate, camera perspective, lighting and scale.",{"steps":30}),("C","A realistic Japanese tempura serving: one recognizable golden shrimp tempura and several crisp vegetable tempura pieces, replacing the puri; preserve the plate, curry, sauce, background, lighting and perspective.")]
    for item in prompts:
        name,prompt,*extra=item; req=dict(base); req['prompt']=prompt
        if extra: req['settings_override']=extra[0]
        (out/f'request_{name}.json').write_text(json.dumps(req,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(approval,indent=2))
if __name__=='__main__': main()
