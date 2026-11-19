"""Observe an already running editor. Interval RSS is not a full-lifetime peak."""
import json
from pathlib import Path
import time
import psutil

p=Path(__file__).resolve().parent
samples=[]
for _ in range(180):
    processes=[]
    for process in psutil.process_iter(['pid','name','cmdline','memory_info']):
        try:
            args=process.info['cmdline'] or []
            if 'scripts.instruction_edit' in args and any('request_seed_42.json' in x for x in args):
                processes.append({'pid':process.pid,'rss':process.info['memory_info'].rss})
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    if not processes:break
    samples.append({'unix_time':time.time(),'editor_processes':processes,'free_system_ram':psutil.virtual_memory().available})
    time.sleep(2)
result={'scope':'observed interval after model load, not full-lifetime RSS peak',
 'samples':samples,'max_observed_editor_rss_sum':max((sum(x['rss'] for x in s['editor_processes']) for s in samples),default=None)}
(p/'case1/seed42_cpu_observation.json').write_text(json.dumps(result,indent=2))
