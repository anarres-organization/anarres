#!/usr/bin/env python3
"""Freeze an already officially scored train-side calibration panel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def train_tasks(checkout: Path) -> set[str]:
    split_path = checkout / "state_bench/domains/customer_support/splits/train_test.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))["splits"]
    return set(split["train"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--official-results-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    checkout = arguments.checkout.resolve()
    results = arguments.official_results_dir.resolve()
    output = arguments.output.resolve()
    source = audit_checkout(checkout)
    allowed = train_tasks(checkout)
    entries = []
    for path in sorted(results.glob("run*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        task_id = record.get("task_id")
        if task_id not in allowed:
            raise SystemExit(f"calibration includes a non-training task: {task_id}")
        if record.get("task_requirements_met") not in {0, 1}:
            raise SystemExit(f"trajectory is missing an official task score: {path}")
        task_path = checkout / "state_bench/domains/customer_support/tasks" / f"{task_id}.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        entries.append(
            {
                "run_index": int(path.parent.name.removeprefix("run")),
                "task_id": task_id,
                "task_type": task["task_type"],
                "trajectory_relative_path": str(path.relative_to(results)),
                "trajectory_sha256": sha256(path),
                "task_definition_sha256": sha256(task_path),
            }
        )
    if not entries:
        raise SystemExit("no officially scored train-side trajectories found")

    panel = {
        "schema_version": 1,
        "status": "DEVELOPMENT_JUDGE_CALIBRATION_FROZEN",
        "source_revision": source["revision"],
        "official_results_dir_name": results.name,
        "trajectory_count": len(entries),
        "entries": entries,
        "acceptance_gate": {
            "task_requirement_agreement_minimum": 0.9,
            "false_pass_rate_maximum": 0.1,
            "manual_audit_required_for_every_disagreement": True,
            "automatic_qualification": False,
        },
    }
    panel["panel_sha256"] = canonical_digest(panel)
    serialized = json.dumps(panel, indent=2, sort_keys=True) + "\n"
    if output.exists() and output.read_text(encoding="utf-8") != serialized:
        raise SystemExit(f"refusing to replace a different frozen panel: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
