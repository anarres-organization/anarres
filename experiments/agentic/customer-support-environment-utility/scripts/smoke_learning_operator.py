#!/usr/bin/env python3
"""Run an outcome-blind, model-free smoke test of the learning operator."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout

OPERATOR_SPEC = importlib.util.spec_from_file_location(
    "anarres_learning_operator",
    ROOT / "execution/state_bench_extension/anarres_learning_operator.py",
)
OPERATOR_MODULE = importlib.util.module_from_spec(OPERATOR_SPEC)
assert OPERATOR_SPEC.loader is not None
OPERATOR_SPEC.loader.exec_module(OPERATOR_MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_key(task_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"customer-support-smoke-v1\0{task_id}".encode()).hexdigest()
    return digest, task_id


def smoke(checkout: Path, smoke_plan: dict) -> tuple[dict, dict]:
    source = audit_checkout(checkout)
    if smoke_plan.get("source_revision") != source["revision"]:
        raise ValueError("smoke plan source revision differs from the checkout")
    domain_root = checkout / "state_bench/domains/customer_support"
    split = json.loads((domain_root / "splits/train_test.json").read_text())["splits"]
    train_ids = set(split["train"])
    test_ids = set(split["test"])
    task_types = {
        task_id: json.loads((domain_root / "tasks" / f"{task_id}.json").read_text())["task_type"]
        for task_id in train_ids
    }
    expected = []
    for family in sorted(set(task_types.values())):
        family_ids = [task_id for task_id in train_ids if task_types[task_id] == family]
        expected.append(min(family_ids, key=stable_key))
    task_ids = smoke_plan.get("task_ids")
    if sorted(task_ids) != sorted(expected) or set(task_ids) & test_ids:
        raise ValueError("smoke task membership differs from the frozen train-only rule")
    membership = OPERATOR_MODULE.membership_hash(task_ids)
    artifact = OPERATOR_MODULE.build_artifact(
        checkout / "datasets/train_task_trajectories/customer_support",
        task_ids,
        source_revision=source["revision"],
        candidate_plan_sha256=hashlib.sha256(
            json.dumps(smoke_plan, sort_keys=True).encode()
        ).hexdigest(),
        arm="smoke_only",
        expected_membership_sha256=membership,
    )
    self_retrievals = 0
    for record in artifact["records"]:
        retrieved = OPERATOR_MODULE.retrieve(artifact, record["retrieval_text"], top_k=3)
        self_retrievals += int(record["learning"] in retrieved)
    result = {
        "schema_version": 1,
        "status": "LEARNING_OPERATOR_SMOKE_PASSED__NO_MODEL_CALLS_MADE",
        "source_revision": source["revision"],
        "train_tasks": len(task_ids),
        "task_families": len(set(task_types[task_id] for task_id in task_ids)),
        "artifact_records": artifact["record_count"],
        "self_retrieval_at_3": self_retrievals / len(task_ids),
        "held_out_task_overlap": len(set(task_ids) & test_ids),
        "model_calls_made": 0,
        "scientific_outcomes_opened": False,
    }
    return artifact, result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--smoke-plan", type=Path, default=ROOT / "SMOKE_PLAN.json")
    parser.add_argument("--artifact-output", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    plan = json.loads(arguments.smoke_plan.read_text(encoding="utf-8"))
    artifact, result = smoke(arguments.checkout.resolve(), plan)
    if arguments.artifact_output:
        if arguments.artifact_output.exists():
            raise FileExistsError(arguments.artifact_output)
        arguments.artifact_output.parent.mkdir(parents=True, exist_ok=True)
        arguments.artifact_output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
        result["artifact_sha256"] = sha256(arguments.artifact_output)
    if arguments.output:
        if arguments.output.exists():
            raise FileExistsError(arguments.output)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
