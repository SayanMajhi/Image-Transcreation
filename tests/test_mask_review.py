"""Offline mask-review fixtures are synthetic, never real human approvals."""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from scripts.review_grounding import digest
from scripts.review_mask import ACCEPT, decide, main, prepare, read_candidate
from transcreation.contracts import GroundingDetection, GroundingResult, SamPoint, SegmentationInput, SegmentationMask, SegmentationResult


class MaskReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        Image.new("RGB", (60, 40), "white").save(self.source / "original.png")
        image_hash = digest((self.source / "original.png").read_bytes())
        prediction = GroundingDetection((5, 5, 45, 35), .8, "synthetic object")
        grounding = GroundingResult(image_hash, (60, 40), "synthetic object", "test detector", "a" * 40,
                                    "DETECTED", (prediction,), {}, {}, {}, {})
        (self.source / "source_detection.json").write_text(json.dumps(asdict(grounding)), encoding="utf-8")
        request = SegmentationInput("unused-original-path.png", image_hash, (60, 40), "unused-detector-path.json",
                                     digest((self.source / "source_detection.json").read_bytes()), 0, prediction,
                                     "synthetic object", "test detector", "a" * 40, "RESEARCH_ONLY", "Synthetic fixture")
        masks = []
        for index, (bounds, score) in enumerate([((8, 8, 31, 26), .95), ((10, 10, 29, 25), .7)]):
            image = Image.new("L", (60, 40), 0)
            draw = ImageDraw.Draw(image)
            draw.rectangle((bounds[0], bounds[1], bounds[2]-1, bounds[3]-1), fill=255)
            filename = f"mask_{index}.png"
            image.save(self.source / filename)
            Image.new("RGB", (60, 40), "green").save(self.source / f"overlay_{index}.png")
            masks.append(SegmentationMask(index, filename, (60, 40), score, image.histogram()[255], bounds, "VALID"))
        Image.new("RGB", (60, 40), "white").save(self.source / "box.png")
        self.result = SegmentationResult(request, "facebook/sam-vit-base", "b" * 40, "SEGMENTED", tuple(masks), 0,
                                         {"model_id":"facebook/sam-vit-base", "revision":"b" * 40,
                                          "source_image_copy":"original.png", "source_detection_copy":"source_detection.json"},
                                         {}, {}, ())
        self.segmentation = self.source / "segmentation.json"
        self.save_source()
        self.case = self.root / "review"
        requests = prepare(self.segmentation, self.case, (0, 1), "Synthetic visible body only", "Synthetic segmentation test")
        self.request = requests[1]
        self.out = self.case / "decision.json"

    def save_source(self):
        self.segmentation.write_text(json.dumps(asdict(self.result)), encoding="utf-8")

    def accept(self, **overrides):
        fields = dict(index=1, inspected_original=True, inspected_mask=True, inspected_overlay=True)
        fields.update(overrides)
        return decide(self.request, self.out, ACCEPT, "synthetic named reviewer", "Unit-test declaration only", **fields)

    def mutate(self, path, fields):
        data = json.loads(path.read_text())
        data.update(fields)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_explicit_valid_lower_score_acceptance(self):
        record = self.accept()
        self.assertEqual(record["selected_mask_index"], 1)
        self.assertEqual(record["sam_score"], .7)
        image = read_candidate(self.out)
        self.assertEqual(image.mode, "L")
        self.assertEqual(image.histogram()[255], record["foreground_pixels"])
        self.assertEqual(record["selected_mask_sha256"], digest((self.case / "mask_1.png").read_bytes()))

    def test_reject_does_not_release_a_mask(self):
        record = decide(self.request, self.out, "REJECT", "synthetic named reviewer", "Not suitable", None, True, True, True)
        self.assertIsNone(record["selected_mask_index"])
        with self.assertRaises(ValueError): read_candidate(self.out)

    def test_needs_review_does_not_release_a_mask(self):
        decide(self.request, self.out, "NEEDS_REVIEW", "synthetic named reviewer", "Extent unresolved", None, True, True, True)
        with self.assertRaises(ValueError): read_candidate(self.out)

    def test_pending_has_no_fabricated_human_confirmation(self):
        record = json.loads(self.request.read_text())
        self.assertEqual(record["decision"], "PENDING")
        for key in ("selected_mask_index", "selected_mask_sha256", "reviewer", "reviewed_at_utc", "candidate_kind"):
            self.assertIsNone(record[key])
        self.assertFalse(record["inspected_original"])
        with self.assertRaises(ValueError): read_candidate(self.request)

    def test_placeholder_reviewers_rejected(self):
        for name in ("", " ", "YOUR_NAME", "Your Name", "your-name", "YOURNAME", "N/A", "unknown", "<your name>"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                decide(self.request,self.out,ACCEPT,name,"test",1,True,True,True)
        self.assertFalse(self.out.exists())

    def test_invalid_or_mismatched_candidate_index(self):
        for index in (None, -1, 2, 0, True, 1.0):
            with self.subTest(index=index), self.assertRaises(ValueError): self.accept(index=index)

    def test_missing_candidate_selection_not_default_zero(self):
        with self.assertRaises(ValueError):
            prepare(self.segmentation,self.root/"none",(),"target","experiment")
        with self.assertRaises(ValueError): self.accept(index=None)

    def test_modified_selected_png_bytes_rejected(self):
        mask = self.case / "mask_1.png"
        mask.write_bytes(mask.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError,"snapshot/hash"): self.accept()

    def test_modified_unselected_png_also_breaks_manifest(self):
        mask = self.case / "mask_0.png"
        mask.write_bytes(mask.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError,"snapshot/hash"): self.accept()

    def test_source_image_hash_mismatch(self):
        source = self.case / "original.png"
        source.write_bytes(source.read_bytes()+b"changed")
        with self.assertRaises(ValueError): self.accept()

    def test_segmentation_json_hash_mismatch(self):
        source = self.case / "segmentation.json"
        source.write_bytes(source.read_bytes()+b"\n")
        with self.assertRaisesRegex(ValueError,"snapshot/hash"): self.accept()

    def test_foreground_count_mismatch_before_preparation(self):
        data = json.loads(self.segmentation.read_text())
        data["masks"][1]["foreground_pixels"] += 1
        self.segmentation.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"foreground count"):
            prepare(self.segmentation,self.root/"bad_count",(1,),"target","experiment")

    def test_review_metadata_count_tampering_rejected(self):
        self.mutate(self.request,{"foreground_pixels":1})
        with self.assertRaisesRegex(ValueError,"snapshot/hash"): self.accept()

    def test_nonbinary_mask_rejected(self):
        path = self.source / "mask_1.png"
        with Image.open(path) as image: changed = image.copy()
        changed.putpixel((15,15),127);changed.save(path)
        with self.assertRaisesRegex(ValueError,"0 or 255"):
            prepare(self.segmentation,self.root/"bad_pixels",(1,),"target","experiment")

    def test_wrong_mask_dimensions_rejected(self):
        Image.new("L",(30,20),255).save(self.source/"mask_1.png")
        with self.assertRaises(ValueError):
            prepare(self.segmentation,self.root/"bad_size",(1,),"target","experiment")

    def test_missing_mask_rejected(self):
        (self.case/"mask_1.png").unlink()
        with self.assertRaises(OSError): self.accept()

    def test_original_mask_overlay_inspection_required_for_every_decision(self):
        for decision in (ACCEPT,"REJECT","NEEDS_REVIEW"):
            for flags in ((False,True,True),(True,False,True),(True,True,False)):
                with self.subTest(decision=decision,flags=flags), self.assertRaises(ValueError):
                    decide(self.request,self.out,decision,"synthetic named reviewer","test",1 if decision==ACCEPT else None,*flags)

    def test_editing_diffusion_cultural_permissions_stay_false(self):
        record = self.accept()
        self.assertEqual(record["source_selection_status"],"RESEARCH_ONLY")
        for key in ("image_edit_authorized","diffusion_authorized","cultural_transformation_authorized"):
            self.assertIs(record[key],False)
        self.mutate(self.out,{"diffusion_authorized":True})
        with self.assertRaises(ValueError): read_candidate(self.out)

    def test_parent_request_hash_preserved_and_verified(self):
        self.accept()
        self.request.write_bytes(self.request.read_bytes()+b"\n")
        with self.assertRaisesRegex(ValueError,"audit hash"): read_candidate(self.out)

    def test_accepted_target_scope_cannot_change(self):
        self.accept()
        self.mutate(self.out,{"target_definition":"Whole image replacement"})
        with self.assertRaisesRegex(ValueError,"scope changed"): read_candidate(self.out)

    def test_accepted_selected_mask_cannot_change(self):
        self.accept()
        self.mutate(self.out,{"selected_mask_index":0})
        with self.assertRaises(ValueError): read_candidate(self.out)

    def test_overlay_tampering_rejected(self):
        path = self.case/"overlay_1.png"
        path.write_bytes(path.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError,"snapshot/hash"): self.accept()

    def test_serialization_source_preservation_and_unchanged_contract(self):
        before = {path.name:path.read_bytes() for path in self.source.iterdir()}
        request_before = self.request.read_bytes()
        record = self.accept()
        self.assertEqual(record,json.loads(self.out.read_text()))
        self.assertEqual(self.request.read_bytes(),request_before)
        self.assertEqual(before,{path.name:path.read_bytes() for path in self.source.iterdir()})
        self.assertEqual(json.loads((self.case/'segmentation.json').read_text()),json.loads(self.segmentation.read_text()))
        self.assertEqual(len(json.loads(self.segmentation.read_text())["masks"]),2)

    def test_no_overwrite_or_rewriting_prior_decisions(self):
        self.accept();before=self.out.read_bytes()
        with self.assertRaises(FileExistsError): self.accept()
        self.assertEqual(before,self.out.read_bytes())
        with self.assertRaises(ValueError):
            decide(self.out,self.case/'new.json','REJECT','synthetic named reviewer','test',None,True,True,True)
        with self.assertRaises(FileExistsError):
            prepare(self.segmentation,self.case,(1,),'target','experiment')

    def test_bicycle_case_triage_is_not_a_human_decision(self):
        case=self.root/'bike'
        requests=prepare(self.segmentation,case,(0,1),'physical parts','test','NEEDS_REVIEW','Known thin-structure failures')
        manifest=json.loads((case/'case.json').read_text())
        self.assertEqual(manifest['preparation_status'],'NEEDS_REVIEW')
        self.assertEqual(manifest['human_decision'],'PENDING')
        self.assertTrue(all(json.loads(path.read_text())['decision']=='PENDING' for path in requests))
        with self.assertRaises(ValueError):read_candidate(case/'case.json')

    def test_point_document_hash_and_prompt_provenance(self):
        document={'annotation_status':'RESEARCH_ONLY_REQUIRES_REVIEW','coordinate_system':'original_image_xy_pixels',
                  'source_image_sha256':self.result.request.image_sha256,'detection_json_sha256':self.result.request.detection_sha256,
                  'prediction_index':0,'target_definition':'synthetic target','points':[{'x':10,'y':10,'label':1}]}
        point_file=self.source/'points.json';point_file.write_text(json.dumps(document))
        Image.new('RGB',(60,40),'white').save(self.source/'points.png')
        request=replace(self.result.request,points=(SamPoint(10,10,1),),point_prompt_file='old-points.json',point_prompt_sha256=digest(point_file.read_bytes()))
        self.result=replace(self.result,request=request,settings={**self.result.settings,'point_prompt_copy':'points.json','point_preview':'points.png'})
        self.save_source()
        case=self.root/'points_review';requests=prepare(self.segmentation,case,(1,),'target','test')
        record=json.loads(requests[0].read_text())
        self.assertEqual(record['prompt_type'],'BOX_PLUS_POINTS')
        self.assertEqual(record['point_document_sha256'],digest(point_file.read_bytes()))
        (case/'points.json').write_bytes(point_file.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'point document'):
            decide(requests[0],case/'accepted.json',ACCEPT,'synthetic named reviewer','test',1,True,True,True)

    def test_cli_prepare_and_missing_selection(self):
        case=self.root/'cli'
        with redirect_stdout(StringIO()):
            main(['prepare','--segmentation',str(self.segmentation),'--candidates','0','1','--target','test target',
                  '--experiment','test experiment','--out',str(case)])
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            main(['decide','--request',str(case/'pending_0.json'),'--decision',ACCEPT,'--reviewer','synthetic named reviewer',
                  '--reason','test','--inspected-original','--inspected-mask','--inspected-overlay','--out',str(case/'decision.json')])
        self.assertEqual(caught.exception.code,2)

    def test_malformed_segmentation_metadata_rejected(self):
        original=self.segmentation.read_bytes()
        for fields in ({'settings':[]},{'model_id':None},{'resolved_revision':None}):
            self.segmentation.write_bytes(original)
            self.mutate(self.segmentation,fields)
            with self.assertRaises(ValueError):
                prepare(self.segmentation,self.root/'bad_metadata',(1,),'target','experiment')

    def test_duplicate_candidate_ids_rejected(self):
        data=json.loads(self.segmentation.read_text())
        data['masks'][1]['index']=0
        self.segmentation.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            prepare(self.segmentation,self.root/'duplicate',(0,),'target','experiment')
