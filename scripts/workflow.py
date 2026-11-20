"""Start or resume the complete human-guided research workflow without editing JSON."""
import argparse
from dataclasses import replace
import html
import importlib.metadata
import os
from pathlib import Path

from transcreation.workflow import Workflow, AUTOMATIC, CONFIG_DIR, read


def download_models(config_dir=CONFIG_DIR):
    """Restore only pinned runtime files; omit duplicate formats and ONNX exports."""
    from huggingface_hub import snapshot_download, HfApi
    from transcreation.config import (load_config, load_grounding_config, load_sam_config, load_inpainting_config)
    api = HfApi()
    for name, loader in [('models.yaml', load_config), ('grounding.yaml', load_grounding_config),
                         ('sam.yaml', load_sam_config), ('inpainting.yaml', load_inpainting_config)]:
        config = loader(Path(config_dir) / name)
        files = api.list_repo_files(config.model_id, revision=config.revision)
        selected = [p for p in files if (p.endswith(('.json', '.txt')) or p.endswith('.safetensors'))
                    and not p.startswith('onnx/')]
        print('Downloading pinned model:', config.model_id, flush=True)
        snapshot_download(config.model_id, revision=config.revision, allow_patterns=selected, max_workers=4)


def doctor(config_dir=CONFIG_DIR):
    """Read-only readiness checks. Cache presence is not a model-load test."""
    from transcreation.config import (load_config, load_grounding_config, load_sam_config,
                                      load_inpainting_config, load_planner_config)
    from transcreation.stages.ollama_planner import OllamaPlanner
    from huggingface_hub.constants import HF_HUB_CACHE
    import torch
    ready = True
    for package in ('torch', 'transformers', 'diffusers', 'accelerate', 'Pillow'):
        try:
            print(f'{package}: {importlib.metadata.version(package)}')
        except importlib.metadata.PackageNotFoundError:
            print(f'{package}: MISSING'); ready = False
    print('CUDA:', torch.cuda.is_available())
    if torch.cuda.is_available():
        print('GPU:', torch.cuda.get_device_name(0), '| VRAM GiB:', round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2))
    else:
        ready = False
    print('Model cache:', HF_HUB_CACHE)
    for name, loader in [('models.yaml', load_config), ('grounding.yaml', load_grounding_config),
                         ('sam.yaml', load_sam_config), ('inpainting.yaml', load_inpainting_config)]:
        config = loader(Path(config_dir) / name)
        folder = Path(HF_HUB_CACHE) / ('models--' + config.model_id.replace('/', '--')) / 'snapshots' / config.revision
        weights = list(folder.rglob('*.safetensors')) if folder.exists() else []
        found = any(p.is_file() for p in weights)
        print(f'{config.model_id} @ {config.revision}: ' + ('cached weights found (completeness not proven)' if found else 'MISSING pinned weights'))
        ready &= found
    planner = load_planner_config(Path(config_dir) / 'planner.yaml')
    try:
        models = OllamaPlanner(replace(planner, timeout=3)).api('/api/tags')['models']
        found = any(m.get('name') == planner.model for m in models)
        print('Ollama', planner.model, ':', 'installed' if found else 'MISSING')
        ready &= found
    except Exception as exc:
        print('Ollama unavailable:', exc); ready = False
    print('Preflight:', 'basic checks passed; actual model loading still required' if ready else 'dependencies or services need setup before a live run')
    return ready


def review_page(workflow):
    s, root = workflow.state, workflow.root
    paths = [('Original', Path(s['original']))]
    if s.get('detection_file'):
        paths.append(('Detection boxes (image labels start at 1)', Path(s['detection_file']).parent / 'annotated.png'))
    if s.get('segmentation_file'):
        folder = Path(s['segmentation_file']).parent
        bundle = read(s['segmentation_file'])
        for mask in bundle['masks']:
            paths.append((f"SAM mask index {mask['index']}", folder / f"overlay_{mask['index']}.png"))
    if s.get('final_image'):
        paths.append(('Final image', Path(s['final_image'])))
    elif s['passes']:
        paths.append(('Latest completed edit', Path(s['passes'][-1]['final'])))
    figures = ''.join(f'<figure><figcaption>{html.escape(title)}</figcaption><img src="{html.escape(Path(os.path.relpath(p,root)).as_posix(), quote=True)}"></figure>' for title,p in paths if p.exists())
    details = {'stage': s['stage'], 'request': s['request'], 'source_culture': s['source_culture'], 'target_culture': s['target_culture']}
    for key in ('caption_file', 'plan_file', 'generation_input', 'final_verification'):
        if s.get(key):
            details[key] = read(s[key])
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Workflow review</title>
<style>body{{font:18px/1.5 system-ui;max-width:1100px;margin:30px auto;padding:20px}}img{{max-width:100%;max-height:650px;object-fit:contain}}figure{{margin:30px 0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef2f5;padding:20px}}</style>
<h1>Workflow review: {html.escape(s['stage'])}</h1><p>Inspect these artifacts, then enter your decision in the terminal. Refresh this page after each stage. Review controls are in the terminal.</p>{figures}<h2>Recorded details</h2><pre>{html.escape(__import__('json').dumps(details,indent=2))}</pre></html>'''
    path = root / 'review.html'
    path.write_text(body, encoding='utf-8')
    return path


def answer(prompt):
    value = input(prompt).strip()
    if value.lower() in {'quit', 'exit', 'pause'}:
        raise KeyboardInterrupt
    return value


def required(prompt):
    while True:
        value = answer(prompt)
        if value:
            return value
        print('Please enter a value, or type pause.')


def interactive(workflow, open_browser=False):
    reviewer = required('Your name for review records: ')
    print('Type pause at any prompt to save progress and resume later.')
    opened = False
    while True:
        s = workflow.state
        stage = s['stage']
        print('\nStage:', stage)
        page = review_page(workflow)
        print('Review images and evidence:', page)
        if open_browser and not opened:
            import webbrowser
            webbrowser.open(page.as_uri()); opened = True
        if stage in AUTOMATIC:
            print('Running model stage; outputs go to a new attempt directory...')
            workflow.advance()
            continue
        if stage in {'COMPLETED', 'REJECTED', 'NO_EDIT'}:
            print('Result:', s.get('visual_review', stage))
            if s.get('final_image'):
                print('Final image:', s['final_image'])
                print('Verification:', s['final_verification'])
            return
        if stage == 'FAILED':
            print(s['error'])
            if answer('After resolving the problem, type retry; otherwise pause: ').lower() == 'retry':
                workflow.retry()
                continue
            return
        try:
            if stage in {'CAPTION_REVIEW', 'REVIEW_REQUIRED'}:
                if stage == 'REVIEW_REQUIRED':
                    print('Planner requires clarification. No edit was released.')
                    print(workflow.plan().decision_reason)
                else:
                    print('Model caption:', read(s['caption_file'])['caption'])
                caption = required('After inspecting the image, enter a complete confirmed/corrected caption: ')
                objects = [v.strip() for v in required('Visible source objects to consider (separate with ;): ').split(';') if v.strip()]
                request = answer(f"Request [{s['request']}]: ") or s['request']
                note = required('Source inspection note: ')
                workflow.review('confirm_source', reviewer, note, caption=caption, objects=objects, request=request)
            elif stage == 'PLAN_REVIEW':
                plan = workflow.plan()
                for i, edit in enumerate(plan.candidate_edits):
                    print(f'{i+1}. {edit.object_description} -> {edit.proposed_change}')
                    print('Reason:', edit.cultural_reason)
                print('Preserve:', '; '.join(plan.must_preserve))
                print('Required checks:', '\n'.join(plan.verification_requirements))
                decision = answer('After checking every proposal and preservation requirement, type approve or reject: ').lower()
                if decision not in {'approve', 'reject'}:
                    continue
                workflow.review('approve_plan' if decision == 'approve' else 'reject', reviewer, required('Plan review note: '))
            elif stage == 'BOX_REVIEW':
                detections = read(s['detection_file'])['detections']
                for i, box in enumerate(detections):
                    print(f"Index {i} (image label {i+1}): {box['label']}, box {box['box']}")
                value = answer('Inspect the box image. Enter the ZERO-BASED index, or reject: ')
                if value == 'reject':
                    workflow.review('reject', reviewer, required('Reason: '))
                else:
                    workflow.review('select_box', reviewer, required('Box inspection note: '), index=int(value))
            elif stage == 'MASK_REVIEW':
                print('Inspect each mask overlay. It must exclude protected objects and all earlier edited regions.')
                value = answer('Enter a suitable mask index, or reject: ')
                if value == 'reject':
                    workflow.review('reject', reviewer, required('Reason: '))
                else:
                    workflow.review('select_mask', reviewer, required('Mask boundary/protection inspection note: '), index=int(value))
            elif stage == 'GENERATION_REVIEW':
                request = read(s['generation_input'])
                print('Generated prompt:', request['prompt'])
                print('Selected mask:', request['mask_file'])
                value = answer('Type generate to authorize this research edit, or reject: ').lower()
                if value not in {'generate', 'reject'}:
                    continue
                workflow.review('authorize_generation' if value == 'generate' else 'reject', reviewer, required('Generation decision note: '))
            elif stage == 'FINAL_REVIEW':
                print('Pixel checks passed. Inspect the visual result separately.')
                value = answer('Type accept or needs_changes: ').lower()
                if value not in {'accept', 'needs_changes'}:
                    continue
                workflow.review('accept_result' if value == 'accept' else 'needs_changes', reviewer, required('Visual quality and requested-change review: '))
        except (ValueError, KeyError) as exc:
            print('Cannot proceed:', exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor', help='Check local dependencies, GPU, model cache and Ollama')
    commands.add_parser('download-models', help='Download configured pinned model files into the Hugging Face cache')
    start = commands.add_parser('start', help='Start a fresh session with an image and plain-language request')
    start.add_argument('--image', type=Path, required=True)
    start.add_argument('--request', required=True)
    start.add_argument('--target-culture', required=True)
    start.add_argument('--source-culture')
    start.add_argument('--out', type=Path, required=True)
    start.add_argument('--open', action='store_true', help='Open the local artifact review page in a browser')
    resume = commands.add_parser('resume', help='Continue a paused or failed session')
    resume.add_argument('--run', type=Path, required=True)
    resume.add_argument('--open', action='store_true')
    status = commands.add_parser('status', help='Read current state and check recorded file hashes')
    status.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            raise SystemExit(0 if doctor() else 1)
        if args.command == 'download-models':
            download_models()
            return
        if args.command == 'start':
            wf = Workflow.create(args.out, args.image, args.request, args.target_culture, args.source_culture)
        else:
            wf = Workflow(args.run)
        wf.check()
        if args.command == 'status':
            print('Stage:', wf.state['stage'])
            print('Completed edit passes:', len(wf.state['passes']))
            print('Recorded artifacts verified:', len(wf.state['artifacts']))
            print('Review page:', review_page(wf))
            if wf.state.get('error'):
                print('Error:', wf.state['error'])
            return
        try:
            interactive(wf, args.open)
        except (KeyboardInterrupt, EOFError):
            print('\nPaused. Resume with: python -m scripts.workflow resume --run "' + str(wf.root) + '" --open')
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
