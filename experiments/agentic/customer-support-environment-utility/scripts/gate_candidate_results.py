#!/usr/bin/env python3
"""Verify candidate result completeness before scientific outcomes are aggregated."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_arms(values: list[str]) -> dict[str, Path]:
    arms = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--arm must use NAME=RESULTS_DIRECTORY")
        name, raw_path = value.split("=", 1)
        if not name or name in arms:
            raise ValueError(f"invalid or duplicate arm name: {name!r}")
        arms[name] = Path(raw_path).resolve()
    return arms


def require_number(record: dict, name: str, path: Path) -> float:
    value = record.get(name)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{path}: {name} must be numeric")
    return float(value)


def require_binary(record: dict, name: str, path: Path) -> int:
    value = record.get(name)
    if value not in (0, 1, False, True):
        raise ValueError(f"{path}: {name} must be scored as 0 or 1")
    return int(value)


def validate_trajectory(path: Path, task_id: str, expected_agent: dict | None = None) -> dict:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: missing or malformed trajectory") from exc
    if record.get("task_id") != task_id:
        raise ValueError(f"{path}: task identity mismatch")
    if record.get("error"):
        raise ValueError(f"{path}: runtime error remains in trajectory")
    require_binary(record, "task_completion_pass", path)
    require_binary(record, "state_requirements_met", path)
    require_binary(record, "task_requirements_met", path)
    normalized = dict(record)
    token_usage = record.get("token_usage") if isinstance(record.get("token_usage"), dict) else {}
    for field in ("input_tokens", "output_tokens"):
        value = record.get(field, token_usage.get(field))
        normalized[field] = value
        require_number(normalized, field, path)
    for field in ("ux_score", "tool_calls", "tool_errors", "redundant_calls"):
        require_number(normalized, field, path)
    if require_number(normalized, "input_tokens", path) < 0:
        raise ValueError(f"{path}: input_tokens must be non-negative")
    if require_number(normalized, "output_tokens", path) <= 0:
        raise ValueError(f"{path}: output_tokens must be positive")
    if require_number(normalized, "tool_calls", path) < 0:
        raise ValueError(f"{path}: tool_calls must be non-negative")
    normalized["cost_usd"] = record.get("cost_usd", token_usage.get("total_cost_usd"))
    if require_number(normalized, "cost_usd", path) < 0:
        raise ValueError(f"{path}: cost_usd must be non-negative")
    agent_model = record.get("agent_model")
    if not isinstance(agent_model, dict) or not str(agent_model.get("model_name", "")).strip():
        raise ValueError(f"{path}: agent_model identity is missing")
    observed_agent = {
        "model_name": str(agent_model["model_name"]).strip(),
        "reasoning_level": (
            str(agent_model["reasoning_level"]).strip() or None
            if agent_model.get("reasoning_level") is not None
            else None
        ),
    }
    normalized["agent_model"] = observed_agent
    if expected_agent is not None and (
        observed_agent["model_name"] != expected_agent.get("model_name")
        or observed_agent["reasoning_level"] != expected_agent.get("reasoning_level")
    ):
        raise ValueError(f"{path}: trajectory agent differs from the frozen run contract")
    return normalized


def gate_results(
    checkout: Path,
    candidate_plan_path: Path,
    protocol_path: Path,
    scoring_path: Path,
    arms: dict[str, Path],
) -> dict:
    source = audit_checkout(checkout)
    candidate_plan = json.loads(candidate_plan_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
    if candidate_plan.get("held_out_outcomes_opened") is not False:
        raise ValueError("candidate plan does not preserve unopened held-out outcomes")
    if not candidate_plan.get("status", "").startswith("CANDIDATES_AND_PREDICTION_FROZEN"):
        raise ValueError("candidate plan is not frozen")
    if scoring.get("held_out_outcomes_opened") is not False:
        raise ValueError("scoring contract does not preserve unopened held-out outcomes")
    if not scoring.get("status", "").startswith("SCORING_CONTRACT_FROZEN"):
        raise ValueError("scoring contract is not frozen")
    if any(item.get("study_id") != protocol["study_id"] for item in (candidate_plan, scoring)):
        raise ValueError("study identities do not match")
    if candidate_plan.get("predicted_choice") != scoring["predicted_choice"]:
        raise ValueError("candidate prediction differs from the scoring contract")
    if set(candidate_plan["candidates"]) != set(scoring["candidate_arms"]):
        raise ValueError("candidate plan differs from the scoring arms")
    expected_arms = {scoring["baseline_arm"], *scoring["candidate_arms"]}
    if set(arms) != expected_arms:
        raise ValueError("result directories do not match the required arms")
    if source["test_split_count"] != protocol["source"]["held_out_task_count"]:
        raise ValueError("qualified test-split count differs from the protocol")
    if source["official_runs_per_task"] != scoring["runs_per_task"]:
        raise ValueError("qualified run count differs from the scoring contract")

    domain_root = checkout / "state_bench" / "domains" / "customer_support"
    split = json.loads((domain_root / "splits" / "train_test.json").read_text())["splits"]
    task_ids = list(split["test"])
    runs = int(scoring["runs_per_task"])
    records = []
    cost_complete = True
    learning_artifacts = {}
    for arm in sorted(arms):
        root = arms[arm]
        manifest_path = root / "ARM_MANIFEST.json"
        if not manifest_path.is_file():
            raise ValueError(f"{arm}: ARM_MANIFEST.json is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_membership = (
            None
            if arm == scoring["baseline_arm"]
            else candidate_plan["candidates"][arm]["membership_sha256"]
        )
        if (
            manifest.get("study_id") != protocol["study_id"]
            or manifest.get("status") != "ARM_READY__HELD_OUT_OUTCOMES_UNOPENED"
            or manifest.get("held_out_outcomes_opened") is not False
            or manifest.get("arm") != arm
            or manifest.get("candidate_plan_sha256") != sha256(candidate_plan_path)
            or manifest.get("run_contract_sha256")
            != candidate_plan["freeze_inputs"]["run_contract_sha256"]
            or manifest.get("candidate_membership_sha256") != expected_membership
            or manifest.get("starting_agent") != candidate_plan["run_contract"]["starting_agent"]
            or manifest.get("learning_operator")
            != candidate_plan["run_contract"]["learning_operator"]
        ):
            raise ValueError(f"{arm}: arm manifest differs from the frozen contract")
        if arm == scoring["baseline_arm"]:
            if (
                manifest.get("learning_artifact_sha256") is not None
                or manifest.get("learning_artifact_relative_path") is not None
            ):
                raise ValueError("no-learning baseline declares a learning artifact")
            learning_artifacts[arm] = None
        else:
            artifact_hash = manifest.get("learning_artifact_sha256")
            relative_path = manifest.get("learning_artifact_relative_path")
            if not isinstance(artifact_hash, str) or len(artifact_hash) != 64:
                raise ValueError(f"{arm}: learning artifact hash is missing")
            if not isinstance(relative_path, str) or not relative_path:
                raise ValueError(f"{arm}: retained learning artifact is missing")
            artifact_path = (root / relative_path).resolve()
            try:
                artifact_path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"{arm}: learning artifact leaves its result directory") from exc
            if not artifact_path.is_file() or sha256(artifact_path) != artifact_hash:
                raise ValueError(f"{arm}: retained learning artifact differs from its manifest")
            learning_artifacts[arm] = {
                "relative_path": relative_path,
                "sha256": artifact_hash,
                "build_cost_usd": require_number(
                    manifest, "learning_artifact_build_cost_usd", manifest_path
                ),
                "build_wall_time_seconds": require_number(
                    manifest, "learning_artifact_build_wall_time_seconds", manifest_path
                ),
            }
            if (
                learning_artifacts[arm]["build_cost_usd"] < 0
                or learning_artifacts[arm]["build_wall_time_seconds"] < 0
            ):
                raise ValueError(f"{arm}: learning artifact build accounting is negative")
        for run_index in range(1, runs + 1):
            run_dir = root / f"run{run_index}"
            observed_files = {path.name for path in run_dir.glob("*.json")}
            expected_files = {f"{task_id}.json" for task_id in task_ids}
            if observed_files != expected_files:
                raise ValueError(f"{arm}/run{run_index}: task files differ from the test split")
            for task_id in task_ids:
                path = run_dir / f"{task_id}.json"
                trajectory = validate_trajectory(
                    path, task_id, candidate_plan["run_contract"]["starting_agent"]
                )
                cost_complete = cost_complete and trajectory.get("cost_usd") is not None
                records.append(
                    {
                        "arm": arm,
                        "run": run_index,
                        "task_id": task_id,
                        "relative_path": str(path.relative_to(root)),
                        "sha256": sha256(path),
                    }
                )

    expected_records = len(expected_arms) * runs * len(task_ids)
    if len(records) != expected_records:
        raise ValueError("result count differs from the complete arm-run-task matrix")
    return {
        "schema_version": 1,
        "study_id": protocol["study_id"],
        "status": "CANDIDATE_RESULTS_COMPLETE__NOT_SCORED",
        "held_out_outcomes_opened": True,
        "scientific_aggregates_computed": False,
        "source_revision": source["revision"],
        "arms": sorted(expected_arms),
        "runs_per_task": runs,
        "held_out_tasks": len(task_ids),
        "trajectory_records": len(records),
        "cost_accounting_complete": cost_complete,
        "inputs": {
            "candidate_plan_sha256": sha256(candidate_plan_path),
            "protocol_sha256": sha256(protocol_path),
            "scoring_contract_sha256": sha256(scoring_path),
        },
        "records": records,
        "arm_manifests": {arm: sha256(arms[arm] / "ARM_MANIFEST.json") for arm in sorted(arms)},
        "learning_artifacts": learning_artifacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--candidate-plan", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--scoring-contract", type=Path, required=True)
    parser.add_argument("--arm", action="append", default=[], metavar="NAME=DIR")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    result = gate_results(
        arguments.checkout.resolve(),
        arguments.candidate_plan.resolve(),
        arguments.protocol.resolve(),
        arguments.scoring_contract.resolve(),
        parse_arms(arguments.arm),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "arms": len(result["arms"]),
                "held_out_tasks": result["held_out_tasks"],
                "trajectory_records": result["trajectory_records"],
                "cost_accounting_complete": result["cost_accounting_complete"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
