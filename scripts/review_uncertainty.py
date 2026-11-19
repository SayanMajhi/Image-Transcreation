"""Human classification of a narrowly eligible blocked plan; never releases edits."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image

from scripts.review_edit_intent import _human
from scripts.review_grounding import _write, digest
from transcreation.contracts import PlanningInput
from transcreation.orchestration import validate_planner_audit
from transcreation.stages import planning as policy
from transcreation.stages.caption import SmolCaptionResult
from transcreation.stages.ollama_planner import OllamaPlannerError, parse_planning_input


DECISIONS = ('ROUTINE_VERIFICATION_REQUIRED', 'MATERIAL_UNRESOLVED', 'REJECT', 'NEEDS_REVIEW')
DECLARATIONS = ('inspected_original', 'inspected_edit', 'inspected_uncertainties',
                'checked_user_instructions', 'inspected_audit')
PERMISSIONS = {name: False for name in ('candidate_release_authorized', 'edit_intent_authorized',
    'grounding_authorized', 'sam_authorized', 'diffusion_authorized', 'image_edit_authorized',
    'cultural_transformation_authorized')}
EVIDENCE = ('planning_input.json', 'planner_audit.json', 'validated_plan.json', 'experiment_frozen.json',
            'saved_caption.json', 'human_confirmation.json', 'raw_response_before_validation.json', 'raw_qwen_message.txt')
BUNDLE_FILES = (*EVIDENCE, 'original.webp', 'preview.png', 'review_request.md')
QUESTIONS = (
    'Does the proposed edit target the original noodles/object, rather than a future replacement?',
    'Is the original source identity supported by the image and supplied user verification?',
    'Does the edit preserve the requested bowl/protected object and scene?',
    'Is the adaptation reasonable for this user-directed objective?',
    'Does the exact uncertainty identify a material problem, or only a normal pre-edit verification requirement?',
    'Is the proposed change sufficiently specific for a later, separately authorized localization review?',
)


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f'non-finite JSON value: {value}')
    result = json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(result, dict):
        raise ValueError('expected a JSON object')
    return result


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _case(folder: Path, image: Path, index: int):
    """Only the documented single-candidate, uncertainty-only REVIEW profile."""
    payload = {name: (folder/name).read_bytes() for name in EVIDENCE}
    docs = {name: _json(raw) for name, raw in payload.items() if name.endswith('.json')}
    source = image.read_bytes()
    image_hash = digest(source)
    frozen, audit = docs['experiment_frozen.json'], docs['planner_audit.json']
    supplied = parse_planning_input(docs['planning_input.json'])
    if image_hash != frozen['source_image_sha256']:
        raise ValueError('source image hash differs from frozen evidence')
    for name, key in (('planning_input.json', 'planning_input_sha256'),
                      ('saved_caption.json', 'saved_caption_sha256'),
                      ('human_confirmation.json', 'human_confirmation_sha256')):
        if digest(payload[name]) != frozen[key]:
            raise ValueError(f'frozen evidence hash mismatch: {name}')
    if digest(Path(policy.__file__).read_bytes()) != frozen['validator_source_sha256']:
        raise ValueError('validator version differs from this frozen review evidence')
    with Image.open(BytesIO(source)) as original:
        original.load()
        dimensions, file_format = original.size, original.format
        preview = original.convert('RGB')
    if list(dimensions) != frozen['dimensions'] or file_format != frozen['format']:
        raise ValueError('source dimensions/format mismatch')
    caption_values = dict(docs['saved_caption.json'])
    if caption_values.pop('input_sha256') != image_hash:
        raise ValueError('caption belongs to another image')
    caption = SmolCaptionResult(**caption_values)
    if tuple(caption.image_dimensions or ()) != dimensions:
        raise ValueError('caption dimensions mismatch')
    expected = PlanningInput.from_caption(caption, supplied.target_culture, source_culture=supplied.source_culture,
        user_instructions=supplied.user_instructions, verified_objects=supplied.verified_objects)
    if not _same(asdict(expected), asdict(supplied)) or not _same(frozen['planning_input'], asdict(supplied)):
        raise ValueError('caption/input/frozen context mismatch')
    if (not _same(audit['request'], frozen['predeclared_expected_request'])
            or not _same(audit['config'], frozen['config'])
            or not _same(audit['resolved_model'], frozen['model'])
            or not _same(audit['request']['format'], frozen['schema'])):
        raise ValueError('actual planner request/model differs from frozen evidence')
    messages = audit['request']['messages']
    if (len(messages) != 2 or messages[0]['role'] != 'system' or messages[1]['role'] != 'user'
            or digest(messages[0]['content'].encode()) != frozen['new_system_prompt_sha256']
            or not _same(_json(messages[1]['content'].encode()), asdict(supplied))):
        raise ValueError('actual system/user message differs from planning input')
    if (not _same(audit['response'], docs['raw_response_before_validation.json'])
            or payload['raw_qwen_message.txt'].decode('utf8') != audit['response']['message']['content']):
        raise ValueError('raw response copies conflict')
    response = audit['response']
    if (response.get('done') is not True or response.get('done_reason') != 'stop'
            or response.get('model') != audit['config']['model']
            or response['message'].get('role') != 'assistant' or response['message'].get('tool_calls')):
        raise ValueError('incomplete or unexpected planner response is not triage-eligible')
    raw = _json(payload['raw_qwen_message.txt'])
    if (raw.get('decision') != 'PROPOSE' or len(raw.get('candidate_edits', [])) != 1
            or audit.get('parse_issues') != [] or audit['validation'].get('raw_schema_valid') is not True):
        raise ValueError('only one schema-valid original raw PROPOSE candidate is triage-eligible')
    try:
        final, issues = validate_planner_audit(supplied, audit)
    except OllamaPlannerError as exc:
        raise ValueError(f'original planner audit is invalid: {exc.code}: {exc}') from exc
    if (not _same(docs['validated_plan.json'], {'planning_result': asdict(final), 'issues': issues})
            or not _same(audit['validation']['issues'], issues)
            or audit['validation'].get('automatically_authorized') is not False):
        raise ValueError('validated REVIEW result or issues differ from recomputed evidence')
    profile = [(i['code'], i['severity'], i['candidate_index']) for i in issues]
    if (final.decision != 'REVIEW' or final.candidate_edits or not final.uncertainties
            or len(profile) != 2 or set(profile) != {
                ('USER_CONSTRAINTS_UNRESOLVED', 'human_verification', None),
                ('EDIT_UNCERTAINTY_UNRESOLVED', 'review', None)}):
        raise ValueError('ineligible issue profile: no other blocking or unknown issue may be triaged')
    if type(index) is not int or index != 0:
        raise ValueError('select the explicit original raw candidate index (zero for this single-candidate case)')
    candidate = raw['candidate_edits'][index]
    verified = next((v for v in supplied.verified_objects if v.object_id == candidate['verified_object_id']), None)
    if verified is None or candidate['object_description'] != verified.description or candidate['identity_uncertain'] is not False:
        raise ValueError('source identity must already match supplied verified evidence')
    confirmation = docs['human_confirmation.json']
    if audit.get('fixture_scope') not in (None, 'SYNTHETIC_TEST_ONLY'):
        raise ValueError('unknown fixture/evidence scope')
    synthetic = audit.get('fixture_scope') == 'SYNTHETIC_TEST_ONLY'
    if (confirmation['source_image_sha256'] != image_hash or not _same(confirmation['confirmed_object'], asdict(verified))
            or confirmation['image_edit_authorized'] is not False):
        raise ValueError('source confirmation conflicts with image/object or claims editing authorization')
    if synthetic:
        if confirmation.get('evidence_type') != 'SYNTHETIC_TEST_ONLY':
            raise ValueError('synthetic audit must remain explicitly synthetic')
    elif (confirmation.get('evidence_type') != 'ACTUAL_USER_MESSAGE'
            or confirmation.get('source_verification_provided_by_actual_user') is not True):
        raise ValueError('real evidence requires the original actual-user confirmation')
    if not isinstance(confirmation.get('verbatim_user_confirmation'), str) or not confirmation['verbatim_user_confirmation'].strip():
        raise ValueError('the original source-confirmation text is required')
    rejected = audit['validation'].get('rejected_candidates')
    if (not isinstance(rejected, list) or len(rejected) != 1
            or rejected[0].get('candidate_index') != index or not _same(rejected[0].get('raw_proposal'), candidate)
            or rejected[0].get('issue_codes') != [i['code'] for i in issues]):
        raise ValueError('original quarantine record must match the blocked proposal and issues')
    binding = {'original_image_sha256': image_hash, 'original_dimensions': list(dimensions),
        'planning_input_sha256': digest(payload['planning_input.json']),
        'planner_audit_sha256': digest(payload['planner_audit.json']),
        'raw_response_sha256': digest(payload['raw_response_before_validation.json']),
        'raw_message_sha256': digest(payload['raw_qwen_message.txt']),
        'validated_review_sha256': digest(payload['validated_plan.json']),
        'original_raw_candidate_index': index, 'verified_object': asdict(verified), 'original_raw_candidate': candidate,
        'original_scene_summary': raw['scene_summary'], 'source_culture': supplied.source_culture,
        'target_culture': supplied.target_culture, 'user_instructions': supplied.user_instructions,
        'must_preserve': list(final.must_preserve), 'original_uncertainties': list(final.uncertainties),
        'raw_verification_requirements': raw['verification_requirements'],
        'validated_verification_requirements': list(final.verification_requirements),
        'validation_issues': issues, 'original_issue_codes': [i['code'] for i in issues],
        'original_raw_decision': 'PROPOSE', 'original_validated_decision': 'REVIEW',
        'original_released_candidate_count': 0, 'triage_eligible': True,
        'eligibility_basis': 'Exact coded uncertainty-only profile; not proof of semantic or cultural correctness.',
        'evidence_scope': 'SYNTHETIC_TEST_ONLY' if synthetic else 'REAL_SAVED_PLANNING_EVIDENCE'}
    return binding, payload, source, preview


def prepare(case: Path, image: Path, index: int, out: Path) -> Path:
    binding, payload, source, preview = _case(case, image, index)
    out.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        (out/name).write_bytes(data)
    (out/'original.webp').write_bytes(source)  # byte identity matters; Pillow detects actual encoding
    preview.thumbnail((850, 850)); preview.save(out/'preview.png')
    text = ('# PENDING human uncertainty triage\n\n'
        'Classification only. Original final decision remains REVIEW with zero released candidates.\n'
        'No decision here authorizes grounding, segmentation or image editing.\n\n'
        '![Original photograph preview](preview.png)\n\n[Original byte-identical image](original.webp)\n\n'
        '## Exact bound case\n\n```json\n'+json.dumps(binding, indent=2, ensure_ascii=False)+'\n```\n\n'
        '## Required human questions\n\n'+'\n'.join(f'{i}. {question}' for i, question in enumerate(QUESTIONS, 1))+
        '\n\nRead the full original instructions, raw proposal, uncertainty and raw/final audit. '
        'Record a specific explanation. ROUTINE_VERIFICATION_REQUIRED records only your classification; '
        'it does not satisfy other user-constraint checks or release any candidate.\n')
    (out/'review_request.md').write_text(text, encoding='utf8')
    record = {'schema_version': 1, 'record_type': 'planning_uncertainty_human_review',
        'scope': 'UNCERTAINTY_CLASSIFICATION_ONLY', **binding,
        'file_sha256': {name: digest((out/name).read_bytes()) for name in BUNDLE_FILES},
        'decision': 'PENDING', 'reviewer': None, 'reason': 'Awaiting real human uncertainty triage.',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'reviewed_at_utc': None,
        **{flag: False for flag in DECLARATIONS}, **PERMISSIONS}
    check(record, out)
    path = out/'pending.json'; _write(path, record)
    return path


def _reviewer(record):
    _human(record)  # reuse existing identity, reason, original/edit inspection and timestamp checks
    placeholders = {'yourname', 'yourrealname', 'reviewer', 'reviewername', 'name', 'yourfullname', 'fullname',
                    'unknown', 'pending', 'todo', 'tbd', 'na', 'none', 'null', 'reason', 'yourreason',
                    'explanation', 'justification', 'placeholder', 'ok', 'yes', 'approved'}
    placeholders.update(re.sub(r'\W|_', '', value.casefold()) for value in DECISIONS)
    for field in ('reviewer', 'reason'):
        value = record[field]
        if re.sub(r'\W|_', '', value.casefold()) in placeholders or '<' in value or '>' in value:
            raise ValueError('reviewer and explanation must not be placeholders or a bare classification label')
    if any(record.get(flag) is not True for flag in DECLARATIONS):
        raise ValueError('declare inspection of original, proposal, uncertainties, complete instructions and audit')


def check(record: dict, folder: Path):
    if (type(record.get('schema_version')) is not int or record.get('schema_version') != 1 or record.get('record_type') != 'planning_uncertainty_human_review'
            or record.get('scope') != 'UNCERTAINTY_CLASSIFICATION_ONLY'
            or any(record.get(key) is not False for key in PERMISSIONS)):
        raise ValueError('uncertainty classification cannot authorize candidate release or any execution')
    if (not isinstance(record.get('reason'), str) or not record['reason'].strip()
            or datetime.fromisoformat(record['created_at_utc']).utcoffset() is None):
        raise ValueError('a reason and timezone-aware request creation timestamp are required')
    manifest = record.get('file_sha256')
    if not isinstance(manifest, dict) or set(manifest) != set(BUNDLE_FILES):
        raise ValueError('complete fixed-file evidence manifest is required')
    for name, expected in manifest.items():
        if digest((folder/name).read_bytes()) != expected:
            raise ValueError(f'review evidence hash mismatch: {name}')
    binding, _, _, _ = _case(folder, folder/'original.webp', record['original_raw_candidate_index'])
    if any(not _same(record.get(key), value) for key, value in binding.items()):
        raise ValueError('review metadata conflicts with original source, candidate, uncertainty or issues')
    keys = set(binding) | {'schema_version', 'record_type', 'scope', 'file_sha256', 'decision', 'reviewer',
                          'reason', 'created_at_utc', 'reviewed_at_utc', *DECLARATIONS, *PERMISSIONS}
    if record['decision'] == 'PENDING':
        if (record['reviewer'] is not None or record['reviewed_at_utc'] is not None
                or any(record.get(flag) is not False for flag in DECLARATIONS)):
            raise ValueError('PENDING cannot claim inspection, a reviewer or a decision timestamp')
    elif record['decision'] in DECISIONS:
        keys |= {'pending_file', 'pending_sha256'}
        _reviewer(record)
        if record.get('pending_file') != 'pending.json':
            raise ValueError('a decision must reference its original pending.json in this bundle')
        data = (folder/'pending.json').read_bytes()
        if digest(data) != record.get('pending_sha256'):
            raise ValueError('pending request hash mismatch')
        parent = _json(data)
        if parent.get('decision') != 'PENDING':
            raise ValueError('the parent must be the original PENDING request')
        check(parent, folder)
        mutable = {'decision', 'reviewer', 'reason', 'reviewed_at_utc', *DECLARATIONS}
        if any(not _same(record.get(key), value) for key, value in parent.items() if key not in mutable):
            raise ValueError('decision changed the original evidence or review scope')
    else:
        raise ValueError('unknown uncertainty-review decision')
    if set(record) != keys:
        raise ValueError('missing or unexpected uncertainty-review fields')
    return binding


def verify(path: Path) -> dict:
    record = _json(path.read_bytes()); check(record, path.parent)
    return record


def decide(pending: Path, out: Path, decision: str, reviewer: str, reason: str, *,
           inspected_original=False, inspected_edit=False, inspected_uncertainties=False,
           checked_user_instructions=False, inspected_audit=False) -> Path:
    record = verify(pending)
    if (record['decision'] != 'PENDING' or pending.name != 'pending.json' or decision not in DECISIONS
            or pending.parent.resolve() != out.parent.resolve()):
        raise ValueError('write one new classification beside its original PENDING evidence')
    record.update(decision=decision, reviewer=reviewer, reason=reason,
        reviewed_at_utc=datetime.now(timezone.utc).isoformat(), inspected_original=inspected_original,
        inspected_edit=inspected_edit, inspected_uncertainties=inspected_uncertainties,
        checked_user_instructions=checked_user_instructions, inspected_audit=inspected_audit,
        pending_file='pending.json', pending_sha256=digest(pending.read_bytes()))
    check(record, pending.parent); _write(out, record)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    ready = commands.add_parser('prepare')
    for name in ('case', 'image', 'out'):
        ready.add_argument('--'+name, type=Path, required=True)
    ready.add_argument('--index', type=int, required=True)
    submit = commands.add_parser('decide')
    submit.add_argument('--pending', type=Path, required=True); submit.add_argument('--out', type=Path, required=True)
    submit.add_argument('--decision', choices=DECISIONS, required=True)
    submit.add_argument('--reviewer', required=True); submit.add_argument('--reason', required=True)
    for flag in DECLARATIONS:
        submit.add_argument('--'+flag.replace('_', '-'), action='store_true')
    commands.add_parser('verify').add_argument('--review', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare': path = prepare(args.case, args.image, args.index, args.out)
        elif args.command == 'decide':
            path = decide(args.pending, args.out, args.decision, args.reviewer, args.reason,
                          **{flag: getattr(args, flag) for flag in DECLARATIONS})
        else: path = args.review
        print(json.dumps(verify(path), indent=2, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
