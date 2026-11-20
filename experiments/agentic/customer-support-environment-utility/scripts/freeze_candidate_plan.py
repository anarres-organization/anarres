#!/usr/bin/env python3
"""Bind a qualified candidate draft to one executable learning contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_text(payload: dict, path: tuple[str, ...]) -> None:
    value = payload
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("run contract lacks " + ".".join(path))


def freeze(draft: dict, protocol: dict, scoring: dict, run_contract: dict) -> dict:
    study_id = protocol["study_id"]
    if any(item.get("study_id") != study_id for item in (draft, scoring, run_contract)):
        raise ValueError("study identities do not match")
    if draft.get("status") != "DRAFT_CANDIDATE_PLAN__HELD_OUT_OUTCOMES_UNOPENED":
        raise ValueError("candidate input is not an outcome-blind draft")
    if draft.get("held_out_outcomes_opened") is not False:
        raise ValueError("candidate draft does not preserve unopened outcomes")
    if scoring.get("held_out_outcomes_opened") is not False:
        raise ValueError("scoring contract does not preserve unopened outcomes")
    if not scoring.get("status", "").startswith("SCORING_CONTRACT_FROZEN"):
        raise ValueError("scoring contract is not frozen")
    if run_contract.get("status") != "READY_TO_FREEZE":
        raise ValueError("run contract must be marked READY_TO_FREEZE")
    for path in (
        ("starting_agent", "model_name"),
        ("starting_agent", "model_revision"),
        ("starting_agent", "agent_class"),
        ("starting_agent", "client_class"),
        ("learning_operator", "id"),
        ("learning_operator", "revision"),
        ("learning_operator", "artifact_builder"),
        ("infrastructure", "attempt_ledger"),
        ("infrastructure", "failed_attempt_cost_accounting"),
    ):
        require_text(run_contract, path)
    if run_contract.get("candidate_size") != draft["candidate_size"]:
        raise ValueError("run-contract candidate size differs from the draft")
    measured_agent = draft.get("starting_agent", {})
    frozen_agent = run_contract.get("starting_agent", {})
    if measured_agent.get("model_name") != frozen_agent.get("model_name") or measured_agent.get(
        "reasoning_level"
    ) != frozen_agent.get("reasoning_level"):
        raise ValueError("run-contract starting agent differs from the measured agent")
    if run_contract.get("held_out_runs_per_task") != scoring["runs_per_task"]:
        raise ValueError("held-out run count differs from the scoring contract")
    if run_contract.get("development_runs_per_task", 0) < 2:
        raise ValueError("development measurement requires at least two runs per task")
    retry_attempts = run_contract.get("infrastructure", {}).get("retry_attempts")
    if not isinstance(retry_attempts, int) or retry_attempts < 1:
        raise ValueError("run contract must declare a positive retry-attempt limit")
    if run_contract.get("learning_operator", {}).get("retrieval_top_k") != 3:
        raise ValueError("STATE-Bench requires retrieve_learnings_top_k=3")
    evaluation = run_contract.get("evaluation", {})
    if evaluation != {
        "protocol": "state_bench_gpt54",
        "split": "test",
        "split_version": "train_test",
        "task_count": 50,
    }:
        raise ValueError("run contract differs from the qualified evaluation contract")
    if set(draft["candidates"]) != set(scoring["candidate_arms"]):
        raise ValueError("candidate arms differ from the scoring contract")
    if draft["predicted_choice"] != scoring["predicted_choice"]:
        raise ValueError("point prediction differs from the scoring contract")

    return {
        **draft,
        "status": "CANDIDATES_AND_PREDICTION_FROZEN__HELD_OUT_OUTCOMES_UNOPENED",
        "held_out_outcomes_opened": False,
        "run_contract": run_contract,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--scoring-contract", type=Path, required=True)
    parser.add_argument("--run-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    paths = {
        "draft": arguments.draft,
        "protocol": arguments.protocol,
        "scoring_contract": arguments.scoring_contract,
        "run_contract": arguments.run_contract,
    }
    payloads = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    result = freeze(
        payloads["draft"],
        payloads["protocol"],
        payloads["scoring_contract"],
        payloads["run_contract"],
    )
    result["freeze_inputs"] = {f"{name}_sha256": sha256(path) for name, path in paths.items()}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidates": len(result["candidates"]),
                "predicted_choice": result["predicted_choice"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
