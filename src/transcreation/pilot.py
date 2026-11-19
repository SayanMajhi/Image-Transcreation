"""Phase 9 six-case repeatability pilot: validate, run, verify and package.

This module only orchestrates the existing REFERENCE_GUIDED_COMPOSITING stage
(`stages.reference_replacement`). It never calls a model, never reads planner
output and never records a human approval: human review fields are copied from the
frozen manifest, where a PASS requires verbatim user feedback evidence.

All manifest paths are relative to the repository root (`root`, resolved from the
manifest's own directory), so the pilot works from any checkout location.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from transcreation.stages import reference_replacement as rr

SCHEMA = "phase9_pilot_cases/v1"
CASE_IDS = [f"CASE_{i:02d}" for i in range(1, 7)]
CASE_FIELDS = ("id", "status", "category", "source_object", "target_object", "source_culture",
               "target_culture", "direction", "semantic_role", "intended_transformation",
               "source_image", "reference_image", "preservation_requirements",
               "feasibility_concerns", "human_review_status")
IMAGE_FIELDS = ("path", "sha256", "dimensions", "title", "creator", "license", "license_url",
                "source_url", "date_accessed", "attribution")
REVIEW_STATUSES = {"PENDING_USER_REVIEW", "PASS", "FAIL", "NEEDS_CHANGES"}
PENDING = "PENDING_USER_REVIEW"
RUN_MANIFEST = "run_manifest.json"
VERIFICATION = "verification_summary.json"
SUMS = "SHA256SUMS.txt"
# Never shipped in a review package.
EXCLUDED_PARTS = {"__pycache__", ".venv", "venv", ".git", ".idea", ".mypy_cache", "node_modules"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".safetensors", ".bin", ".ckpt", ".pt", ".pth", ".onnx", ".gguf", ".zip"}
EXCLUDED_NAMES = {".env", "credentials.json", "token.json"}


class ManifestError(ValueError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("invalid pilot manifest:\n  - " + "\n  - ".join(self.errors))


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path, start) -> str:
    """Portable forward-slash relative path (works across Windows/POSIX checkouts)."""
    import os
    return Path(os.path.relpath(Path(path).resolve(), Path(start).resolve())).as_posix()


def _rgb(path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


# --------------------------------------------------------------------------- manifest

def load_manifest(manifest_path):
    manifest_path = Path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    root = (manifest_path.parent / data.get("root", "..")).resolve()
    return data, root


def _check_file(root, rel, expected_sha, label, errors):
    if not isinstance(rel, str) or not rel:
        errors.append(f"{label}: missing path")
        return None
    path = root / rel
    if not path.is_file():
        errors.append(f"{label}: file not found: {rel}")
        return None
    if expected_sha is not None and sha256(path) != expected_sha:
        errors.append(f"{label}: SHA-256 mismatch for {rel}")
    return path


def validate_manifest(manifest_path, check_files=True) -> dict:
    """Collect every schema, provenance and hash problem; raise ManifestError if any."""
    data, root = load_manifest(manifest_path)
    errors = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if data.get("method") != rr.METHOD or data.get("scope") != "RESEARCH_ONLY":
        errors.append("method/scope must be REFERENCE_GUIDED_COMPOSITING / RESEARCH_ONLY")
    budget = data.get("max_attempts_per_case")
    if budget != 2:
        errors.append("max_attempts_per_case must be 2")
    absent_references = []
    images = data.get("images") or {}
    cases = data.get("cases") or []
    ids = [c.get("id") for c in cases]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate case IDs: {sorted({i for i in ids if ids.count(i) > 1})}")
    if ids != CASE_IDS:
        errors.append(f"cases must be exactly {CASE_IDS} in order, got {ids}")

    for key, img in images.items():
        missing = [f for f in IMAGE_FIELDS if not img.get(f)]
        if missing:
            errors.append(f"image {key}: missing provenance fields {missing}")
            continue
        if not str(img["source_url"]).startswith("https://"):
            errors.append(f"image {key}: source_url must be https")
        if check_files:
            path = _check_file(root, img["path"], img["sha256"], f"image {key}", errors)
            if path is not None:
                with Image.open(path) as im:
                    if list(im.size) != list(img["dimensions"]):
                        errors.append(f"image {key}: dimensions {list(im.size)} != {img['dimensions']}")

    for case in cases:
        cid = case.get("id", "?")
        missing = [f for f in CASE_FIELDS if case.get(f) in (None, "", [])]
        if missing:
            errors.append(f"{cid}: missing fields {missing}")
            continue
        match = re.fullmatch(r"\s*([^>]+?)\s*->\s*([^>]+?)\s*", str(case["direction"]))
        if (not match or match.group(1) == match.group(2) or
                (match.group(1), match.group(2)) != (case["source_culture"], case["target_culture"])):
            errors.append(f"{cid}: unsupported direction {case['direction']!r} "
                          "(must be 'source_culture->target_culture' with different cultures)")
        for role in ("source_image", "reference_image"):
            if case[role] not in images:
                errors.append(f"{cid}: {role} {case[role]!r} has no provenance record")
        status = case["status"]
        review = case["human_review_status"]
        if review not in REVIEW_STATUSES:
            errors.append(f"{cid}: unknown human_review_status {review!r}")
        elif review != PENDING:
            # A decision is only valid with saved verbatim user words; never inferred.
            fb = case.get("human_feedback") or {}
            if not fb.get("verbatim") or not fb.get("evidence"):
                errors.append(f"{cid}: human_review_status {review} without verbatim feedback evidence")
            elif check_files and not (root / fb["evidence"]).is_file():
                errors.append(f"{cid}: human feedback evidence file not found")
        if status == "HISTORICAL_BASELINE":
            hist = case.get("historical") or {}
            if check_files:
                _check_file(root, hist.get("request"), hist.get("request_sha256"), f"{cid} historical request", errors)
                _check_file(root, hist.get("output"), hist.get("output_sha256"), f"{cid} historical output", errors)
            if case.get("attempts"):
                errors.append(f"{cid}: historical baseline must not declare new attempts")
        elif status == "NEW":
            attempts = case.get("attempts") or []
            if not 1 <= len(attempts) <= (budget or 2):
                errors.append(f"{cid}: attempts must be 1..{budget}")
            for index, att in enumerate(attempts):
                label = f"{cid} attempt {att.get('attempt')}"
                if index >= 2 or att.get("attempt") != "AB"[index]:
                    errors.append(f"{label}: attempts must be labelled A then B")
                if index == 0 and att.get("role") != "primary":
                    errors.append(f"{label}: first attempt must be primary")
                if index > 0 and (att.get("role") != "correction" or not att.get("correction")):
                    errors.append(f"{label}: second attempt must be a documented correction")
                if not check_files:
                    continue
                req_path = _check_file(root, att.get("request"), att.get("request_sha256"), f"{label} request", errors)
                if req_path is None:
                    continue
                req = json.loads(req_path.read_text(encoding="utf-8-sig"))
                if req.get("method") != rr.METHOD or req.get("scope") != "RESEARCH_ONLY":
                    errors.append(f"{label}: request is not RESEARCH_ONLY reference compositing")
                for role, key in (("source", "source_image"), ("reference", "reference_image")):
                    img = images.get(case[key], {})
                    if req.get(role, {}).get("sha256") != img.get("sha256"):
                        errors.append(f"{label}: request {role} hash differs from manifest {case[key]}")
                if att.get("historical_output"):
                    if not att.get("historical_output_sha256"):
                        errors.append(f"{label}: historical output without SHA-256")
                    elif (root / att["historical_output"]).is_file():
                        _check_file(root, att["historical_output"], att["historical_output_sha256"],
                                    f"{label} historical output", errors)
                    else:
                        # Reference copy only (not an input): a relocated review package omits
                        # it and verify compares against the recorded hash instead.
                        absent_references.append(att["historical_output"])
        else:
            errors.append(f"{cid}: status must be NEW or HISTORICAL_BASELINE")

    if cases and not errors:
        if sum(c["status"] == "HISTORICAL_BASELINE" for c in cases) != 1 or cases[0]["status"] != "HISTORICAL_BASELINE":
            errors.append("CASE_01 must be the only HISTORICAL_BASELINE")
        if len({c["category"] for c in cases}) < 2:
            errors.append("need at least two object categories")
        if len({c["direction"] for c in cases}) < 2:
            errors.append("need at least two cultural directions")
        if not any(c["status"] == "NEW" and c["target_culture"].lower() != "indian" for c in cases):
            errors.append("at least one NEW case needs a non-Indian target culture")
    freeze = data.get("original_freeze") or {}
    if check_files and freeze:
        _check_file(root, freeze.get("path"), freeze.get("sha256"), "original freeze manifest", errors)
    if errors:
        raise ManifestError(errors)
    return {"result": "VALID", "manifest_sha256": sha256(manifest_path), "root": str(root),
            "cases": len(cases), "new_cases": sum(c["status"] == "NEW" for c in cases),
            "attempts": sum(len(c.get("attempts", [])) for c in cases),
            "categories": sorted({c["category"] for c in cases}),
            "directions": [c["direction"] for c in cases],
            "historical_reference_outputs_absent": absent_references}


# --------------------------------------------------------------------------- review images

def _font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _panel(images, labels, height=520, caption=None):
    """Side-by-side panels of equal height with readable labels."""
    scaled = [im.convert("RGB").resize((max(1, round(im.width * height / im.height)), height),
                                       Image.Resampling.LANCZOS) for im in images]
    gap, top = 16, 44
    bottom = 40 if caption else 12
    sheet = Image.new("RGB", (sum(s.width for s in scaled) + gap * (len(scaled) + 1), height + top + bottom), (236, 236, 236))
    draw, font = ImageDraw.Draw(sheet), _font(22)
    x = gap
    for im, label in zip(scaled, labels):
        sheet.paste(im, (x, top))
        draw.text((x, 12), label, fill=(20, 20, 20), font=font)
        x += im.width + gap
    if caption:
        draw.text((gap, top + height + 8), caption, fill=(60, 60, 60), font=_font(18))
    return sheet


def _detail_box(alpha_bbox, size, max_w=1200, max_h=900):
    """Native-resolution window around the target object (whole object if it fits)."""
    x0, y0, x1, y1 = alpha_bbox
    pad = 40
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(size[0], x1 + pad), min(size[1], y1 + pad)
    w, h = min(x1 - x0, max_w), min(y1 - y0, max_h)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    left = min(max(0, cx - w // 2), size[0] - w)
    top = min(max(0, cy - h // 2), size[1] - h)
    return (left, top, left + w, top + h)


def _review_assets(case_dir, source_path, final_path, alpha_bbox, case, attempt_finals):
    with Image.open(source_path) as s, Image.open(final_path) as f:
        source, final = s.convert("RGB"), f.convert("RGB")
    _panel([source, final], [f"Original: {case['source_object']}", f"Final: {case['target_object']}"],
           caption=f"{case['id']}  {case['direction']}  REFERENCE_GUIDED_COMPOSITING / RESEARCH_ONLY"
           ).save(case_dir / "comparison.jpg", quality=92)
    box = _detail_box(alpha_bbox, source.size)
    _panel([source.crop(box), final.crop(box)], ["Original (native pixels)", "Final (native pixels)"],
           height=box[3] - box[1], caption=f"Native crop {list(box)}").save(case_dir / "closeup_native.png")
    if len(attempt_finals) > 1:
        ims = [source]
        for letter, path in attempt_finals:
            with Image.open(path) as im:
                ims.append(im.convert("RGB"))
        _panel(ims, ["Original"] + [f"Attempt {a}" for a, _ in attempt_finals]).save(case_dir / "attempts.jpg", quality=90)
    return box


def _review_card(case, selected, notes):
    defects = notes.get("defects") or "Not yet inspected."
    lines = [
        f"# {case['id']}: {case['source_object']} -> {case['target_object']}",
        "",
        f"**What changed:** {case['intended_transformation']} ({case['direction']}).",
        f"**Selected attempt:** {selected}.  **Method:** REFERENCE_GUIDED_COMPOSITING / RESEARCH_ONLY "
        "(a real licensed photo was cut out and placed by a researcher; no AI model generated it).",
        f"**Visible defects noted by the assistant:** {defects}",
        "",
        f"HUMAN_REVIEW_STATUS = {case['human_review_status']}",
        "",
        "Open `comparison.jpg`, then `closeup_native.png`"
        + (", then `attempts.jpg`." if len(case.get("attempts", [])) > 1 else "."),
        "",
        "Questions (answer in plain words):",
        "1. Does the new object look real?",
        f"2. Does it look like a {case['target_object']}?",
        "3. Does anything look pasted or unnatural?",
        "4. Was the background preserved?",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- run

def _environment():
    import PIL
    return {"python": sys.version.split()[0], "platform": platform.platform(),
            "processor": platform.processor(), "pillow": PIL.__version__, "numpy": np.__version__,
            "device": "CPU only; no model weights, GPU, Ollama or network used"}


def _load_notes(root):
    path = root / "configs" / "phase9_assistant_visual_notes.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")).get("cases", {})
    return {}


def run_pilot(manifest_path, out, log=print) -> dict:
    """Execute every NEW attempt into a fresh directory; failures are recorded, not hidden."""
    manifest_path, out = Path(manifest_path), Path(out)
    validation = validate_manifest(manifest_path)
    if out.exists():
        raise FileExistsError(f"output directory already exists (never overwritten): {out}")
    data, root = load_manifest(manifest_path)
    notes = _load_notes(root)
    out.mkdir(parents=True)
    started, t0 = _now(), perf_counter()
    lines = []

    def say(msg):
        lines.append(msg)
        log(msg)

    say(f"Phase 9 pilot run -> {out}  (manifest {validation['manifest_sha256'][:12]})")
    results = []
    for case in data["cases"]:
        cid, case_dir = case["id"], out / case["id"]
        case_dir.mkdir()
        source_path = root / data["images"][case["source_image"]]["path"]
        record = {"id": cid, "status": case["status"], "direction": case["direction"],
                  "source_object": case["source_object"], "target_object": case["target_object"],
                  "human_review_status": case["human_review_status"], "attempts": []}
        try:
            if case["status"] == "HISTORICAL_BASELINE":
                # Frozen benchmark: copied byte-for-byte, never regenerated.
                hist = case["historical"]
                shutil.copyfile(root / hist["output"], case_dir / "final.png")
                if sha256(case_dir / "final.png") != hist["output_sha256"]:
                    raise ValueError("historical output copy hash mismatch")
                req = json.loads((root / hist["request"]).read_text(encoding="utf-8-sig"))
                ref_parent = (root / hist["request"]).parent
                with Image.open(ref_parent / req["permitted"]["path"]) as m:
                    bbox = m.getbbox()
                record.update(selected_attempt="historical", case_status="OK",
                              note="Historical result copied unchanged (not regenerated)")
                _review_assets(case_dir, source_path, case_dir / "final.png", bbox, case, [])
                say(f"{cid}: historical baseline copied, sha256 verified")
            else:
                finals = []
                for att in case["attempts"]:
                    letter, adir = att["attempt"], case_dir / f"attempt_{att['attempt']}"
                    entry = {"attempt": letter, "role": att["role"], "request": att["request"]}
                    try:
                        meta = rr.run_request(root / att["request"], adir)
                        entry.update(status="OK", elapsed_seconds=round(meta["elapsed_seconds"], 3),
                                     output_sha256=sha256(adir / "final.png"), target_bbox=meta["target_bbox"])
                        finals.append((letter, adir / "final.png", meta["target_bbox"]))
                        say(f"{cid} attempt {letter}: OK in {meta['elapsed_seconds']:.2f}s")
                    except Exception as exc:  # keep going; the failure is evidence
                        entry.update(status="FAILED", error=f"{type(exc).__name__}: {exc}",
                                     traceback=traceback.format_exc())
                        say(f"{cid} attempt {letter}: FAILED {type(exc).__name__}: {exc}")
                    record["attempts"].append(entry)
                if not finals:
                    record.update(case_status="FAILED", selected_attempt=None)
                else:
                    # Pre-declared rule: a correction exists only to fix a diagnosed defect of
                    # A, so the last technically successful attempt is the one shown for review.
                    letter, final_path, bbox = finals[-1]
                    shutil.copyfile(final_path, case_dir / "final.png")
                    record.update(selected_attempt=letter,
                                  case_status="OK" if len(finals) == len(case["attempts"]) else "PARTIAL_FAILURE")
                    _review_assets(case_dir, source_path, case_dir / "final.png", bbox, case,
                                   [(a, p) for a, p, _ in finals])
        except Exception as exc:
            record.update(case_status="FAILED", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
            say(f"{cid}: FAILED {type(exc).__name__}: {exc}")
        (case_dir / "REVIEW.md").write_text(
            _review_card(case, record.get("selected_attempt"), notes.get(cid, {})), encoding="utf-8")
        (case_dir / "status.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        results.append(record)

    _overview(out, data, root, results)
    elapsed = perf_counter() - t0
    failed = [r["id"] for r in results if r["case_status"] != "OK"]
    say(f"Finished in {elapsed:.1f}s; cases OK: {6 - len(failed)}/6" + (f"; failed: {failed}" if failed else ""))
    (out / "execution.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    run_manifest = {
        "method": rr.METHOD, "scope": "RESEARCH_ONLY", "model": None, "approval": False,
        "manifest": _rel(manifest_path, out), "manifest_sha256": validation["manifest_sha256"],
        "repo_root": _rel(root, out), "started_utc": started, "finished_utc": _now(),
        "elapsed_seconds": round(elapsed, 3), "environment": _environment(), "cases": results,
        "files": {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()},
    }
    (out / RUN_MANIFEST).write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")
    return {"run": str(out), "cases_ok": 6 - len(failed), "failed_cases": failed,
            "attempts_executed": sum(len(r["attempts"]) for r in results), "elapsed_seconds": round(elapsed, 3)}


def _overview(out, data, root, results):
    rows = []
    for case, rec in zip(data["cases"], results):
        final = out / case["id"] / "final.png"
        if not final.is_file():
            continue
        with Image.open(root / data["images"][case["source_image"]]["path"]) as s, Image.open(final) as f:
            rows.append(_panel([s, f], [f"{case['id']} original: {case['source_object']}",
                                        f"final: {case['target_object']} ({rec['selected_attempt']})"],
                               height=300, caption=f"{case['direction']} | human review: {case['human_review_status']}"))
    if rows:
        width = max(r.width for r in rows)
        sheet = Image.new("RGB", (width, sum(r.height for r in rows)), (236, 236, 236))
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height
        sheet.save(out / "overview.jpg", quality=88)


# --------------------------------------------------------------------------- verify

def _region_checks(source, final, permitted, protected, alpha, shadow, background_rgb):
    region, prot = permitted == 255, protected > 0
    changed = np.any(source != final, axis=2)
    target = alpha > 0
    shade = (shadow > 0) & ~target
    plain = region & ~target & ~shade
    # Outside the target footprint, a region pixel must equal the reconstructed plate
    # (background colour darkened by the documented shadow); anything else is leftover
    # source content.
    bg = np.asarray(background_rgb, dtype=np.float32)
    expected = bg * (1 - shadow[..., None].astype(np.float32) / 255)
    residual = region & ~target & np.any(np.abs(final.astype(np.float32) - expected) > 2, axis=2)
    dark_source = source.min(axis=2) < 235
    return {
        "permitted_pixels": int(region.sum()), "protected_pixels": int(prot.sum()),
        "changed_inside": int((changed & region).sum()), "changed_outside": int((changed & ~region).sum()),
        "max_outside_channel_difference": int(np.abs(source.astype(int) - final.astype(int))[~region].max(initial=0)),
        "protected_changed": int((changed & prot).sum()),
        "inside_breakdown": {
            "target_footprint_pixels": int((region & target).sum()),
            "shadow_only_pixels": int((region & shade).sum()),
            "background_reconstruction_only_pixels": int(plain.sum()),
            "background_reconstruction_changed_pixels": int((plain & changed).sum()),
            "source_object_pixels_replaced_by_background": int((plain & dark_source).sum()),
            "mean_abs_change_in_reconstruction_only": round(float(np.abs(source.astype(int) - final.astype(int))[plain].mean()) if plain.any() else 0.0, 3),
        },
        "source_residual_pixels_in_region": int(residual.sum()),
        "info_dark_source_pixels_outside_region": int((dark_source & ~region).sum()),
    }


def _verify_attempt(root, run, cid, att, record):
    out = {"attempt": att["attempt"], "checks": {}, "failures": []}
    fail = out["failures"].append
    if record is None or record.get("status") != "OK":
        out["result"] = "NOT_EXECUTED"
        fail("attempt did not complete in the run")
        return out
    req_path = root / att["request"]
    req = json.loads(req_path.read_text(encoding="utf-8-sig"))
    adir = run / cid / f"attempt_{att['attempt']}"
    images = {}
    for key in ("source", "reference", "selection", "permitted", "protected"):
        path = req_path.parent / req[key]["path"]
        ok = path.is_file() and sha256(path) == req[key]["sha256"]
        out["checks"][f"{key}_sha256"] = req[key]["sha256"] if ok else "MISMATCH"
        if not ok:
            fail(f"{key} input hash mismatch")
            continue
        with Image.open(path) as im:
            images[key] = im.copy()
    final_path = adir / "final.png"
    if not final_path.is_file() or len(images) < 5:
        fail("missing output or inputs")
        out["result"] = "FAIL"
        return out
    out["checks"]["output_sha256"] = sha256(final_path)
    out["checks"]["mask_sha256"] = req["permitted"]["sha256"]
    source, final = np.asarray(images["source"].convert("RGB")), _rgb(final_path)
    if source.shape != final.shape:
        fail("output dimensions differ from source")
        out["result"] = "FAIL"
        return out
    out["checks"]["dimensions"] = [final.shape[1], final.shape[0]]
    with Image.open(adir / "placed_alpha.png") as a, Image.open(adir / "shadow_alpha.png") as s, \
            Image.open(adir / "source_removed.png") as c:
        alpha, shadow, plate = np.asarray(a), np.asarray(s), np.asarray(c.convert("RGB"))
    permitted, protected = np.asarray(images["permitted"]), np.asarray(images["protected"])
    params = req["parameters"]
    stats = _region_checks(source, final, permitted, protected, alpha, shadow, params["background_rgb"])
    out["checks"].update(stats)
    region = permitted == 255
    out["checks"]["clean_plate_region_is_background"] = bool(np.all(plate[region] == params["background_rgb"]))
    # Deterministic replay in memory: same frozen inputs must give identical decoded pixels.
    replay, *_ = rr.replace_object(images["source"], images["reference"], images["selection"],
                                   images["permitted"], images["protected"], scope="RESEARCH_ONLY", **params)
    out["checks"]["deterministic_replay_pixel_identical"] = bool(np.array_equal(np.asarray(replay), final))
    if att.get("historical_output_sha256"):
        out["checks"]["historical_bytes_identical"] = out["checks"]["output_sha256"] == att["historical_output_sha256"]
        hist = root / att["historical_output"]
        out["checks"]["historical_pixels_identical"] = (bool(np.array_equal(_rgb(hist), final)) if hist.is_file()
                                                        else "historical file not present; byte hash compared instead")
    if stats["changed_outside"]:
        fail("pixels changed outside permitted region")
    if stats["protected_changed"]:
        fail("protected pixels changed")
    if stats["changed_inside"] == 0:
        fail("no change inside region")
    if stats["source_residual_pixels_in_region"]:
        fail("source content remains in region outside the target footprint")
    if not out["checks"]["clean_plate_region_is_background"]:
        fail("clean plate retains source content")
    if not out["checks"]["deterministic_replay_pixel_identical"]:
        fail("replay is not pixel identical")
    if out["checks"].get("historical_pixels_identical") is False:
        fail("decoded pixels differ from historical output")
    out["result"] = "FAIL" if out["failures"] else "PASS"
    return out


def verify_run(run) -> dict:
    """Reopen everything from disk and recompute; writes verification_summary.json."""
    run = Path(run)
    rm_path = run / RUN_MANIFEST
    if not rm_path.is_file():
        raise FileNotFoundError(f"not a pilot run directory (no {RUN_MANIFEST}): {run}")
    rm = json.loads(rm_path.read_text(encoding="utf-8"))
    root = (run / rm["repo_root"]).resolve()
    manifest_path = (run / rm["manifest"]).resolve()
    summary = {"run": str(run), "verified_utc": _now(), "failures": []}
    fail = summary["failures"].append
    missing = [p for p in rm["files"] if not (run / p).is_file()]
    tampered = [p for p, h in rm["files"].items() if (run / p).is_file() and sha256(run / p) != h]
    summary["files"] = {"recorded": len(rm["files"]), "missing": missing, "tampered": tampered}
    if missing:
        fail(f"missing outputs: {missing}")
    if tampered:
        fail(f"tampered outputs: {tampered}")
    try:
        validate_manifest(manifest_path)
        summary["manifest_provenance"] = "VALID"
    except ManifestError as exc:
        summary["manifest_provenance"] = exc.errors
        fail("manifest provenance invalid")
    if sha256(manifest_path) != rm["manifest_sha256"]:
        fail("pilot manifest changed after the run")
    data, _ = load_manifest(manifest_path)
    records = {r["id"]: r for r in rm["cases"]}
    summary["cases"] = []
    for case in data["cases"]:
        cid, rec = case["id"], records.get(case["id"], {})
        entry = {"id": cid, "direction": case["direction"], "human_review_status": case["human_review_status"],
                 "selected_attempt": rec.get("selected_attempt"), "attempts": []}
        if case["status"] == "NEW" and case["human_review_status"] != PENDING and not case.get("human_feedback"):
            fail(f"{cid}: review decision without feedback")
        if case["status"] == "HISTORICAL_BASELINE":
            entry["attempts"].append(_verify_historical(root, run, case))
        else:
            atts = {a["attempt"]: a for a in rec.get("attempts", [])}
            for att in case["attempts"]:
                entry["attempts"].append(_verify_attempt(root, run, cid, att, atts.get(att["attempt"])))
            sel = run / cid / "final.png"
            if rec.get("selected_attempt") and sel.is_file():
                entry["selected_matches_attempt"] = sha256(sel) == sha256(run / cid / f"attempt_{rec['selected_attempt']}" / "final.png")
                if not entry["selected_matches_attempt"]:
                    fail(f"{cid}: selected final differs from its attempt")
        for a in entry["attempts"]:
            for f in a["failures"]:
                fail(f"{cid} attempt {a['attempt']}: {f}")
        entry["result"] = "PASS" if all(a["result"] == "PASS" for a in entry["attempts"]) else "FAIL"
        summary["cases"].append(entry)
    summary["result"] = "FAIL" if summary["failures"] else "PASS"
    summary["note"] = ("Pixel locality, provenance and replay checks do not measure photographic realism or "
                       "cultural correctness; those need human review.")
    (run / VERIFICATION).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _verify_historical(root, run, case):
    hist = case["historical"]
    out = {"attempt": "historical", "checks": {}, "failures": []}
    final_path = run / case["id"] / "final.png"
    out["checks"]["output_sha256"] = sha256(final_path) if final_path.is_file() else None
    if out["checks"]["output_sha256"] != hist["output_sha256"]:
        out["failures"].append("historical result changed")
        out["result"] = "FAIL"
        return out
    req_path = root / hist["request"]
    req = json.loads(req_path.read_text(encoding="utf-8-sig"))
    ims = {}
    for key in ("source", "reference", "selection", "permitted", "protected"):
        p = req_path.parent / req[key]["path"]
        if not p.is_file() or sha256(p) != req[key]["sha256"]:
            out["failures"].append(f"{key} input hash mismatch")
            continue
        with Image.open(p) as im:
            ims[key] = im.copy()
    if len(ims) == 5:
        source, final = np.asarray(ims["source"].convert("RGB")), _rgb(final_path)
        permitted, protected = np.asarray(ims["permitted"]), np.asarray(ims["protected"])
        changed = np.any(source != final, axis=2)
        out["checks"].update(dimensions=[final.shape[1], final.shape[0]],
                             mask_sha256=req["permitted"]["sha256"],
                             permitted_pixels=int((permitted == 255).sum()),
                             changed_inside=int((changed & (permitted == 255)).sum()),
                             changed_outside=int((changed & (permitted != 255)).sum()),
                             protected_changed=int((changed & (protected > 0)).sum()))
        # In-memory check only; the saved benchmark is never rewritten.
        replay, *_ = rr.replace_object(ims["source"], ims["reference"], ims["selection"], ims["permitted"],
                                       ims["protected"], scope="RESEARCH_ONLY", **req["parameters"])
        out["checks"]["in_memory_replay_pixel_identical"] = bool(np.array_equal(np.asarray(replay), final))
        if out["checks"]["changed_outside"] or out["checks"]["protected_changed"]:
            out["failures"].append("historical locality violated")
        if not out["checks"]["in_memory_replay_pixel_identical"]:
            out["failures"].append("historical replay differs")
    out["result"] = "FAIL" if out["failures"] else "PASS"
    return out


# --------------------------------------------------------------------------- package

DOC_FILES = ["README.md", "REPRODUCTION.md", "pyproject.toml", "results/phase9_pilot/README.md",
             "configs/phase9_assistant_visual_notes.json",
             "src/transcreation/__init__.py", "src/transcreation/pilot.py",
             "src/transcreation/stages/__init__.py", "src/transcreation/stages/reference_replacement.py",
             "scripts/pilot.py", "scripts/reference_replacement.py",
             "tests/test_pilot.py", "tests/test_reference_replacement.py"]
PROVENANCE_FILES = ["results/phase9_repeatability/LICENSE_AND_ATTRIBUTION.md",
                    "results/phase9_repeatability/asset_provenance.json",
                    "results/phase9_repeatability/annotations.json",
                    "results/phase9_repeatability/cultural_context.md",
                    "results/phase9_repeatability/candidate_selection.json",
                    "results/phase9_repeatability/frozen_manifest.sha256",
                    "results/phase8_cultural_validation/true_object_replacement/LICENSE_AND_ATTRIBUTION.md"]


def _excluded(rel: Path) -> bool:
    return (bool(EXCLUDED_PARTS & set(rel.parts)) or rel.suffix.lower() in EXCLUDED_SUFFIXES
            or rel.name in EXCLUDED_NAMES)


def package_files(run) -> tuple[Path, list[str]]:
    run = Path(run)
    rm = json.loads((run / RUN_MANIFEST).read_text(encoding="utf-8"))
    root = (run / rm["repo_root"]).resolve()
    manifest_path = (run / rm["manifest"]).resolve()
    data, _ = load_manifest(manifest_path)
    wanted = set(DOC_FILES + PROVENANCE_FILES)
    wanted.add(_rel(manifest_path, root))
    wanted.update(img["path"] for img in data["images"].values())
    freeze = data.get("original_freeze", {})
    if freeze.get("path"):
        wanted.add(freeze["path"])
    requests = []
    for case in data["cases"]:
        if case.get("human_feedback", {}).get("evidence"):
            wanted.add(case["human_feedback"]["evidence"])
        if case["status"] == "HISTORICAL_BASELINE":
            requests.append(case["historical"]["request"])
            wanted.add(case["historical"]["output"])  # the frozen benchmark itself
        requests += [a["request"] for a in case.get("attempts", [])]
    for req_rel in requests:
        wanted.add(req_rel)
        req_path = root / req_rel
        req = json.loads(req_path.read_text(encoding="utf-8-sig"))
        for key in ("source", "reference", "selection", "permitted", "protected"):
            wanted.add(_rel(req_path.parent / req[key]["path"], root))
    # Pilot-level evidence beside the run (test logs, reproduction transcripts).
    for p in run.parent.iterdir():
        if p.is_file() and p.suffix in {".json", ".log", ".md", ".txt"}:
            wanted.add(_rel(p, root))
    for p in run.rglob("*"):
        if p.is_file():
            wanted.add(_rel(p, root))
    files = sorted(w for w in wanted if (root / w).is_file() and not _excluded(Path(w)))
    return root, files


def package_run(run, out_zip) -> dict:
    run, out_zip = Path(run), Path(out_zip)
    if out_zip.exists():
        raise FileExistsError(f"package already exists (never overwritten): {out_zip}")
    verification = verify_run(run)  # fresh verification is always shipped
    root, files = package_files(run)
    absent = [w for w in DOC_FILES if not (root / w).is_file()]
    sums = {rel: sha256(root / rel) for rel in files}
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_zip.with_suffix(".partial")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in files:
            zf.write(root / rel, rel)
        zf.writestr(SUMS, "".join(f"{h}  {rel}\n" for rel, h in sums.items()))
    tmp.replace(out_zip)
    check = check_package(out_zip)
    return {"zip": str(out_zip), "files": len(files), "bytes": out_zip.stat().st_size,
            "zip_sha256": sha256(out_zip), "verification": verification["result"],
            "verification_failures": verification["failures"], "missing_expected_docs": absent,
            "package_check": check}


def check_package(zip_path) -> dict:
    """Reopen the ZIP: CRCs, manifest coverage of every member, and every hash."""
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        names = [n for n in zf.namelist() if not n.endswith("/")]
        lines = zf.read(SUMS).decode("utf-8").splitlines()
        listed = dict(reversed(line.split("  ", 1)) for line in lines if line)
        uncovered = sorted(set(names) - set(listed) - {SUMS})
        phantom = sorted(set(listed) - set(names))
        wrong = [n for n, h in listed.items() if n in names and hashlib.sha256(zf.read(n)).hexdigest() != h]
        forbidden = [n for n in names if _excluded(Path(n))]
    ok = bad is None and not uncovered and not phantom and not wrong and not forbidden
    return {"result": "PASS" if ok else "FAIL", "members": len(names), "crc_error": bad,
            "not_in_manifest": uncovered, "listed_but_missing": phantom, "hash_mismatch": wrong,
            "forbidden_members": forbidden}
