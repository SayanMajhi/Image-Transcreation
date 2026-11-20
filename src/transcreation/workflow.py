"""Resumable, human-guided research workflow using the existing model stages.

Reviews authorize a recorded experiment, not cultural correctness. REVIEW and
ABSTAIN plans never reach editing. Each pass is grounded on its actual input.
"""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from transcreation.contracts import CaptionStatus, PlanningInput, VerifiedObject, InpaintingInput
from transcreation.orchestration import validate_planner_audit

CONFIG_DIR = Path(__file__).resolve().parents[2] / 'configs'
AUTOMATIC = {'CAPTIONING', 'PLANNING', 'GROUNDING', 'SEGMENTING', 'GENERATING'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} is required')
    return value.strip()


def prompt_for(edit, preserve, instructions):
    """Copy only reviewed plan content; no invented replacement details."""
    return (f"Edit the selected {edit.object_description}: {edit.proposed_change}. "
            f"Preserve: {'; '.join(preserve)}. User request: {instructions}. "
            "Change only the selected masked region. Match the original lighting, perspective and scale.")


def verify_pixels(source, final, mask, protected=None):
    with Image.open(source) as im:
        a = np.asarray(im.convert('RGB')).copy()
    with Image.open(final) as im:
        b = np.asarray(im.convert('RGB')).copy()
    with Image.open(mask) as im:
        if im.mode != 'L':
            raise ValueError('Mask must be grayscale')
        m = np.asarray(im).copy()
    if a.shape != b.shape or m.shape != a.shape[:2] or not set(np.unique(m)) <= {0, 255}:
        raise ValueError('Image dimensions or binary mask invalid')
    editable = m == 255
    changed = np.any(a != b, axis=2)
    result = {'changed_inside': int((changed & editable).sum()),
              'changed_outside': int((changed & ~editable).sum()),
              'source_sha256': sha(source), 'final_sha256': sha(final), 'mask_sha256': sha(mask)}
    if protected is not None:
        result['changed_previous_edits'] = int((changed & protected).sum())
    if result['changed_outside'] or not result['changed_inside'] or result.get('changed_previous_edits', 0):
        raise ValueError(f'Pixel verification failed: {result}')
    return result


class ModelBackend:
    """Load one model at a time and use existing artifact validators."""
    def __init__(self, config_dir):
        self.config_dir = Path(config_dir)

    def idle(self):
        from transcreation.config import load_planner_config
        from transcreation.stages.ollama_planner import OllamaPlanner
        from transcreation.orchestration import _planner_idle
        _planner_idle(OllamaPlanner(load_planner_config(self.config_dir / 'planner.yaml')))

    def caption(self, source):
        from transcreation.config import load_config
        from transcreation.pipeline import create_captioner
        from transcreation.orchestration import _release_captioner
        self.idle()
        model = None
        try:
            model = create_captioner(load_config(self.config_dir / 'models.yaml'))
            with Image.open(source) as im:
                return asdict(model.caption(im.convert('RGB')))
        finally:
            _release_captioner(model)

    def plan(self, request):
        from transcreation.config import load_planner_config
        from transcreation.stages.ollama_planner import OllamaPlanner
        planner = OllamaPlanner(load_planner_config(self.config_dir / 'planner.yaml'))
        try:
            return planner.record_plan(request)
        finally:
            self.idle()

    def ground(self, source, phrase, out):
        from transcreation.config import load_grounding_config
        from transcreation.stages.grounding import GroundingDetector, save_grounding_artifacts
        self.idle()
        model = GroundingDetector(load_grounding_config(self.config_dir / 'grounding.yaml'))
        try:
            result = model.detect(source, phrase)
            save_grounding_artifacts(source, result, out)
            if result.status != 'DETECTED':
                raise ValueError(f'Grounding did not find a usable object: {result.status}; {result.observations}')
        finally:
            model.close()

    def segment(self, source, detection, index, note, out):
        from transcreation.config import load_sam_config
        from transcreation.stages.segmentation import SamSegmenter, load_segmentation_input
        request = load_segmentation_input(source, detection, index, True, note=note,
                                          expected_image_sha256=sha(source))
        self.idle()
        model = SamSegmenter(load_sam_config(self.config_dir / 'sam.yaml'))
        try:
            result = model.segment(request, out)
            if result.status != 'SEGMENTED':
                raise ValueError(f'Segmentation failed: {result.status}; {result.observations}')
        finally:
            model.close()

    def generate(self, request, out):
        from transcreation.config import load_inpainting_config
        from transcreation.stages.inpainting import run_inpainting
        self.idle()
        result = run_inpainting(request, load_inpainting_config(self.config_dir / 'inpainting.yaml'), out)
        if result['status'] != 'COMPLETED':
            raise ValueError(f"Generation failed: {result.get('observations')}")


class Workflow:
    def __init__(self, directory, backend=None):
        self.root = Path(directory).resolve()
        self.backend = backend or ModelBackend(self.root / 'configs')
        self.state = read(self.root / 'session.json')
        if self.state['root'] != str(self.root):
            raise ValueError('This live session uses absolute paths; resume at its original location')

    @classmethod
    def create(cls, directory, image, instructions, target_culture, source_culture=None,
               config_dir=CONFIG_DIR, backend=None):
        instructions = text(instructions, 'User request')
        target_culture = text(target_culture, 'Target culture')
        image, directory = Path(image).resolve(), Path(directory).resolve()
        with Image.open(image) as im:
            im.verify()
        # Validate configurations before creating a session.
        from transcreation.config import (load_config, load_planner_config, load_grounding_config,
                                          load_sam_config, load_inpainting_config)
        loaders = {'models.yaml': load_config, 'planner.yaml': load_planner_config,
                   'grounding.yaml': load_grounding_config, 'sam.yaml': load_sam_config,
                   'inpainting.yaml': load_inpainting_config}
        for name, loader in loaders.items():
            loader(Path(config_dir) / name)
        directory.mkdir(parents=True, exist_ok=False)
        (directory / 'configs').mkdir()
        for name in loaders:
            shutil.copyfile(Path(config_dir) / name, directory / 'configs' / name)
        source = directory / ('source' + image.suffix)
        shutil.copyfile(image, source)
        state = {'schema': 1, 'root': str(directory), 'stage': 'CAPTIONING',
                 'execution_mode': 'HUMAN_GUIDED_RESEARCH', 'original': str(source),
                 'current_source': str(source), 'request': instructions, 'target_culture': target_culture,
                 'source_culture': source_culture, 'artifacts': {}, 'reviews': [], 'passes': [],
                 'attempt': 0, 'edit_index': 0, 'created_utc': datetime.now(timezone.utc).isoformat()}
        for p in directory.rglob('*'):
            if p.is_file():
                state['artifacts'][p.relative_to(directory).as_posix()] = sha(p)
        write(directory / 'session.json', state)
        return cls(directory, backend)

    @contextmanager
    def locked(self):
        lock = self.root / '.workflow.lock'
        try:
            handle = lock.open('x')
        except FileExistsError:
            raise RuntimeError('Session is busy. If an earlier process crashed, confirm it stopped before removing .workflow.lock.')
        try:
            handle.close()
            self.state = read(self.root / 'session.json')
            self.check()
            yield
            self.check()
            write(self.root / 'session.json', self.state)
        finally:
            lock.unlink()

    def check(self):
        for name, expected in self.state['artifacts'].items():
            p = (self.root / name).resolve()
            if not p.is_relative_to(self.root) or sha(p) != expected:
                raise ValueError(f'Recorded artifact was changed: {name}')

    def register(self, path):
        path = Path(path)
        files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
        for p in files:
            name = p.relative_to(self.root).as_posix()
            digest = sha(p)
            previous = self.state['artifacts'].get(name)
            if previous is not None and previous != digest:
                raise ValueError(f'Attempted replacement of recorded evidence: {name}')
            self.state['artifacts'][name] = digest

    def evidence(self, name, value):
        path = self.root / name
        if path.exists():
            raise ValueError(f'Evidence already exists: {path}')
        write(path, value)
        self.register(path)
        return str(path)

    def planning_input(self):
        return PlanningInput(self.state['confirmed_caption'], CaptionStatus.COMPLETE,
                             self.state['target_culture'], self.state['source_culture'], self.state['request'],
                             tuple(VerifiedObject(**obj) for obj in self.state['verified_objects']))

    def plan(self):
        return validate_planner_audit(self.planning_input(), read(self.state['plan_file']))[0]

    def current_edit(self):
        plan = self.plan()
        if plan.decision != 'PROPOSE':
            raise ValueError('Only a validated PROPOSE plan can reach editing')
        if self.state.get('approved_plan_sha256') != sha(self.state['plan_file']):
            raise ValueError('Current plan has no matching operator approval')
        return plan.candidate_edits[self.state['edit_index']]

    def previous_mask(self):
        with Image.open(self.state['original']) as im:
            union = np.zeros((im.height, im.width), dtype=bool)
        for item in self.state['passes']:
            with Image.open(item['mask']) as im:
                union |= np.asarray(im) == 255
        return union

    def advance(self):
        with self.locked():
            stage = self.state['stage']
            if stage not in AUTOMATIC:
                raise ValueError(f'{stage} requires operator input')
            self.state['attempt'] += 1
            attempt = self.root / f"attempt_{self.state['attempt']:03d}_{stage.lower()}"
            attempt.mkdir()
            before = deepcopy(self.state)
            try:
                self._advance(stage, attempt)
                self.state.pop('error', None)
            except (Exception, KeyboardInterrupt) as exc:
                self.state = before
                self.state.update(stage='FAILED', failed_stage=stage, error=f'{type(exc).__name__}: {exc}')
                write(attempt / 'error.json', {'stage': stage, 'error': self.state['error']})
            finally:
                self.register(attempt)
        return self.state['stage']

    def _advance(self, stage, attempt):
        state = self.state
        source = Path(state['current_source'])
        if stage == 'CAPTIONING':
            caption = self.backend.caption(source)
            write(attempt / 'caption.json', caption)
            state.update(caption_file=str(attempt / 'caption.json'), stage='CAPTION_REVIEW')
        elif stage == 'PLANNING':
            audit = self.backend.plan(self.planning_input())
            write(attempt / 'plan.json', audit)
            state['plan_file'] = str(attempt / 'plan.json')
            plan = self.plan()
            state['stage'] = {'PROPOSE': 'PLAN_REVIEW', 'REVIEW': 'REVIEW_REQUIRED', 'ABSTAIN': 'NO_EDIT'}[plan.decision]
        elif stage == 'GROUNDING':
            edit = self.current_edit()
            self.backend.ground(source, edit.localization_phrase, attempt / 'grounding')
            detection = attempt / 'grounding/detection.json'
            from scripts.review_grounding import _evidence
            result, _ = _evidence(source.read_bytes(), detection.read_bytes())
            if result.status != 'DETECTED' or result.source_phrase != edit.localization_phrase:
                raise ValueError('Detector returned no valid matching source-object result')
            state.update(detection_file=str(detection), stage='BOX_REVIEW')
        elif stage == 'SEGMENTING':
            self.current_edit()
            self.backend.segment(source, Path(state['detection_file']), state['box_index'],
                                 state['box_note'], attempt / 'segmentation')
            state['segmentation_file'] = str(attempt / 'segmentation/segmentation.json')
            from scripts.review_mask import _bundle
            result, _ = _bundle(Path(state['segmentation_file']))
            if (result.status != 'SEGMENTED' or result.request.image_sha256 != sha(source)
                    or result.request.detection_sha256 != sha(state['detection_file'])
                    or result.request.prediction_index != state['box_index']):
                raise ValueError('SAM result does not match the selected source and box')
            state['stage'] = 'MASK_REVIEW'
        elif stage == 'GENERATING':
            self.current_edit()
            request_path = Path(state['generation_input'])
            if state.get('authorized_request_sha256') != sha(request_path):
                raise ValueError('Generation needs explicit authorization of this exact prompt and mask')
            request = InpaintingInput(**read(request_path))
            from transcreation.stages.inpainting import validate_inputs
            validate_inputs(request)
            self.backend.generate(request, attempt / 'generation')
            final = attempt / 'generation/final.png'
            report = read(attempt / 'generation/inpainting.json')
            if report['status'] != 'COMPLETED' or report['request'] != asdict(request):
                raise ValueError('Generation result does not match this request')
            metrics = verify_pixels(source, final, request.mask_file, self.previous_mask())
            write(attempt / 'verification.json', metrics)
            state['passes'].append({'source': str(source), 'mask': request.mask_file, 'final': str(final),
                                    'request': str(request_path), 'verification': str(attempt / 'verification.json'),
                                    'edit_index': state['edit_index']})
            state['current_source'] = str(final)
            state['edit_index'] += 1
            state.pop('authorized_request_sha256', None)
            if state['edit_index'] < len(self.plan().candidate_edits):
                state['stage'] = 'GROUNDING'
            else:
                mask_path = attempt / 'all_edit_regions.png'
                Image.fromarray(self.previous_mask().astype('uint8') * 255).save(mask_path)
                final_metrics = verify_pixels(state['original'], final, mask_path)
                write(attempt / 'final_verification.json', final_metrics)
                # Convenient deliverable without changing the recorded per-pass output.
                shutil.copyfile(final, self.root / 'final.png')
                self.register(self.root / 'final.png')
                state.update(stage='FINAL_REVIEW', final_image=str(self.root / 'final.png'),
                             final_verification=str(attempt / 'final_verification.json'))

    def review(self, action, reviewer, note, **values):
        reviewer, note = text(reviewer, 'Reviewer name'), text(note, 'Review note')
        with self.locked():
            state = self.state
            stage = state['stage']
            if stage in AUTOMATIC or stage in {'COMPLETED', 'REJECTED', 'FAILED', 'NO_EDIT'}:
                raise ValueError(f'Cannot review at {stage}')
            evidence = {'reviewer': reviewer, 'note': note, 'action': action, 'stage': stage,
                        'at_utc': datetime.now(timezone.utc).isoformat(), 'values': values,
                        'artifact_sha256': dict(state['artifacts'])}
            if action == 'reject':
                state['stage'] = 'REJECTED'
            elif stage in {'CAPTION_REVIEW', 'REVIEW_REQUIRED'} and action == 'confirm_source':
                caption = text(values.get('caption'), 'Confirmed complete caption')
                descriptions = values.get('objects')
                if not isinstance(descriptions, list) or not descriptions:
                    raise ValueError('Confirm at least one visible source object')
                objects = [VerifiedObject(f'object-{i+1}', text(v, 'Source object')) for i,v in enumerate(descriptions)]
                state.update(confirmed_caption=caption, verified_objects=[asdict(o) for o in objects],
                             request=text(values.get('request', state['request']), 'User request'), stage='PLANNING')
                state.pop('approved_plan_sha256', None)
            elif stage == 'PLAN_REVIEW' and action == 'approve_plan':
                if self.plan().decision != 'PROPOSE':
                    raise ValueError('REVIEW and ABSTAIN cannot be approved for generation')
                state.update(approved_plan_sha256=sha(state['plan_file']), stage='GROUNDING')
            elif stage == 'BOX_REVIEW' and action == 'select_box':
                from scripts.review_grounding import _evidence
                result, _ = _evidence(Path(state['current_source']).read_bytes(), Path(state['detection_file']).read_bytes())
                index = values.get('index')
                if type(index) is not int or not 0 <= index < len(result.detections):
                    raise ValueError('Choose an existing zero-based box index')
                state.update(box_index=index, box_note=note, stage='SEGMENTING')
            elif stage == 'MASK_REVIEW' and action == 'select_mask':
                from scripts.review_mask import _bundle
                result, _ = _bundle(Path(state['segmentation_file']))
                index = values.get('index')
                candidates = [m for m in result.masks if m.index == index and m.status == 'VALID']
                if type(index) is not int or len(candidates) != 1:
                    raise ValueError('Select a valid SAM mask index')
                mask = Path(state['segmentation_file']).parent / candidates[0].filename
                with Image.open(mask) as im:
                    if np.any((np.asarray(im) == 255) & self.previous_mask()):
                        raise ValueError('Mask overlaps earlier edits. Choose a disjoint mask or start a revised session.')
                edit, plan = self.current_edit(), self.plan()
                request = InpaintingInput(state['current_source'], sha(state['current_source']),
                    state['segmentation_file'], sha(state['segmentation_file']), str(mask), sha(mask), index,
                    prompt_for(edit, plan.must_preserve, state['request']), note, 'RESEARCH_ONLY')
                from transcreation.stages.inpainting import validate_inputs
                validate_inputs(request)
                state['generation_input'] = self.evidence(f"generation_input_{state['edit_index']:03d}.json", asdict(request))
                state['stage'] = 'GENERATION_REVIEW'
            elif stage == 'GENERATION_REVIEW' and action == 'authorize_generation':
                self.current_edit()
                state.update(authorized_request_sha256=sha(state['generation_input']), stage='GENERATING')
            elif stage == 'FINAL_REVIEW' and action in {'accept_result', 'needs_changes'}:
                state.update(stage='COMPLETED', visual_review='ACCEPTED' if action == 'accept_result' else 'NEEDS_CHANGES')
            else:
                raise ValueError(f'Action {action} is invalid at {stage}')
            path = self.evidence(f"review_{len(state['reviews'])+1:03d}.json", evidence)
            state['reviews'].append(path)
        return self.state['stage']

    def retry(self):
        with self.locked():
            if self.state['stage'] != 'FAILED':
                raise ValueError('Only a failed automatic stage can be retried')
            self.state['stage'] = self.state['failed_stage']
        return self.state['stage']
