#!/usr/bin/env python3
"""Bind one candidate arm to its learning artifact before held-out evaluation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPERATOR_SPEC = importlib.util.spec_from_file_location(
    "anarres_learning_operator",
    ROOT / "execution/state_bench_extension/anarres_learning_operator.py",
)
OPERATOR_MODULE = importlib.util.module_from_spec(OPERATOR_SPEC)
assert OPERATOR_SPEC.loader is not None
OPERATOR_SPEC.loader.exec_module(OPERATOR_MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(
    candidate_plan: dict,
    candidate_plan_sha256: str,
    arm: str,
    artifact: Path | None,
    artifact_relative_path: str | None = None,
    build_cost_usd: float | None = None,
    build_wall_time_seconds: float | None = None,
) -> dict:
    if not candidate_plan.get("status", "").startswith("CANDIDATES_AND_PREDICTION_FROZEN"):
        raise ValueError("candidate plan is not frozen")
    if candidate_plan.get("held_out_outcomes_opened") is not False:
        raise ValueError("candidate plan does not preserve unopened outcomes")
    candidates = candidate_plan["candidates"]
    if arm == "no_learning":
        if artifact is not None:
            raise ValueError("no_learning must not receive a candidate learning artifact")
        membership = None
        artifact_hash = None
        artifact_relative_path = None
        build_cost_usd = 0.0
        build_wall_time_seconds = 0.0
    else:
        if arm not in candidates:
            raise ValueError(f"unknown candidate arm: {arm}")
        if artifact is None or not artifact.is_file():
            raise ValueError(f"{arm} requires a materialized learning artifact")
        if not artifact_relative_path:
            raise ValueError(f"{arm} requires a retained learning-artifact path")
        if build_cost_usd is None or build_cost_usd < 0:
            raise ValueError(f"{arm} requires non-negative learning build cost")
        if build_wall_time_seconds is None or build_wall_time_seconds < 0:
            raise ValueError(f"{arm} requires non-negative learning build wall time")
        membership = candidates[arm]["membership_sha256"]
        artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
        OPERATOR_MODULE.validate_artifact(artifact_payload)
        expected_operator = candidate_plan["run_contract"]["learning_operator"]["id"]
        if (
            artifact_payload.get("operator_id") != expected_operator
            or artifact_payload.get("candidate_plan_sha256") != candidate_plan_sha256
            or artifact_payload.get("arm") != arm
            or artifact_payload.get("candidate_membership_sha256") != membership
            or artifact_payload.get("record_count") != candidate_plan.get("candidate_size")
        ):
            raise ValueError(f"{arm} learning artifact differs from the frozen candidate")
        artifact_hash = sha256(artifact)
    run_contract = candidate_plan["run_contract"]
    return {
        "schema_version": 1,
        "study_id": candidate_plan["study_id"],
        "status": "ARM_READY__HELD_OUT_OUTCOMES_UNOPENED",
        "held_out_outcomes_opened": False,
        "arm": arm,
        "candidate_plan_sha256": candidate_plan_sha256,
        "run_contract_sha256": candidate_plan["freeze_inputs"]["run_contract_sha256"],
        "candidate_membership_sha256": membership,
        "learning_artifact_sha256": artifact_hash,
        "learning_artifact_relative_path": artifact_relative_path,
        "learning_artifact_build_cost_usd": build_cost_usd,
        "learning_artifact_build_wall_time_seconds": build_wall_time_seconds,
        "starting_agent": run_contract["starting_agent"],
        "learning_operator": run_contract["learning_operator"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-plan", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--learning-artifact", type=Path)
    parser.add_argument("--learning-build-cost-usd", type=float)
    parser.add_argument("--learning-build-wall-time-seconds", type=float)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    candidate_plan = json.loads(arguments.candidate_plan.read_text(encoding="utf-8"))
    artifact = arguments.learning_artifact.resolve() if arguments.learning_artifact else None
    artifact_relative_path = None
    if artifact is not None:
        try:
            artifact_relative_path = str(artifact.relative_to(arguments.output.parent.resolve()))
        except ValueError as exc:
            raise ValueError(
                "learning artifact must be retained inside the arm result directory"
            ) from exc
    result = prepare(
        candidate_plan,
        sha256(arguments.candidate_plan),
        arguments.arm,
        artifact,
        artifact_relative_path,
        arguments.learning_build_cost_usd,
        arguments.learning_build_wall_time_seconds,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "arm": result["arm"],
                "learning_artifact_sha256": result["learning_artifact_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
