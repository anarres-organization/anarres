#!/usr/bin/env python3
"""Plan or execute the frozen train-side STATE-Bench model smoke."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PREFLIGHT_SPEC = importlib.util.spec_from_file_location(
    "preflight_execution", Path(__file__).with_name("preflight_execution.py")
)
PREFLIGHT_MODULE = importlib.util.module_from_spec(PREFLIGHT_SPEC)
assert PREFLIGHT_SPEC.loader is not None
PREFLIGHT_SPEC.loader.exec_module(PREFLIGHT_MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_command(
    task_ids: list[str],
    output_dir: Path,
    model_name: str,
    reasoning_level: str | None,
    workers: int,
    provider: str,
    api_key_var: str,
) -> list[str]:
    command = [
        "uv",
        "run",
        "python",
        "-m",
        "state_bench.scripts.run_batch",
        "--domain",
        "customer_support",
        "--tasks",
        ",".join(task_ids),
        "--num-runs",
        "2",
        "--agent-class",
        "AnarresEpisodicMemoryAgent",
        "--agent-model-name",
        model_name,
        "--agent-provider",
        provider,
        "--agent-api-key-var",
        api_key_var,
        "--retrieve-learnings-top-k",
        "3",
        "--retry-attempts",
        "1",
        "--num-workers",
        str(workers),
        "--output-dir",
        str(output_dir),
    ]
    if reasoning_level:
        command.extend(["--agent-model-reasoning-level", reasoning_level])
    return command


def inspect_outputs(output_dir: Path, task_ids: list[str], runs: int) -> tuple[list[dict], bool]:
    records = []
    complete = True
    for run_index in range(1, runs + 1):
        for task_id in task_ids:
            path = output_dir / f"run{run_index}" / f"{task_id}.json"
            record = {
                "run": run_index,
                "task_id": task_id,
                "relative_path": str(path.relative_to(output_dir)),
                "present": path.is_file(),
            }
            if path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                token_usage = payload.get("token_usage", {})
                task_identity_match = payload.get("task_id") == task_id
                scoring_complete = all(
                    payload.get(name) is not None
                    for name in (
                        "state_requirements_met",
                        "task_requirements_met",
                        "task_completion_pass",
                        "ux_score",
                    )
                )
                token_accounting_complete = all(
                    isinstance(token_usage.get(name), int)
                    and not isinstance(token_usage.get(name), bool)
                    and token_usage[name] >= 0
                    for name in ("input_tokens", "output_tokens", "total_tokens")
                )
                record.update(
                    {
                        "sha256": sha256(path),
                        "runtime_error": bool(payload.get("error")),
                        "task_identity_match": task_identity_match,
                        "scoring_complete": scoring_complete,
                        "token_accounting_complete": token_accounting_complete,
                        "input_tokens": payload.get(
                            "input_tokens", token_usage.get("input_tokens")
                        ),
                        "output_tokens": payload.get(
                            "output_tokens", token_usage.get("output_tokens")
                        ),
                        "cost_usd": payload.get("cost_usd", token_usage.get("total_cost_usd")),
                    }
                )
                complete = complete and all(
                    (
                        not record["runtime_error"],
                        task_identity_match,
                        scoring_complete,
                        token_accounting_complete,
                    )
                )
            else:
                complete = False
            records.append(record)
    return records, complete


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--agent-model-name", required=True)
    parser.add_argument(
        "--agent-provider",
        choices=["azure_openai", "openai"],
        default=os.environ.get("STATE_BENCH_AGENT_PROVIDER", "azure_openai"),
    )
    parser.add_argument("--agent-api-key-var")
    parser.add_argument("--reasoning-level", choices=["low", "medium", "high"])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.workers < 1:
        raise ValueError("workers must be positive")
    checkout = arguments.checkout.resolve()
    output_dir = arguments.output_dir.resolve()
    api_key_var = arguments.agent_api_key_var or (
        "OPENAI_API_KEY" if arguments.agent_provider == "openai" else "STATE_BENCH_AGENT_API_KEY"
    )
    if not api_key_var.isidentifier():
        raise ValueError("agent API-key variable must be a valid environment-variable name")
    smoke_plan = json.loads((ROOT / "SMOKE_PLAN.json").read_text(encoding="utf-8"))
    command = build_command(
        smoke_plan["task_ids"],
        output_dir,
        arguments.agent_model_name,
        arguments.reasoning_level,
        arguments.workers,
        arguments.agent_provider,
        api_key_var,
    )
    plan = {
        "status": "TRAIN_SIDE_MODEL_SMOKE_PLANNED",
        "source_revision": smoke_plan["source_revision"],
        "tasks": len(smoke_plan["task_ids"]),
        "runs_per_task": smoke_plan["runs_per_task"],
        "expected_trajectories": len(smoke_plan["task_ids"]) * smoke_plan["runs_per_task"],
        "execution_contract": {
            "agent_class": "AnarresEpisodicMemoryAgent",
            "retrieve_learnings_top_k": 3,
            "retry_attempts": 1,
            "inline_scoring": "task/state and UX",
        },
        "credential_values_recorded": False,
    }
    if not arguments.execute:
        print(json.dumps(plan, indent=2))
        return
    if output_dir.exists():
        raise FileExistsError(output_dir)
    readiness = PREFLIGHT_MODULE.preflight(
        checkout,
        provider=arguments.agent_provider,
        agent_api_key_var=api_key_var,
        agent_model_name=arguments.agent_model_name,
    )
    if readiness["status"] != "READY_FOR_TRAIN_SIDE_MODEL_SMOKE":
        raise RuntimeError("execution preflight is not ready")
    output_dir.mkdir(parents=True)
    environment = os.environ.copy()
    environment.pop("ANARRES_STATE_LEARNINGS_PATH", None)
    started = time.time()
    with (
        (output_dir / "runner.stdout.log").open("w", encoding="utf-8") as stdout_file,
        (output_dir / "runner.stderr.log").open("w", encoding="utf-8") as stderr_file,
    ):
        completed = subprocess.run(
            command,
            cwd=checkout,
            env=environment,
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
        )
    records, complete = inspect_outputs(
        output_dir, smoke_plan["task_ids"], smoke_plan["runs_per_task"]
    )
    ledger = {
        **plan,
        "status": (
            "TRAIN_SIDE_MODEL_SMOKE_COMPLETE"
            if complete and completed.returncode == 0
            else "TRAIN_SIDE_MODEL_SMOKE_INCOMPLETE"
        ),
        "process_return_code": completed.returncode,
        "wall_time_seconds": time.time() - started,
        "failed_attempt_cost_accounting": (
            "complete because no failed attempts were observed"
            if complete
            else "unresolved; reconcile provider billing before any prospective freeze"
        ),
        "cost_scope": (
            "agent-side token and cost ledger exposed by STATE-Bench; "
            "simulator and judge provider costs require separate reconciliation"
        ),
        "records": records,
        "stdout_sha256": sha256(output_dir / "runner.stdout.log"),
        "stderr_sha256": sha256(output_dir / "runner.stderr.log"),
    }
    ledger_path = output_dir / "ATTEMPT_LEDGER.json"
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": ledger["status"],
                "records": len(records),
                "ledger": str(ledger_path),
            },
            indent=2,
        )
    )
    if ledger["status"] != "TRAIN_SIDE_MODEL_SMOKE_COMPLETE":
        sys.exit(1)


if __name__ == "__main__":
    main()
