"""Build an offline evidence walkthrough; checks saved files without running models."""
from pathlib import Path
import hashlib
import html
import json
import os
from datetime import datetime, timezone

import numpy as np
from PIL import Image


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'results/phase7_integration'
    run = base / 'visual_v3'
    out = root / 'outputs/presentation_walkthrough'
    out.mkdir(parents=True, exist_ok=True)
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    record = read(run / 'A/inpainting.json')
    request = record['request']
    source_path = root / request['source_image']
    if not source_path.exists():
        source_path = run / 'original.webp'
    sam_path = root / request['segmentation_file']
    sam = read(sam_path)
    detector_path = root / sam['request']['detection_file']
    checks = {}
    for field in ('image', 'mask', 'annotation', 'protected_mask', 'segmentation'):
        path_key = {'image': 'source_image', 'protected_mask': 'protected_mask_file'}.get(field, field + '_file')
        p = root / request[path_key]
        if field == 'image':
            p = source_path
        checks[field + '_hash'] = sha(p) == request[field + '_sha256']
    checks['detector_hash'] = sha(detector_path) == sam['request']['detection_sha256']
    checks['sam_source_binding'] = sam['request']['image_sha256'] == request['image_sha256']
    checks['generation_completed'] = record['status'] == 'COMPLETED'
    for name, digest in record.get('artifact_sha256', {}).items():
        checks['generated_artifact:' + name] = sha(run / 'A' / name) == digest
    def pixels(path, mode):
        with Image.open(path) as im:
            return np.asarray(im.convert(mode)).copy()
    source = pixels(source_path, 'RGB')
    final = pixels(run / 'A/final.png', 'RGB')
    mask_raw = pixels(root / request['mask_file'], 'L')
    protected_raw = pixels(root / request['protected_mask_file'], 'L')
    checks['dimensions'] = source.shape == final.shape and mask_raw.shape == source.shape[:2] and protected_raw.shape == mask_raw.shape
    if not checks['dimensions']:
        raise ValueError('Image and mask dimensions disagree')
    checks['binary_masks'] = set(np.unique(mask_raw)) <= {0, 255} and set(np.unique(protected_raw)) <= {0, 255}
    mask, protected = mask_raw == 255, protected_raw == 255
    changed = np.any(source != final, axis=2)
    metrics = {'width': source.shape[1], 'height': source.shape[0],
               'editable_pixels': int(mask.sum()), 'changed_inside': int((changed & mask).sum()),
               'changed_outside': int((changed & ~mask).sum()),
               'changed_protected': int((changed & protected).sum()),
               'mask_protected_overlap': int((mask & protected).sum())}
    checks['nonempty_edit'] = metrics['changed_inside'] > 0
    checks['outside_preserved'] = metrics['changed_outside'] == 0
    checks['protected_preserved'] = metrics['changed_protected'] == 0
    checks['no_protected_overlap'] = metrics['mask_protected_overlap'] == 0
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              'mode': 'SAVED_ARTIFACT_VERIFICATION_NO_MODEL_INFERENCE',
              'passed': all(checks.values()), 'checks': checks, 'metrics': metrics,
              'final_sha256': sha(run / 'A/final.png'),
              'limitation': 'Manual research mask; visual adaptation recorded as unsuccessful. No new human approval.'}
    (out / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    def url(p):
        return Path(os.path.relpath(p, out)).as_posix()
    def figure(p, caption):
        return f'<figure><a href="{url(p)}"><img src="{url(p)}" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>'
    stages = [
        ('1. Input image', 'Research objective: adapt exposed ramen noodles toward Indian-style masala noodles while preserving the scene.', [(run / 'original.webp', 'Original saved photograph')]),
        ('2. Object detection', 'Grounding DINO located the original noodles. The selected box also contains toppings and utensils, so it cannot serve as an editing mask.', [(detector_path.parent / 'annotated.png', 'Saved Grounding DINO detection')]),
        ('3. SAM segmentation', 'SAM produced candidate masks. This saved candidate is the geometric reference for the later manually refined mask.', [(sam_path.parent / 'overlay_1.png', 'SAM candidate 1 overlay')]),
        ('4. Manual mask refinement', 'The operator traced three exposed noodle regions and excluded protected objects. This is a manual research annotation, not an automatic SAM output or a human-approved cultural edit.', [(run / 'mask_overlay.png', 'Actual editable regions'), (run / 'protected_overlay.png', 'Protected regions')]),
        ('5. Saved diffusion output', 'Stable Diffusion 1.5 inpainting completed with seed 42 and a 512-square processing crop. The recorded assessment found weak seasoning and synthetic texture. The intended visual adaptation was unsuccessful.', [(run / 'original.webp', 'Before'), (run / 'A/final.png', 'Saved result A')]),
    ]
    sections = ''.join(f'<section id="step{i}"><h2>{title}</h2><p>{text}</p><div class="images">' + ''.join(figure(p,c) for p,c in images) + '</div></section>' for i,(title,text,images) in enumerate(stages,1))
    rows = ''.join(f'<tr><td>{html.escape(k.replace("_", " "))}</td><td>{v:,}</td></tr>' for k,v in metrics.items())
    status = 'PASS' if report['passed'] else 'FAIL'
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Saved workflow demonstration</title>
<style>body{{font:20px/1.6 system-ui;background:#f5f7fa;color:#172238;margin:0}}main{{max-width:1100px;margin:auto;padding:36px}}h1{{font-size:40px;line-height:1.2}}h2{{font-size:30px}}section{{padding:30px 0;border-top:1px solid #ccd4de}}.images{{display:flex;gap:20px;flex-wrap:wrap}}figure{{margin:0;flex:1;min-width:300px}}img{{width:100%;max-height:640px;object-fit:contain;background:white}}figcaption{{font-size:16px}}a{{color:#1355a1}}table{{border-collapse:collapse;width:100%}}td{{padding:9px;border-bottom:1px solid #ccd4de}}nav{{display:flex;gap:20px;flex-wrap:wrap}}.note{{background:#fff2d7;padding:18px}}@media print{{section{{break-inside:avoid}}}}</style>
<main><h1>One saved image-editing workflow</h1><p>Original image, object detection, segmentation, manual refinement, saved generation, and fresh pixel verification.</p>
<p class="note">Saved research demonstration. Opening this page does not run AI models. The pipeline stages produced artifacts, while visual adaptation remains unsuccessful in this example.</p>
<nav>{''.join(f'<a href="#step{i}">Step {i}</a>' for i in range(1,7))}</nav>{sections}
<section id="step6"><h2>6. Fresh verification: {status}</h2><p>The verifier reopened the saved source, final image, and masks, checked recorded hashes, and compared every RGB pixel. These checks establish file integrity and pixel preservation, not visual quality.</p><table>{rows}</table><p><a href="verification.json">Full verification record</a> · <a href="{url(run/'A/inpainting.json')}">Generation metadata</a> · <a href="{url(base/'README.md')}">Original experiment report</a></p></section>
<section><h2>What this demonstrates</h2><p>Detection, segmentation, manually guided localized editing, and independent verification can be traced through saved artifacts. A convincing cultural transformation and a complete automatic workflow remain future work.</p></section></main></html>'''
    (out / 'index.html').write_text(page, encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Walkthrough:', out / 'index.html')
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
