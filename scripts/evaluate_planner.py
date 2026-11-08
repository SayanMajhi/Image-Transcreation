"""Run the six archived/synthetic planning cases, sequentially and without a VLM."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time

from transcreation.config import load_planner_config
from transcreation.stages.ollama_planner import OllamaPlanner, parse_planning_input


def save(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")


def memory_sample(planner: OllamaPlanner) -> dict:
    sample = {"at": datetime.now(timezone.utc).isoformat()}
    try:
        sample["ollama_ps"] = planner.api("/api/ps", timeout=2)
    except RuntimeError as exc:
        sample["ollama_ps_error"] = str(exc)
    try:
        measured = subprocess.run([
            "nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ], capture_output=True, text=True, timeout=3, check=True)
        sample["nvidia_smi"] = measured.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        sample["nvidia_smi_error"] = str(exc)
    return sample


def measured_run(planner: OllamaPlanner, operation) -> tuple[dict, list[dict]]:
    samples = [memory_sample(planner)]
    stop = threading.Event()

    def sample_loop():
        while not stop.wait(0.5):
            samples.append(memory_sample(planner))

    sampler = threading.Thread(target=sample_loop, daemon=True)
    sampler.start()
    try:
        result = operation()
    finally:
        stop.set()
        sampler.join(timeout=6)
        samples.append(memory_sample(planner))
    return result, samples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/planner.yaml"))
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures/planning/scenarios.json"))
    parser.add_argument("--out", type=Path, required=True, help="New directory; existing evidence is never overwritten")
    args = parser.parse_args()
    config = load_planner_config(args.config)
    if config.keep_alive != 0:
        parser.error("evaluation requires keep_alive: 0 so every scenario unloads its model")
    planner = OllamaPlanner(config)
    args.out.mkdir(parents=True, exist_ok=False)
    environment = {
        "created_at": datetime.now(timezone.utc).isoformat(), "config": asdict(config),
        "ollama_version": planner.api("/api/version"), "tags": planner.api("/api/tags"),
        "initial_memory": memory_sample(planner),
        "strategy": "Qwen only; no VLM import/inference. Sequential requests; keep_alive=0 and explicit unload.",
        "measurement_limits": "Sampled global GPU usage includes desktop apps. Ollama size_vram is a reported allocation, not tensor peak or process RSS. Sampling can miss peaks.",
    }
    save(args.out / "environment.json", environment)

    # Test standalone Qwen before any cultural-planning scenario.
    probe_body = {
        "model": config.model, "stream": False, "keep_alive": 0, "options": {
            **config.options, "num_predict": 32,
        },
        "messages": [{"role": "system", "content": "Return only a JSON object with ready set to true."}],
        "format": {"type": "object", "properties": {"ready": {"type": "boolean"}},
                   "required": ["ready"], "additionalProperties": False},
    }
    start = time.perf_counter()
    probe, samples = measured_run(planner, lambda: planner.api("/api/chat", probe_body))
    planner.unload()
    probe_record = {"request": probe_body, "response": probe, "elapsed_seconds": time.perf_counter() - start,
                    "memory_samples": samples, "resolved_models": environment["tags"]}
    probe_ok = (probe.get("done") is True and probe.get("done_reason") == "stop"
                and json.loads(probe["message"]["content"]) == {"ready": True})
    probe_record["passed"] = probe_ok
    save(args.out / "standalone_probe.json", probe_record)
    if not probe_ok:
        raise RuntimeError("Standalone Qwen test failed; no cultural scenarios were run.")
    print("Standalone Qwen probe passed.", flush=True)

    summary = []
    for scenario in json.loads(args.fixtures.read_text(encoding="utf-8")):
        source = args.fixtures.parent / scenario["input_file"]
        request = parse_planning_input(json.loads(source.read_text(encoding="utf-8")))
        started = time.perf_counter()
        record, samples = measured_run(planner, lambda: planner.record_plan(request))
        record.update(scenario=scenario["name"], fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      provenance=scenario["provenance"], memory_samples=samples,
                      request_wall_seconds=time.perf_counter() - started)
        result = record["planning_result"]
        decision = result["decision"] if result else None
        record["policy_check"] = {
            "expected_decisions": scenario["expected_policy_decisions"],
            "matched": decision in scenario["expected_policy_decisions"],
            "note": "Policy expectations only; not cultural-correctness scores.",
        }
        response = record.get("response") or {}
        summary.append({
            "scenario": scenario["name"], "validation": record["validation"],
            "decision": decision, "elapsed_seconds": record["elapsed_seconds"],
            "prompt_tokens": response.get("prompt_eval_count"), "output_tokens": response.get("eval_count"),
            "policy_check": record["policy_check"], "human_review_notes": "",
        })
        save(args.out / (scenario["name"] + ".json"), record)
        print(scenario["name"], record["validation"]["status"], decision,
              f'{record["elapsed_seconds"]:.2f}s', flush=True)
    save(args.out / "summary.json", summary)
    save(args.out / "final_memory.json", memory_sample(planner))
    if any(row["validation"]["status"] != "valid" for row in summary):
        raise SystemExit("At least one scenario failed. Original errors are recorded; no fallback plans were created.")


if __name__ == "__main__":
    main()
