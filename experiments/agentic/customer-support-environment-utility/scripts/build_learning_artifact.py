#!/usr/bin/env python3
"""Build one frozen candidate's episodic-memory artifact from released train trajectories."""

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


def build(checkout: Path, candidate_plan_path: Path, arm: str) -> dict:
    source = audit_checkout(checkout)
    plan = json.loads(candidate_plan_path.read_text(encoding="utf-8"))
    if not str(plan.get("status", "")).startswith("CANDIDATES_AND_PREDICTION_FROZEN"):
        raise ValueError("candidate plan must be prospectively frozen")
    if plan.get("held_out_outcomes_opened") is not False:
        raise ValueError("candidate plan does not preserve unopened held-out outcomes")
    if (
        plan.get("run_contract", {}).get("learning_operator", {}).get("id")
        != OPERATOR_MODULE.OPERATOR_ID
    ):
        raise ValueError("run contract names a different learning operator")
    candidate = plan.get("candidates", {}).get(arm)
    if candidate is None:
        raise ValueError(f"unknown candidate arm: {arm}")
    task_ids = candidate.get("task_ids")
    if not isinstance(task_ids, list) or len(task_ids) != plan.get("candidate_size"):
        raise ValueError("candidate membership is incomplete")
    train_root = checkout / "datasets/train_task_trajectories/customer_support"
    return OPERATOR_MODULE.build_artifact(
        train_root,
        task_ids,
        source_revision=source["revision"],
        candidate_plan_sha256=sha256(candidate_plan_path),
        arm=arm,
        expected_membership_sha256=candidate["membership_sha256"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--candidate-plan", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    payload = build(arguments.checkout.resolve(), arguments.candidate_plan.resolve(), arguments.arm)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "operator_id": payload["operator_id"],
                "arm": payload["arm"],
                "records": payload["record_count"],
                "output_sha256": sha256(arguments.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
