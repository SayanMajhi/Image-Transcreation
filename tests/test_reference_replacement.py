"""Synthetic classical-compositor tests; no human approvals or model inference."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
from transcreation.stages.reference_replacement import replace_object, run_request, METHOD


class ReferenceReplacementTests(unittest.TestCase):
    def setUp(self):
        self.source = Image.new("RGB", (80, 50), (180, 30, 20))
        self.reference = Image.new("RGB", (20, 30), (90, 100, 110))
        self.selection = Image.new("L", self.reference.size)
        self.selection.paste(255, (2, 3, 18, 27))
        self.permitted = Image.new("L", self.source.size)
        self.permitted.paste(255, (5, 5, 75, 45))
        self.protected = Image.fromarray(255-np.asarray(self.permitted))
        self.args = dict(scope="RESEARCH_ONLY", target_width=16, position=(20, 10),
                         background_rgb=[255,255,255], shadows=[], edge_radius=0)

    def run_replacement(self, **changes):
        args = self.args | changes
        return replace_object(self.source,self.reference,self.selection,self.permitted,self.protected,**args)

    def test_entire_source_erased_before_placement(self):
        final, clean, _, _ = self.run_replacement()
        region = np.asarray(self.permitted)>0
        self.assertTrue(np.all(np.asarray(clean)[region]==255))
        self.assertTrue(np.all(np.asarray(final)[15,25]==[90,100,110]))
        self.assertFalse(np.any(np.all(np.asarray(final)[region]==[180,30,20],axis=1)))

    def test_outside_and_protected_pixels_exact(self):
        result, _, alpha, shadow = self.run_replacement(shadows=[dict(ellipse=[15,30,60,40],opacity=.2,blur=8)])
        outside = np.asarray(self.permitted)==0
        self.assertTrue(np.array_equal(np.asarray(result)[outside],np.asarray(self.source)[outside]))
        self.assertFalse(np.asarray(alpha)[outside].any())
        self.assertFalse(np.asarray(shadow)[outside].any())

    def test_uniform_scale_and_crop_mapping(self):
        _, _, alpha, _ = self.run_replacement(target_width=24, position=(20,8))
        self.assertEqual(alpha.getbbox(),(20,8,44,44))

    def test_fixed_reference_box_preserves_mapping(self):
        self.selection.paste(0,(2,3,3,27))
        _,_,alpha,_ = self.run_replacement(reference_box=[2,3,18,27])
        self.assertEqual(alpha.getbbox(),(21,10,36,34))

    def test_truncated_reference_rejected(self):
        with self.assertRaises(ValueError): self.run_replacement(reference_box=[3,3,18,27])

    def test_research_only_no_permission_escalation(self):
        for scope in ("AUTOMATED","APPROVED",None):
            with self.assertRaises(ValueError): self.run_replacement(scope=scope)

    def test_invalid_masks_and_protected_overlap(self):
        self.selection.putpixel((5,5),127)
        with self.assertRaises(ValueError): self.run_replacement()
        self.selection.putpixel((5,5),255)
        self.protected.putpixel((20,20),255)
        with self.assertRaises(ValueError): self.run_replacement()

    def test_target_outside_permitted_region_rejected(self):
        with self.assertRaises(ValueError): self.run_replacement(position=(0,0))

    def test_inputs_unchanged_and_deterministic(self):
        before=[x.tobytes() for x in (self.source,self.reference,self.selection,self.permitted,self.protected)]
        a=self.run_replacement(); b=self.run_replacement()
        self.assertEqual(a[0].tobytes(),b[0].tobytes())
        self.assertEqual(before,[x.tobytes() for x in (self.source,self.reference,self.selection,self.permitted,self.protected)])

    def request(self, root):
        d=dict(method=METHOD,scope="RESEARCH_ONLY",parameters=self.args.copy(),
               attribution={"author":"SYNTHETIC TEST ONLY"},annotation_method="synthetic fixture")
        d["parameters"].pop("scope")
        for k in ("source","reference","selection","permitted","protected"):
            p=root/f"{k}.png"; getattr(self,k).save(p)
            d[k]=dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        p=root/"request.json"; p.write_text(json.dumps(d)); return p

    def test_disk_provenance_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); request=self.request(root); output=root/"output"
            result=run_request(request,output)
            self.assertEqual(result["method"],METHOD)
            self.assertIsNone(result["model"])
            self.assertFalse(result["approval"])
            with self.assertRaises(FileExistsError): run_request(request,output)

    def test_tampered_source_and_reference_and_masks_rejected(self):
        for key in ("source","reference","selection","permitted","protected"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); request=self.request(root)
                (root/f"{key}.png").write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                    run_request(request,root/"output")
                self.assertFalse((root/"output").exists())
