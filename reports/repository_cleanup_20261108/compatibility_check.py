from pathlib import Path
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import socket
import sys
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from transcreation.config import load_config, load_planner_config
from transcreation.stages import caption, ollama_planner
from transcreation.stages.ollama_planner import OllamaPlanner, parse_planning_input
from transcreation.stages.planning import parse_model_draft, validate_planning_result

root = Path.cwd()
results = {"constants": {
    "caption_prompt": caption.PROMPT, "concise_prompt": caption.CONCISE_PROMPT,
    "processor_settings": caption.PROCESSOR_SETTINGS, "prompt_variants": caption.PROMPTS,
    "planner_system_prompt": ollama_planner.SYSTEM_PROMPT,
    "schema": ollama_planner.planning_result_schema(),
    "caption_config": asdict(load_config(root / "configs/models.yaml")),
    "planner_config": asdict(load_planner_config(root / "configs/planner.yaml")),
}, "runtime_alias": socket.timeout is TimeoutError, "audit_replays": [], "historical_plan_checks": []}
config = load_planner_config(root / "configs/planner.yaml")
for path in sorted((root / "reports").rglob("*.json")):
    if path.parent.name.startswith("repository_cleanup_"):
        continue
    try:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError):
        continue
    if not isinstance(record, dict) or not isinstance(record.get("input"), dict):
        continue
    response = record.get("response")
    if not isinstance(response, dict) or not isinstance(response.get("message"), dict):
        continue
    if not isinstance(response["message"].get("content"), str):
        continue
    source = path.relative_to(root).as_posix()
    request = parse_planning_input(record["input"])
    calls = []
    def transport(req, timeout):
        body = json.loads(req.data) if req.data else None
        calls.append({"url": req.full_url, "body": body, "timeout": timeout})
        if req.full_url.endswith("/api/tags"):
            data = {"models": [{"name": config.model, "digest": "cleanup-fixed-fixture-digest"}]}
        elif body["messages"] == []:
            data = {"done": True, "done_reason": "unload"}
        else:
            data = deepcopy(response)
        opened = MagicMock()
        opened.__enter__.return_value.read.return_value = json.dumps(data).encode()
        return opened
    with patch("transcreation.stages.ollama_planner.urlopen", side_effect=transport), \
         patch("transcreation.stages.ollama_planner.time.perf_counter", side_effect=[10.0, 10.5]), \
         patch("transcreation.stages.ollama_planner.datetime") as clock:
        clock.now.return_value.isoformat.return_value = "cleanup-fixed-time"
        replay = OllamaPlanner(config).record_plan(request)
    results["audit_replays"].append({"source": source, "record": replay, "http_calls": calls})
    final = replay.get("planning_result")
    if final and final["decision"] in ("REVIEW", "ABSTAIN"):
        assert final["candidate_edits"] == (), source
    assert replay["validation"].get("automatically_authorized", False) is False
    try:
        raw = json.loads(response["message"]["content"])
        draft, issues = parse_model_draft(raw)
        validated, codes = validate_planning_result(request, draft, issues)
        results["historical_plan_checks"].append({"source": source, "final": asdict(validated), "issues": codes})
    except (ValueError, TypeError, KeyError) as error:
        results["historical_plan_checks"].append({"source": source, "error_type": type(error).__name__, "error": str(error)})

fixtures = []
for path in sorted((root / "tests/fixtures/planning").glob("*.json")):
    if path.name == "scenarios.json":
        continue
    request = parse_planning_input(json.loads(path.read_text()))
    fixtures.append({"file": path.name, "input": asdict(request)})
results["fixtures"] = fixtures
Path(sys.argv[1]).write_text(json.dumps(results, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print("Full deterministic audit replays:", len(results["audit_replays"]), "; input fixtures:", len(fixtures))
