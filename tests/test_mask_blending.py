"""Small deterministic CPU tests; no model libraries or weights required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

from scripts.blend_mask import constrained_blend, run_blend


class MaskBlendingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = Image.new("RGB", (40, 24), (10, 20, 30))
        self.mask = Image.new("L", self.original.size, 0)
        ImageDraw.Draw(self.mask).rectangle((8, 5, 31, 18), fill=255)
        ImageDraw.Draw(self.mask).rectangle((17, 9, 22, 14), fill=0)  # protected island
        self.hard = Image.composite(Image.new("RGB", self.original.size, (110, 220, 230)), self.original, self.mask)
        self.paths = {"source_image": self.root / "source.png", "mask_file": self.root / "mask.png", "hard_image": self.root / "hard.png"}
        for name, image in [("source_image", self.original), ("mask_file", self.mask), ("hard_image", self.hard)]:
            image.save(self.paths[name])
        self.hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in self.paths.items()}

    def run_case(self, out):
        return run_blend(self.paths["source_image"], self.paths["mask_file"], self.paths["hard_image"], self.hashes, out)

    def test_alpha_restricted_to_mask_including_protected_island(self):
        _, alpha = constrained_blend(self.original, self.hard, self.mask)
        a, m = np.asarray(alpha), np.asarray(self.mask) == 255
        self.assertFalse(np.any(a[~m])); self.assertTrue(np.any((a[m] > 0) & (a[m] < 255)))
        self.assertEqual(alpha.getpixel((20, 12)), 0)

    def test_fixed_radius_and_analytical_rgb_blend(self):
        with patch.object(Image.Image, "filter", return_value=Image.new("L", self.mask.size, 128)) as blur:
            final, alpha = constrained_blend(self.original, self.hard, self.mask)
        self.assertEqual(blur.call_args.args[0].radius, 5)
        self.assertEqual(final.getpixel((10, 7)), (60, 120, 130))
        self.assertEqual(alpha.getpixel((10, 7)), 128)
        self.assertEqual(final.getpixel((0, 0)), (10, 20, 30))

    def test_zero_outside_differences_and_non_square_support(self):
        final, _ = constrained_blend(self.original, self.hard, self.mask)
        self.assertEqual(final.size, (40, 24))
        outside = np.asarray(self.mask) == 0
        self.assertTrue(np.array_equal(np.asarray(final)[outside], np.asarray(self.original)[outside]))

    def test_binary_dimensions_and_empty_mask_validation(self):
        for bad in [Image.new("L", self.mask.size, 128), Image.new("L", self.mask.size, 0),
                    self.mask.convert("RGB"), Image.new("L", (24, 40), 255)]:
            with self.subTest(mode=bad.mode), self.assertRaises(ValueError):
                constrained_blend(self.original, self.hard, bad)

    def test_input_images_and_files_preserved(self):
        pixels = [im.tobytes() for im in (self.original, self.hard, self.mask)]
        files = {p: p.read_bytes() for p in self.paths.values()}
        constrained_blend(self.original, self.hard, self.mask)
        self.run_case(self.root / "output")
        self.assertEqual(pixels, [im.tobytes() for im in (self.original, self.hard, self.mask)])
        self.assertTrue(all(p.read_bytes() == data for p, data in files.items()))

    def test_no_overwrite_existing_output(self):
        out = self.root / "existing"; out.mkdir(); sentinel = out / "final.png"; sentinel.write_bytes(b"user work")
        with self.assertRaises(FileExistsError): self.run_case(out)
        self.assertEqual(sentinel.read_bytes(), b"user work")

    def test_modified_evidence_rejected_even_with_same_pixels(self):
        path = self.paths["mask_file"]; path.write_bytes(path.read_bytes() + b"modified bytes")
        with self.assertRaisesRegex(ValueError, "SHA-256"): self.run_case(self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_invalid_hard_composite_rejected(self):
        hard = self.hard.copy(); hard.putpixel((0, 0), (255, 255, 255))
        with self.assertRaisesRegex(ValueError, "outside"): constrained_blend(self.original, hard, self.mask)

    def test_saved_alpha_result_metadata_and_input_copies(self):
        out = self.root / "output"; record = self.run_case(out)
        self.assertEqual(record["metrics"]["changed_outside_mask"], 0)
        self.assertEqual(record["metrics"]["nonzero_alpha_outside_mask"], 0)
        self.assertEqual(record["model_inference_calls"], 0)
        self.assertFalse(record["human_approved"])
        self.assertEqual((out / "original_mask.png").read_bytes(), self.paths["mask_file"].read_bytes())
        _, expected = constrained_blend(self.original, self.hard, self.mask)
        with Image.open(out / "alpha.png") as image: self.assertEqual(image.tobytes(), expected.tobytes())
        json.loads((out / "blending.json").read_text())


if __name__ == "__main__":
    unittest.main()
