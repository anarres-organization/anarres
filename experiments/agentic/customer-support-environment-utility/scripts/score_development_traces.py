#!/usr/bin/env python3
"""Score train-side STATE-Bench traces with a local development judge.

The script never mutates benchmark trajectories and never emits official
STATE-Bench scores.  Each result is a sidecar bound to the source trajectory,
task definition, benchmark prompts, and local model revision.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout

_LEDGER_LOCK = threading.Lock()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set")
    return value


def load_state_bench(checkout: Path) -> dict[str, Any]:
    checkout_text = str(checkout)
    if checkout_text not in sys.path:
        sys.path.insert(0, checkout_text)
    from state_bench.domain import get_domain_config
    from state_bench.schemas import StateDiff, TaskDefinition
    from state_bench.scoring import (
        TaskRequirementsJudge,
        combine_task_completion,
        compute_efficiency,
        evaluate_state_requirements,
    )

    return {
        "get_domain_config": get_domain_config,
        "StateDiff": StateDiff,
        "TaskDefinition": TaskDefinition,
        "TaskRequirementsJudge": TaskRequirementsJudge,
        "combine_task_completion": combine_task_completion,
        "compute_efficiency": compute_efficiency,
        "evaluate_state_requirements": evaluate_state_requirements,
    }


class LocalJudgeClient:
    """Minimal OpenAI-compatible client for a local vLLM judge."""

    def __init__(self, *, ledger: Path | None = None):
        from openai import OpenAI

        self.base_url = required_env("ANARRES_DEVELOPMENT_JUDGE_BASE_URL").rstrip("/")
        self.model = required_env("ANARRES_DEVELOPMENT_JUDGE_MODEL")
        self.revision = required_env("ANARRES_DEVELOPMENT_JUDGE_MODEL_REVISION")
        self.seed = int(os.environ.get("ANARRES_DEVELOPMENT_JUDGE_SEED", "1729"))
        template_kwargs_text = os.environ.get(
            "ANARRES_DEVELOPMENT_JUDGE_CHAT_TEMPLATE_KWARGS",
            '{"enable_thinking": false}',
        )
        self.chat_template_kwargs = json.loads(template_kwargs_text)
        if not isinstance(self.chat_template_kwargs, dict):
            raise ValueError("ANARRES_DEVELOPMENT_JUDGE_CHAT_TEMPLATE_KWARGS must be a JSON object")
        self.reasoning_effort = (
            os.environ.get("ANARRES_DEVELOPMENT_JUDGE_REASONING_EFFORT", "").strip() or None
        )
        if self.reasoning_effort not in {None, "low", "medium", "high"}:
            raise ValueError(
                "ANARRES_DEVELOPMENT_JUDGE_REASONING_EFFORT must be low, medium, or high"
            )
        self.ledger = ledger
        self._client = OpenAI(
            api_key=os.environ.get("ANARRES_DEVELOPMENT_JUDGE_API_KEY", "local"),
            base_url=self.base_url,
        )
        self._context = threading.local()

    def set_context(self, *, task_id: str, run_index: int) -> None:
        self._context.value = {"task_id": task_id, "run_index": run_index}

    def request_parameters(self, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        parameters = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
            "seed": self.seed,
            "response_format": {"type": "json_object"},
        }
        if self.chat_template_kwargs:
            parameters["extra_body"] = {"chat_template_kwargs": self.chat_template_kwargs}
        if self.reasoning_effort is not None:
            parameters["reasoning_effort"] = self.reasoning_effort
        return parameters

    def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 16384,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        del reasoning_effort
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        started = time.monotonic()
        response = self._client.chat.completions.create(
            **self.request_parameters(messages, max_tokens)
        )
        elapsed = time.monotonic() - started
        usage = response.usage
        record = {
            **getattr(self._context, "value", {}),
            "request_id": response.id,
            "purpose": "development_task_requirements_judge",
            "configured_model": self.model,
            "returned_model": response.model,
            "model_revision": self.revision,
            "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            "latency_seconds": elapsed,
        }
        if self.ledger is not None:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with _LEDGER_LOCK, self.ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        content = response.choices[0].message.content or "{}"
        return json.loads(content)


def state_diff_from_record(record: dict[str, Any], StateDiff: Any) -> Any:
    raw = record.get("state_diff")
    if raw is None:
        return StateDiff(created={}, modified={}, deleted={})
    if not isinstance(raw, dict) or not {"created", "modified", "deleted"}.issubset(raw):
        raise ValueError("trajectory has malformed state_diff")
    return StateDiff(
        created=raw.get("created", {}),
        modified=raw.get("modified", {}),
        deleted=raw.get("deleted", {}),
    )


def collect_tool_calls(conversation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls = []
    for message in conversation:
        calls.extend(message.get("tool_calls") or [])
    return calls


def judge_contract(
    checkout: Path, client: LocalJudgeClient, modules: dict[str, Any]
) -> dict[str, Any]:
    prompts = checkout / "state_bench/domains/customer_support/prompts"
    domain = modules["get_domain_config"]("customer_support")
    contract = {
        "schema_version": 1,
        "scope": "development_only",
        "official_state_bench_compatible": False,
        "provider": "openai_compatible_local",
        "model": client.model,
        "model_revision": client.revision,
        "seed": client.seed,
        "temperature": 0,
        "chat_template_kwargs": client.chat_template_kwargs,
        "reasoning_effort": client.reasoning_effort,
        "task_requirements_prompt_sha256": sha256(prompts / "judge_task_requirements.md"),
        "judge_system_prompt_sha256": hashlib.sha256(
            domain.judge_system_prompt.encode("utf-8")
        ).hexdigest(),
    }
    return {**contract, "contract_sha256": canonical_digest(contract)}


def score_one(
    *,
    checkout: Path,
    trajectory_path: Path,
    task_path: Path,
    output_path: Path,
    run_index: int,
    client: LocalJudgeClient,
    modules: dict[str, Any],
    contract: dict[str, Any],
    source_revision: str,
) -> dict[str, Any]:
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    task_id = task_path.stem
    if trajectory.get("task_id") != task_id:
        raise ValueError(f"{trajectory_path}: task_id does not match path")
    conversation = trajectory.get("conversation")
    if not isinstance(conversation, list):
        raise ValueError(f"{trajectory_path}: conversation must be a list")

    task = modules["TaskDefinition"].load(task_path)
    state_diff = state_diff_from_record(trajectory, modules["StateDiff"])
    tool_calls = collect_tool_calls(conversation)
    state_result = modules["evaluate_state_requirements"](task, state_diff)
    domain = modules["get_domain_config"]("customer_support")
    judge = modules["TaskRequirementsJudge"](
        client=client,
        prompts_dir=domain.prompts_dir,
        system_prompt=domain.judge_system_prompt,
        reasoning_effort=None,
    )
    client.set_context(task_id=task_id, run_index=run_index)
    task_result = judge.evaluate(task, conversation, tool_calls, state_diff)
    if task_result is None:
        raise RuntimeError("development task-requirements judge returned no score")
    completion = modules["combine_task_completion"](state_result, task_result)
    efficiency = modules["compute_efficiency"](conversation, tool_calls)
    payload = {
        "schema_version": 1,
        "status": "DEVELOPMENT_SCORE_COMPLETE",
        "official_state_bench_compatible": False,
        "task_id": task_id,
        "task_type": task.task_type,
        "run_index": run_index,
        "source_revision": source_revision,
        "trajectory": {
            "relative_path": str(trajectory_path.parent.name + "/" + trajectory_path.name),
            "sha256": sha256(trajectory_path),
        },
        "task_definition_sha256": sha256(task_path),
        "judge_contract": contract,
        "scores": {
            "state_requirements_met": state_result.score if state_result else None,
            "state_requirements_reasoning": state_result.reasoning if state_result else None,
            "state_requirements_details": state_result.details if state_result else None,
            "task_requirements_met": task_result.score,
            "task_requirements_details": task_result.details,
            "task_requirements_reasoning": task_result.reasoning,
            "task_completion_pass": completion,
            "efficiency": efficiency.to_dict(),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        if existing != serialized:
            raise ValueError(f"refusing to replace a different sidecar: {output_path}")
    else:
        output_path.write_text(serialized, encoding="utf-8")
    return payload


def training_tasks(checkout: Path) -> list[str]:
    split_path = checkout / "state_bench/domains/customer_support/splits/train_test.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))["splits"]
    return list(split["train"])


def selected_tasks(checkout: Path, requested: str | None) -> list[str]:
    allowed = training_tasks(checkout)
    if requested is None:
        return allowed
    chosen = [item.strip() for item in requested.split(",") if item.strip()]
    unknown = sorted(set(chosen) - set(allowed))
    if unknown:
        raise ValueError(f"task selection contains non-training tasks: {unknown[:5]}")
    if len(chosen) != len(set(chosen)):
        raise ValueError("task selection contains duplicates")
    return chosen


def planned_inputs(
    results_dir: Path, task_ids: list[str], num_runs: int
) -> list[tuple[int, str, Path]]:
    return [
        (run_index, task_id, results_dir / f"run{run_index}" / f"{task_id}.json")
        for run_index in range(1, num_runs + 1)
        for task_id in task_ids
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-runs", type=int, default=5)
    parser.add_argument("--task-ids", help="Comma-separated training-task IDs; default is all")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.num_runs < 1:
        raise SystemExit("--num-runs must be positive")
    if arguments.workers < 1:
        raise SystemExit("--workers must be positive")

    checkout = arguments.checkout.resolve()
    results_dir = arguments.results_dir.resolve()
    output_dir = arguments.output_dir.resolve()
    source = audit_checkout(checkout)
    task_ids = selected_tasks(checkout, arguments.task_ids)
    inputs = planned_inputs(results_dir, task_ids, arguments.num_runs)
    missing = [str(path) for _, _, path in inputs if not path.is_file()]
    plan = {
        "schema_version": 1,
        "status": "READY_FOR_DEVELOPMENT_SCORING"
        if not missing
        else "BLOCKED_MISSING_TRAJECTORIES",
        "source_revision": source["revision"],
        "task_count": len(task_ids),
        "runs_per_task": arguments.num_runs,
        "planned_sidecars": len(inputs),
        "missing_trajectories": missing,
        "official_state_bench_compatible": False,
        "model_calls_made": 0,
    }
    if not arguments.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    if missing:
        raise SystemExit(json.dumps(plan, indent=2, sort_keys=True))

    ledger = output_dir / "REQUEST_USAGE.jsonl"
    client = LocalJudgeClient(ledger=ledger)
    modules = load_state_bench(checkout)
    contract = judge_contract(checkout, client, modules)
    completed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    def run(item: tuple[int, str, Path]) -> dict[str, Any]:
        run_index, task_id, trajectory_path = item
        task_path = checkout / f"state_bench/domains/customer_support/tasks/{task_id}.json"
        output_path = output_dir / f"run{run_index}/{task_id}.json"
        return score_one(
            checkout=checkout,
            trajectory_path=trajectory_path,
            task_path=task_path,
            output_path=output_path,
            run_index=run_index,
            client=client,
            modules=modules,
            contract=contract,
            source_revision=source["revision"],
        )

    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        futures = {executor.submit(run, item): item for item in inputs}
        for future in as_completed(futures):
            run_index, task_id, _ = futures[future]
            try:
                completed.append(future.result())
            except Exception as exc:
                errors.append({"run_index": run_index, "task_id": task_id, "error": str(exc)})

    sidecars = sorted(output_dir.glob("run*/*.json"))
    manifest = {
        **plan,
        "status": "DEVELOPMENT_SCORING_COMPLETE"
        if not errors
        else "DEVELOPMENT_SCORING_INCOMPLETE",
        "judge_contract": contract,
        "completed_sidecars": len(completed),
        "errors": errors,
        "sidecar_set_sha256": canonical_digest(
            [
                {"path": str(path.relative_to(output_dir)), "sha256": sha256(path)}
                for path in sidecars
            ]
        ),
        "model_calls_made": (
            len(ledger.read_text(encoding="utf-8").splitlines()) if ledger.is_file() else 0
        ),
    }
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
