"""Resume the same pinned fallback files with bounded verified HTTP ranges.

The normal Hub transfer stalled at zero local UNet bytes. No alternate model is used.
No credentials or redirected signed URLs are recorded. Weights stay in the model cache.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import requests
from huggingface_hub import snapshot_download

os.environ.pop('HF_HUB_OFFLINE',None)
p=Path(__file__).resolve().parent
models=[('diffusers/stable-diffusion-xl-1.0-inpainting-0.1','115134f363124c53c7d878647567d04daf26e41e'),
        ('diffusers/controlnet-canny-sdxl-1.0','eb115a19a10d14909256db740ed109532ab1483c')]
report={'reason':'normal large-file transfer stalled; ranged probes succeeded','files':[]}
for model,revision in models:
    metadata=json.loads((p/'research'/(model.replace('/','--')+'.json')).read_text())
    folder=Path(snapshot_download(model,revision=revision,allow_patterns=['*.json','*.txt','README.md','LICENSE*'],max_workers=2))
    for item in metadata['siblings']:
        name=item['rfilename']
        if not name.endswith('.fp16.safetensors'):continue
        expected=item['lfs']['sha256'];size=item['size'];target=folder/name
        target.parent.mkdir(parents=True,exist_ok=True)
        def digest(path):
            h=hashlib.sha256()
            with path.open('rb') as f:
                for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
            return h.hexdigest()
        tick=time.perf_counter()
        if target.exists() and target.stat().st_size==size and digest(target)==expected:
            report['files'].append({'model':model,'revision':revision,'filename':name,'bytes':size,'sha256':expected,'verification':'existing complete file matched'})
            continue
        partial=target.with_suffix(target.suffix+'.phase8_ranges')
        progress=target.with_suffix(target.suffix+'.phase8_progress.json')
        blocksize=16*1024*1024
        chunks=[(start,min(start+blocksize-1,size-1)) for start in range(0,size,blocksize)]
        completed=set(json.loads(progress.read_text())) if progress.exists() and partial.exists() else set()
        if not partial.exists():
            with partial.open('wb') as f:f.truncate(size)
        lock=threading.Lock()
        def fetch(pair):
            start,end=pair
            if start in completed:return
            for attempt in range(2):
                try:
                    url=f'https://huggingface.co/{model}/resolve/{revision}/{name}?download=true&range_start={start}'
                    response=requests.get(url,headers={'Range':f'bytes={start}-{end}'},timeout=(20,90))
                    response.raise_for_status()
                    if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}' or len(response.content)!=end-start+1:
                        raise ValueError('range response does not match requested pinned file extent')
                    with lock:
                        with partial.open('r+b') as f:f.seek(start);f.write(response.content)
                        completed.add(start);progress.write_text(json.dumps(sorted(completed)))
                    return
                except Exception:
                    if attempt:raise
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures=[pool.submit(fetch,pair) for pair in chunks]
            for future in as_completed(futures):
                future.result()
                if len(completed)%16==0:print(model,name,len(completed),len(chunks),flush=True)
        actual=digest(partial)
        if actual!=expected:raise ValueError('downloaded weight checksum mismatch')
        partial.replace(target)
        report['files'].append({'model':model,'revision':revision,'filename':name,'bytes':size,'sha256':actual,
            'verification':'full SHA-256 matched official pinned LFS metadata','download_seconds':time.perf_counter()-tick})
        (p/'weight_checksums.json').write_text(json.dumps(report,indent=2))
(p/'weight_checksums.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
