"""Phase 9 pilot runner tests on a synthetic mini-repository (no models, no real photos)."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from transcreation import pilot
from transcreation.stages import reference_replacement as rr
from scripts import pilot as pilot_cli


def _sha(p):
    return pilot.sha256(p)


class PilotFixture:
    """Builds root/{data,req,configs} with six valid cases; CASE_01 historical."""

    CULTURES = [("French", "Indian"), ("German", "French"), ("American", "Japanese"),
                ("Italian", "Moroccan"), ("Moroccan", "Italian"), ("Generic Western", "Japanese")]

    def __init__(self, root: Path):
        self.root = root
        (root / "data").mkdir(parents=True)
        (root / "req").mkdir()
        (root / "configs").mkdir()
        src = Image.new("RGB", (60, 40), (255, 255, 255))
        src.paste((200, 30, 20), (12, 10, 28, 30))           # source object
        src.paste((10, 120, 10), (45, 5, 55, 35))           # protected neighbour
        ref = Image.new("RGB", (20, 20), (250, 250, 250))
        ref.paste((30, 60, 200), (3, 3, 17, 17))
        sel = Image.new("L", (20, 20))
        sel.paste(255, (3, 3, 17, 17))
        permitted = Image.new("L", (60, 40))
        permitted.paste(255, (5, 3, 38, 37))
        protected = Image.new("L", (60, 40))
        protected.paste(255, (42, 0, 60, 40))
        for name, im in (("src.png", src), ("ref.png", ref), ("sel.png", sel),
                         ("permitted.png", permitted), ("protected.png", protected)):
            im.save(root / "data" / name)
        self.images = {}
        for key in ("src", "ref"):
            path = f"data/{key}.png"
            with Image.open(root / path) as im:
                size = list(im.size)
            self.images[key] = {"path": path, "sha256": _sha(root / path), "dimensions": size,
                                "title": key, "creator": "test", "license": "CC0",
                                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                                "source_url": "https://example.org/" + key, "date_accessed": "2026-11-12",
                                "attribution": "synthetic"}
        self.write_request("case1_A", {})
        rr.run_request(root / "req/case1_A.json", root / "hist")
        (root / "data/feedback.json").write_text('{"verbatim": "looks real"}', encoding="utf-8")
        self.manifest = self.build()
        self.save()

    def write_request(self, name, param_changes):
        params = {"target_width": 16, "position": [12, 12], "background_rgb": [255, 255, 255],
                  "edge_radius": 1.0, "shadows": [{"ellipse": [12, 27, 30, 31], "blur": 2, "opacity": 0.2}]}
        params.update(param_changes)
        req = {"method": rr.METHOD, "scope": "RESEARCH_ONLY",
               "attribution": {"license": "CC0"}, "annotation_method": "synthetic rectangle",
               "parameters": params}
        for key, file in (("source", "src.png"), ("reference", "ref.png"), ("selection", "sel.png"),
                          ("permitted", "permitted.png"), ("protected", "protected.png")):
            req[key] = {"path": f"../data/{file}", "sha256": _sha(self.root / "data" / file)}
        path = self.root / "req" / f"{name}.json"
        path.write_text(json.dumps(req), encoding="utf-8")
        return f"req/{name}.json"

    def attempt(self, n, letter, role="primary", changes=None, correction=None):
        rel = self.write_request(f"case{n}_{letter}", changes or {})
        att = {"attempt": letter, "role": role, "request": rel, "request_sha256": _sha(self.root / rel)}
        if correction:
            att["correction"] = correction
        return att

    def build(self):
        cases = []
        for i, (s, t) in enumerate(self.CULTURES, start=1):
            case = {"id": f"CASE_{i:02d}", "status": "NEW", "category": "food" if i < 4 else "headwear",
                    "source_object": "a", "target_object": "b", "source_culture": s, "target_culture": t,
                    "direction": f"{s}->{t}", "semantic_role": "snack", "intended_transformation": "a to b",
                    "source_image": "src", "reference_image": "ref", "preservation_requirements": ["outside unchanged"],
                    "feasibility_concerns": "none", "human_review_status": "PENDING_USER_REVIEW"}
            if i == 1:
                case.update(status="HISTORICAL_BASELINE", human_review_status="PASS",
                            human_feedback={"verbatim": "looks real", "evidence": "data/feedback.json"},
                            historical={"request": "req/case1_A.json", "request_sha256": _sha(self.root / "req/case1_A.json"),
                                        "output": "hist/final.png", "output_sha256": _sha(self.root / "hist/final.png")})
            elif i == 3:
                case["attempts"] = [self.attempt(i, "A"),
                                    self.attempt(i, "B", "correction", {"edge_radius": 2.0}, "softer edge")]
            else:
                case["attempts"] = [self.attempt(i, "A")]
            cases.append(case)
        return {"schema": pilot.SCHEMA, "root": "..", "method": rr.METHOD, "scope": "RESEARCH_ONLY",
                "max_attempts_per_case": 2, "cases": cases, "images": self.images}

    @property
    def path(self):
        return self.root / "configs" / "pilot.json"

    def save(self):
        self.path.write_text(json.dumps(self.manifest), encoding="utf-8")


class PilotTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fx = PilotFixture(self.tmp / "repo")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assertInvalid(self, fragment):
        self.fx.save()
        with self.assertRaises(pilot.ManifestError) as ctx:
            pilot.validate_manifest(self.fx.path)
        self.assertTrue(any(fragment in e for e in ctx.exception.errors), ctx.exception.errors)

    def run_quiet(self, out=None):
        return pilot.run_pilot(self.fx.path, out or self.tmp / "repo/results/run", log=lambda *_: None)


class ManifestValidationTests(PilotTestBase):
    def test_valid_manifest(self):
        summary = pilot.validate_manifest(self.fx.path)
        self.assertEqual((summary["result"], summary["cases"], summary["new_cases"]), ("VALID", 6, 5))

    def test_missing_field_rejected(self):
        del self.fx.manifest["cases"][2]["semantic_role"]
        self.assertInvalid("missing fields")

    def test_duplicate_ids_rejected(self):
        self.fx.manifest["cases"][2]["id"] = "CASE_02"
        self.assertInvalid("duplicate case IDs")

    def test_unsupported_direction_rejected(self):
        case = self.fx.manifest["cases"][3]
        case["direction"] = case["target_culture"] = case["source_culture"]
        self.assertInvalid("unsupported direction")

    def test_direction_must_match_cultures(self):
        self.fx.manifest["cases"][3]["direction"] = "Italian->Japanese"
        self.assertInvalid("unsupported direction")

    def test_invalid_image_path_rejected(self):
        self.fx.manifest["images"]["src"]["path"] = "data/missing.png"
        self.assertInvalid("file not found")

    def test_image_hash_mismatch_rejected(self):
        self.fx.manifest["images"]["ref"]["sha256"] = "0" * 64
        self.assertInvalid("SHA-256 mismatch")

    def test_request_hash_mismatch_rejected(self):
        self.fx.manifest["cases"][1]["attempts"][0]["request_sha256"] = "1" * 64
        self.assertInvalid("request: SHA-256 mismatch")

    def test_missing_licence_rejected(self):
        self.fx.manifest["images"]["src"]["license"] = ""
        self.assertInvalid("missing provenance")

    def test_no_fabricated_approval(self):
        self.fx.manifest["cases"][4]["human_review_status"] = "PASS"
        self.assertInvalid("without verbatim feedback")

    def test_attempt_budget_and_correction_documentation(self):
        case = self.fx.manifest["cases"][2]
        case["attempts"].append(dict(case["attempts"][1], attempt="C"))
        self.assertInvalid("attempts must be 1..2")
        case["attempts"].pop()
        del case["attempts"][1]["correction"]
        self.assertInvalid("documented correction")

    def test_research_scope_required(self):
        self.fx.manifest["scope"] = "AUTOMATED"
        self.assertInvalid("RESEARCH_ONLY")

    def test_diversity_requirements(self):
        for case in self.fx.manifest["cases"]:
            case["category"] = "food"
        self.assertInvalid("two object categories")


class RunVerifyTests(PilotTestBase):
    def test_run_creates_evidence_and_pending_reviews(self):
        summary = self.run_quiet()
        run = Path(summary["run"])
        self.assertEqual((summary["cases_ok"], summary["attempts_executed"]), (6, 6))
        for cid in pilot.CASE_IDS:
            for name in ("final.png", "comparison.jpg", "closeup_native.png", "REVIEW.md", "status.json"):
                self.assertTrue((run / cid / name).is_file(), (cid, name))
        self.assertTrue((run / "CASE_03/attempts.jpg").is_file())
        self.assertIn("PENDING_USER_REVIEW", (run / "CASE_02/REVIEW.md").read_text(encoding="utf-8"))
        rm = json.loads((run / pilot.RUN_MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual((rm["model"], rm["approval"], rm["scope"]), (None, False, "RESEARCH_ONLY"))
        self.assertEqual(json.loads((run / "CASE_03/status.json").read_text())["selected_attempt"], "B")
        # Historical baseline is copied byte-for-byte, not regenerated.
        self.assertEqual(_sha(run / "CASE_01/final.png"), _sha(self.fx.root / "hist/final.png"))

    def test_never_overwrites(self):
        out = self.tmp / "repo/results/run"
        out.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            self.run_quiet(out)

    def test_invalid_manifest_stops_before_output(self):
        self.fx.manifest["images"]["src"]["sha256"] = "0" * 64
        self.fx.save()
        out = self.tmp / "repo/results/run"
        with self.assertRaises(pilot.ManifestError):
            self.run_quiet(out)
        self.assertFalse(out.exists())

    def test_failed_case_recorded_and_others_continue(self):
        self.fx.manifest["cases"][4]["attempts"] = [self.fx.attempt(5, "A", changes={"position": [55, 30]})]
        self.fx.save()
        summary = self.run_quiet()
        self.assertEqual(summary["failed_cases"], ["CASE_05"])
        status = json.loads((Path(summary["run"]) / "CASE_05/status.json").read_text())
        self.assertEqual(status["attempts"][0]["status"], "FAILED")
        self.assertIn("ValueError", status["attempts"][0]["error"])
        self.assertTrue((Path(summary["run"]) / "CASE_06/final.png").is_file())
        verification = pilot.verify_run(summary["run"])
        self.assertEqual(verification["result"], "FAIL")

    def test_verify_pass_and_region_accounting(self):
        run = Path(self.run_quiet()["run"])
        summary = pilot.verify_run(run)
        self.assertEqual(summary["result"], "PASS", summary["failures"])
        checks = summary["cases"][1]["attempts"][0]["checks"]
        self.assertEqual((checks["changed_outside"], checks["protected_changed"],
                          checks["source_residual_pixels_in_region"]), (0, 0, 0))
        self.assertTrue(checks["deterministic_replay_pixel_identical"])
        self.assertTrue(checks["clean_plate_region_is_background"])
        b = checks["inside_breakdown"]
        self.assertEqual(b["target_footprint_pixels"] + b["shadow_only_pixels"] +
                         b["background_reconstruction_only_pixels"], checks["permitted_pixels"])
        self.assertGreater(b["source_object_pixels_replaced_by_background"], 0)
        self.assertTrue((run / pilot.VERIFICATION).is_file())

    def test_verify_detects_tampered_and_missing_outputs(self):
        run = Path(self.run_quiet()["run"])
        final = run / "CASE_02/attempt_A/final.png"
        im = Image.open(final).convert("RGB")
        im.putpixel((0, 0), (0, 0, 0))   # outside the permitted region
        im.save(final)
        (run / "CASE_04/comparison.jpg").unlink()
        summary = pilot.verify_run(run)
        self.assertEqual(summary["result"], "FAIL")
        self.assertIn("CASE_02/attempt_A/final.png", summary["files"]["tampered"])
        self.assertIn("CASE_04/comparison.jpg", summary["files"]["missing"])
        self.assertTrue(any("outside permitted" in f for f in summary["failures"]))

    def test_region_checks_detect_leftover_source(self):
        source = np.full((10, 10, 3), 255, np.uint8)
        source[2:5, 2:5] = (200, 0, 0)
        permitted = np.zeros((10, 10), np.uint8)
        permitted[1:8, 1:8] = 255
        final = source.copy()   # nothing removed
        zeros = np.zeros((10, 10), np.uint8)
        stats = pilot._region_checks(source, final, permitted, zeros, zeros, zeros, [255, 255, 255])
        self.assertEqual(stats["source_residual_pixels_in_region"], 9)

    def test_deterministic_replay_across_runs(self):
        a = Path(self.run_quiet(self.tmp / "repo/results/r1")["run"])
        b = Path(self.run_quiet(self.tmp / "repo/results/r2")["run"])
        for cid in pilot.CASE_IDS:
            self.assertTrue(np.array_equal(pilot._rgb(a / cid / "final.png"), pilot._rgb(b / cid / "final.png")))


class PackageTests(PilotTestBase):
    def test_package_manifest_covers_every_member(self):
        run = Path(self.run_quiet()["run"])
        (self.fx.root / "src/__pycache__").mkdir(parents=True)
        (self.fx.root / "src/__pycache__/x.pyc").write_bytes(b"x")
        out = self.tmp / "repo/results/review.zip"
        summary = pilot.package_run(run, out)
        self.assertEqual((summary["verification"], summary["package_check"]["result"]), ("PASS", "PASS"))
        with zipfile.ZipFile(out) as zf:
            names = set(zf.namelist())
            listed = {line.split("  ", 1)[1] for line in zf.read(pilot.SUMS).decode().splitlines()}
        self.assertEqual(listed, names - {pilot.SUMS})
        self.assertIn("configs/pilot.json", names)
        self.assertIn("data/src.png", names)
        self.assertIn("results/run/CASE_05/final.png", names)
        self.assertFalse(any("__pycache__" in n or n.endswith(".pyc") for n in names))
        with self.assertRaises(FileExistsError):
            pilot.package_run(run, out)

    def test_unzipped_package_reproduces_elsewhere(self):
        """Regression: the ZIP omits phase-9 reference copies, yet must validate/run/verify alone."""
        hist = self.fx.root / "ref_outputs"
        rr.run_request(self.fx.root / "req/case2_A.json", hist)
        att = self.fx.manifest["cases"][1]["attempts"][0]
        att.update(historical_output="ref_outputs/final.png", historical_output_sha256=_sha(hist / "final.png"))
        self.fx.save()
        run = Path(self.run_quiet()["run"])
        out = self.tmp / "review.zip"
        pilot.package_run(run, out)
        with zipfile.ZipFile(out) as zf:
            self.assertNotIn("ref_outputs/final.png", zf.namelist())
            self.assertIn("hist/final.png", zf.namelist())        # the CASE_01 benchmark ships
            zf.extractall(self.tmp / "elsewhere")
        moved = self.tmp / "elsewhere"
        summary = pilot.validate_manifest(moved / "configs/pilot.json")
        self.assertEqual(summary["historical_reference_outputs_absent"], ["ref_outputs/final.png"])
        new_run = Path(pilot.run_pilot(moved / "configs/pilot.json", moved / "results/again", log=lambda *_: None)["run"])
        result = pilot.verify_run(new_run)
        self.assertEqual(result["result"], "PASS", result["failures"])
        checks = result["cases"][1]["attempts"][0]["checks"]
        self.assertTrue(checks["historical_bytes_identical"])

    def test_present_but_altered_reference_output_rejected(self):
        hist = self.fx.root / "ref_outputs"
        rr.run_request(self.fx.root / "req/case2_A.json", hist)
        att = self.fx.manifest["cases"][1]["attempts"][0]
        att.update(historical_output="ref_outputs/final.png", historical_output_sha256="2" * 64)
        self.assertInvalid("historical output: SHA-256 mismatch")

    def test_check_package_detects_hash_mismatch(self):
        run = Path(self.run_quiet()["run"])
        out = self.tmp / "repo/results/review.zip"
        pilot.package_run(run, out)
        bad = self.tmp / "bad.zip"
        with zipfile.ZipFile(out) as src, zipfile.ZipFile(bad, "w") as dst:
            for n in src.namelist():
                data = src.read(n)
                dst.writestr(n, b"tampered" if n == "data/src.png" else data)
        self.assertEqual(pilot.check_package(bad)["hash_mismatch"], ["data/src.png"])


class CliTests(PilotTestBase):
    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pilot_cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_help(self):
        for argv in ([], ["validate"], ["run"], ["verify"], ["package"]):
            with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                pilot_cli.main(argv + ["--help"])
            self.assertEqual(ctx.exception.code, 0)

    def test_full_cli_flow(self):
        run, zp = self.tmp / "repo/results/run", self.tmp / "repo/results/r.zip"
        self.assertEqual(self.call("validate", "--manifest", str(self.fx.path))[0], 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.call("run", "--manifest", str(self.fx.path), "--out", str(run))[0], 0)
        self.assertEqual(self.call("verify", "--run", str(run))[0], 0)
        self.assertEqual(self.call("package", "--run", str(run), "--out", str(zp))[0], 0)
        code, _, err = self.call("run", "--manifest", str(self.fx.path), "--out", str(run))
        self.assertEqual(code, 1)
        self.assertIn("FileExistsError", err)

    def test_invalid_requests_fail_cleanly(self):
        self.fx.manifest["cases"][1]["id"] = "CASE_01"
        self.fx.save()
        code, _, err = self.call("validate", "--manifest", str(self.fx.path))
        self.assertEqual(code, 1)
        self.assertIn("duplicate case IDs", err)
        self.assertEqual(self.call("verify", "--run", str(self.tmp / "nope"))[0], 1)


class PatchFadeTests(unittest.TestCase):
    def setUp(self):
        self.source = Image.new("RGB", (80, 60), (255, 255, 255))
        self.reference = Image.new("RGB", (40, 40), (245, 245, 245))   # off-white studio patch
        self.reference.paste((20, 20, 20), (15, 15, 25, 25))
        self.selection = Image.new("L", (40, 40), 255)
        self.permitted = Image.new("L", (80, 60))
        self.permitted.paste(255, (5, 5, 75, 55))
        self.protected = Image.new("L", (80, 60))
        self.kw = dict(scope="RESEARCH_ONLY", target_width=40, position=(20, 10),
                       background_rgb=[255, 255, 255], shadows=[], edge_radius=0)

    def replace(self, **kw):
        return rr.replace_object(self.source, self.reference, self.selection, self.permitted, self.protected,
                                 **(self.kw | kw))

    def test_default_is_historical_behaviour(self):
        a = self.replace()[0]
        b = self.replace(patch_fade_sigma=0)[0]
        self.assertTrue(np.array_equal(np.asarray(a), np.asarray(b)))
        self.assertEqual(np.asarray(a)[10, 20].tolist(), [245, 245, 245])   # hard patch edge

    def test_fade_softens_border_keeps_object(self):
        final, _, alpha, _ = self.replace(patch_fade_sigma=3)
        arr = np.asarray(final)
        self.assertGreater(arr[10, 20].min(), 250)                     # patch corner faded to plate
        self.assertEqual(arr[30, 40].tolist(), [20, 20, 20])           # object centre untouched
        self.assertFalse(np.asarray(alpha)[np.asarray(self.permitted) == 0].any())

    def test_invalid_fade_rejected(self):
        for bad in (-1, 500, float("nan"), True, "3"):
            with self.assertRaises(ValueError):
                self.replace(patch_fade_sigma=bad)


if __name__ == "__main__":
    unittest.main()
