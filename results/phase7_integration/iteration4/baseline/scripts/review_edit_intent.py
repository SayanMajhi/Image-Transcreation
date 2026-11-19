"""Evidence-bound human review of a final PROPOSE; permits a grounding test only."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from PIL import Image

from scripts.review_grounding import _json, _write, digest
from transcreation.contracts import PlanningInput, VerifiedObject
from transcreation.stages.ollama_planner import parse_planning_input


DECISIONS = ("ACCEPT_FOR_GROUNDING_TEST", "REJECT", "NEEDS_REVIEW")
PERMISSIONS = {"sam_authorized": False, "image_edit_authorized": False,
               "diffusion_authorized": False, "cultural_transformation_authorized": False}


def _local(folder: Path, name: str) -> Path:
    path = (folder / name).resolve()
    if not isinstance(name, str) or Path(name).is_absolute() or not path.is_relative_to(folder.resolve()):
        raise ValueError("evidence reference must stay within its bundle")
    return path


def _canonical(value) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def _proposal(run_file: Path, image: Path, index: int):
    """Revalidate the original run, not a free-standing candidate copied out of quarantine."""
    from transcreation.orchestration import validate_planner_audit
    from transcreation.stages.caption import SmolCaptionResult

    run_bytes = run_file.read_bytes()
    run = _json(run_bytes)
    if (run.get("execution_mode") != "AUTOMATED_PLANNING" or run.get("state") != "EDIT_PROPOSAL_READY"
            or run.get("image_generation_permitted") is not False):
        raise ValueError("only an original automated final PROPOSE run is eligible")
    payload = {"pipeline_result.json": run_bytes}
    docs = {}
    for key in ("pipeline_input.json", "source", "caption.json", "planning_input.json", "planner_audit.json", "validated_plan.json"):
        entry = run["artifact_ids"][key]
        raw = _local(run_file.parent, entry["path"]).read_bytes()
        if digest(raw) != entry["sha256"] or entry["id"] != entry["sha256"]:
            raise ValueError(f"changed planning evidence: {key}")
        payload[entry["path"]] = raw
        if key != "source":
            docs[key] = _json(raw)
    context = docs["pipeline_input.json"]
    source = payload[run["artifact_ids"]["source"]["path"]]
    if (digest(image.read_bytes()) != context["image_sha256"] or digest(source) != context["image_sha256"]
            or context["execution_mode"] != "AUTOMATED_PLANNING"):
        raise ValueError("original image identity or planning execution mode mismatch")
    with Image.open(image) as photo:
        dimensions = photo.size
    caption_values = dict(docs["caption.json"])
    if caption_values.pop("input_sha256") != context["image_sha256"]:
        raise ValueError("caption is bound to another image")
    caption = SmolCaptionResult(**caption_values)
    if caption.image_dimensions is not None and tuple(caption.image_dimensions) != dimensions:
        raise ValueError("caption image dimensions mismatch")
    expected = PlanningInput.from_caption(caption, context["target_culture"], source_culture=context.get("source_culture"),
                user_instructions=context.get("user_instructions"),
                verified_objects=tuple(VerifiedObject(**v) for v in context.get("verified_objects", [])))
    planning = parse_planning_input(docs["planning_input.json"])
    if _canonical(asdict(expected)) != _canonical(asdict(planning)):
        raise ValueError("caption, cultures or verified-object context mismatch")
    audit = docs["planner_audit.json"]
    plan, issues = validate_planner_audit(planning, audit)
    saved = docs["validated_plan.json"]
    if (_canonical(saved) != _canonical({"planning_result": asdict(plan), "issues": issues})
            or plan.decision != "PROPOSE" or not plan.candidate_edits
            or audit.get("validation", {}).get("rejected_candidates") or audit.get("parse_issues")
            or audit.get("validation", {}).get("raw_schema_valid") is False):
        raise ValueError("only final actionable PROPOSE candidates can be reviewed")
    if type(index) is not int or not 0 <= index < len(plan.candidate_edits):
        raise ValueError("select one explicit valid final candidate index")
    candidate = plan.candidate_edits[index]
    binding = {"original_image_sha256": context["image_sha256"],
        "source_culture": planning.source_culture, "target_culture": planning.target_culture,
        "user_instructions": planning.user_instructions, "verified_objects": context.get("verified_objects", []),
        "validated_plan_sha256": run["artifact_ids"]["validated_plan.json"]["sha256"],
        "planning_result_sha256": _canonical(asdict(plan)),
        "planner_audit_sha256": run["artifact_ids"]["planner_audit.json"]["sha256"],
        "planning_run_sha256": digest(run_bytes), "candidate_index": index, "candidate": asdict(candidate),
        "must_preserve": list(plan.must_preserve), "verification_requirements": list(plan.verification_requirements),
        "evidence_scope": "SYNTHETIC_TEST_ONLY" if audit.get("fixture_scope") == "SYNTHETIC_TEST_ONLY" else "REAL_PLANNING_EVIDENCE"}
    return binding, payload


def prepare(run: Path, image: Path, index: int, out: Path) -> Path:
    binding, payload = _proposal(run, image, index)
    out.mkdir(parents=True, exist_ok=False)
    for name, raw in payload.items():
        target = out / "evidence" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    image_name = "original" + image.suffix.lower()
    (out / image_name).write_bytes(image.read_bytes())
    record = {"schema_version": 1, "record_type": "edit_intent_review", "scope": "GROUNDING_TEST_ONLY",
              **binding, "image_file": image_name, "run_file": "evidence/pipeline_result.json",
              "decision": "PENDING", "reviewer": None, "reason": "Awaiting explicit image and proposal inspection.",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "reviewed_at_utc": None,
              "inspected_original": False, "inspected_edit": False, **PERMISSIONS}
    # Check the copied evidence too, including a source modified during preparation.
    check(record, out)
    path = out / "pending.json"
    _write(path, record)
    return path


def _human(record):
    name, reason = record.get("reviewer"), record.get("reason")
    placeholders = {"YOUR_NAME", "YOURNAME", "YOUR_REAL_NAME", "REVIEWER_NAME", "REVIEWER", "NAME",
                    "YOUR_FULL_NAME", "YOUR_NAME_HERE", "FULL_NAME", "UNKNOWN", "PENDING", "TODO", "N/A", "NONE", "NULL"}
    if (not isinstance(name, str) or not name.strip() or name.strip().upper().replace(" ", "_") in placeholders
            or "<" in name or ">" in name or not isinstance(reason, str) or not reason.strip()
            or reason.strip().upper() in placeholders):
        raise ValueError("a non-placeholder reviewer identity and explanation are required")
    if record.get("inspected_original") is not True or record.get("inspected_edit") is not True:
        raise ValueError("explicit original-image and edit-proposal inspection declarations are required")
    stamp = datetime.fromisoformat(record["reviewed_at_utc"])
    if stamp.utcoffset() is None:
        raise ValueError("review timestamp must include a timezone")


def check(record: dict, folder: Path):
    if (record.get("record_type") != "edit_intent_review" or record.get("schema_version") != 1
            or record.get("scope") != "GROUNDING_TEST_ONLY"
            or any(record.get(k) is not False for k in PERMISSIONS)):
        raise ValueError("edit-intent review never authorizes SAM or image editing")
    binding, _ = _proposal(_local(folder, record["run_file"]), _local(folder, record["image_file"]), record["candidate_index"])
    if any(record.get(key) != value for key, value in binding.items()):
        raise ValueError("review binding differs from original plan, audit, image or candidate")
    if record["decision"] == "PENDING":
        if (record.get("reviewer") is not None or record.get("reviewed_at_utc") is not None
                or record.get("inspected_original") is not False or record.get("inspected_edit") is not False):
            raise ValueError("pending review cannot claim human inspection or acceptance")
    elif record["decision"] in DECISIONS:
        _human(record)
        parent_path = _local(folder, record["pending_file"])
        raw = parent_path.read_bytes()
        if digest(raw) != record["pending_sha256"]:
            raise ValueError("pending review hash mismatch")
        parent = _json(raw)
        if parent.get("decision") != "PENDING":
            raise ValueError("a decision must reference its original pending request")
        check(parent, folder)
        unchanged = set(parent) - {"decision", "reviewer", "reason", "reviewed_at_utc", "inspected_original", "inspected_edit"}
        if any(record.get(k) != parent[k] for k in unchanged):
            raise ValueError("decision changed the pending review scope or evidence")
    else:
        raise ValueError("unknown edit-intent decision")
    return binding


def decide(pending: Path, out: Path, decision: str, reviewer: str, reason: str,
           inspected_original: bool, inspected_edit: bool) -> Path:
    record = _json(pending.read_bytes())
    check(record, pending.parent)
    if record["decision"] != "PENDING" or decision not in DECISIONS or out.parent.resolve() != pending.parent.resolve():
        raise ValueError("write a new decision beside its original pending evidence")
    record.update(decision=decision, reviewer=reviewer, reason=reason, inspected_original=inspected_original,
                  inspected_edit=inspected_edit, reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                  pending_file=pending.name, pending_sha256=digest(pending.read_bytes()))
    check(record, pending.parent)
    _write(out, record)
    return out


def verify(path: Path) -> dict:
    record = _json(path.read_bytes())
    check(record, path.parent)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    for name in ("run", "image", "out"):
        prepare_parser.add_argument("--"+name, type=Path, required=True)
    prepare_parser.add_argument("--index", type=int, required=True)
    decision_parser = commands.add_parser("decide")
    decision_parser.add_argument("--pending", type=Path, required=True)
    decision_parser.add_argument("--out", type=Path, required=True)
    decision_parser.add_argument("--decision", choices=DECISIONS, required=True)
    decision_parser.add_argument("--reviewer", required=True)
    decision_parser.add_argument("--reason", required=True)
    decision_parser.add_argument("--inspected-original", action="store_true")
    decision_parser.add_argument("--inspected-edit", action="store_true")
    commands.add_parser("verify").add_argument("--review", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            path = prepare(args.run, args.image, args.index, args.out)
        elif args.command == "decide":
            path = decide(args.pending, args.out, args.decision, args.reviewer, args.reason, args.inspected_original, args.inspected_edit)
        else:
            path = args.review
        record = verify(path)
        print(json.dumps({"review": str(path), "decision": record["decision"], "scope": record["scope"],
                          "candidate": record["candidate"], "evidence_scope": record["evidence_scope"]}, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
