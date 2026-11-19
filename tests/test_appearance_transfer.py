"""Classical synthetic-image tests; no models, approvals or real cultural labels."""
import unittest
import numpy as np
from PIL import Image
from transcreation.stages.appearance_transfer import transfer_appearance


class AppearanceTransferTests(unittest.TestCase):
    def setUp(self):
        ramp = np.tile(np.arange(40, 200, 4, dtype=np.uint8), (24, 1))
        self.image = Image.fromarray(np.stack([ramp, ramp, ramp], axis=2))
        m = np.zeros((24, 40), dtype=np.uint8); m[3:21, 5:35] = 255
        self.mask = Image.fromarray(m)
        self.protected = Image.fromarray(255-m)

    def run_transfer(self, **kwargs):
        return transfer_appearance(self.image, self.mask, self.protected, scope=kwargs.get('scope','RESEARCH_ONLY'))

    def test_locality_and_alpha(self):
        result, alpha = self.run_transfer()
        outside = np.asarray(self.mask)==0
        self.assertTrue(np.array_equal(np.asarray(result)[outside], np.asarray(self.image)[outside]))
        self.assertFalse(np.asarray(alpha)[outside].any())
        self.assertTrue(np.any(np.asarray(result)[~outside] != np.asarray(self.image)[~outside]))

    def test_non_square_determinism(self):
        a, _ = self.run_transfer(); b, _ = self.run_transfer()
        self.assertEqual(a.size, (40,24)); self.assertEqual(a.tobytes(), b.tobytes())

    def test_original_preserved(self):
        before = [x.tobytes() for x in (self.image,self.mask,self.protected)]
        self.run_transfer()
        self.assertEqual(before,[x.tobytes() for x in (self.image,self.mask,self.protected)])

    def test_no_permission_escalation(self):
        for scope in ('AUTOMATED', 'APPROVED', None):
            with self.assertRaises(ValueError): self.run_transfer(scope=scope)

    def test_invalid_masks(self):
        for bad in (Image.new('L',(40,24),127), Image.new('L',(40,24)), Image.new('L',(2,2),255)):
            with self.assertRaises(ValueError):
                transfer_appearance(self.image,bad,self.protected,scope='RESEARCH_ONLY')

    def test_protected_intersection(self):
        with self.assertRaises(ValueError):
            transfer_appearance(self.image,self.mask,self.mask,scope='RESEARCH_ONLY')

    def test_texture_ramp_order(self):
        result, _ = self.run_transfer()
        # Spatial ramp remains ordered; editing must not synthesize/rearrange edges.
        row=np.asarray(result)[12,8:32].astype(float).mean(axis=1)
        self.assertTrue(np.all(np.diff(row)>0))

    def test_no_overwrite(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts.appearance_transfer import main
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); request=root/'input.json'
            from test_refined_inpainting import RefinedInpaintingTests
            fixture=RefinedInpaintingTests(); fixture.setUp()
            try:
                import json
                from dataclasses import asdict
                request.write_text(json.dumps(asdict(fixture.request)))
                out=root/'existing';out.mkdir(); marker=out/'keep';marker.write_text('untouched')
                with patch('sys.argv',['appearance_transfer','--refined-input',str(request),'--out',str(out)]):
                    with self.assertRaises(FileExistsError):main()
                self.assertEqual(marker.read_text(),'untouched')
            finally: fixture.doCleanups()
