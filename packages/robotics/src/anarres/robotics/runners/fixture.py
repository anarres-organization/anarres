"""Deterministic fixture policy runner.

Run it as `python -m anarres.robotics.runners.fixture`. It needs no simulator
or accelerator. Success is a pure function of the policy revision, task, and
seed. Any initial state whose identity begins with `broken-` produces a reset
failure, so tests can check that infrastructure failures stay separate from
scientific outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from anarres.core import sha256_digest

SIMULATION_STEP_SECONDS = 0.05


def attempt(request: dict, task: dict, sample_index: int, seed: int) -> dict:
    row = {
        "schema_version": "anarres.robotics-probe-attempt.v1",
        "task_id": task["task_id"],
        "initial_state_id": task["initial_state_id"],
        "sample_index": sample_index,
        "seed": seed,
    }
    if task["initial_state_id"].startswith("broken-"):
        return {
            **row,
            "success": None,
            "termination": None,
            "control_steps": 0,
            "simulated_seconds": 0.0,
            "wall_clock_seconds": 0.0,
            "infrastructure_status": "reset_failed",
        }
    key = f"{request['policy']['revision']}|{task['task_id']}|{seed}".encode()
    draw = hashlib.sha256(key).digest()
    max_steps = request["limits"]["max_steps"]
    success = draw[0] < 160
    steps = 1 + draw[1] % max_steps if success else max_steps
    return {
        **row,
        "success": success,
        "termination": "success" if success else "truncated",
        "control_steps": steps,
        "simulated_seconds": round(steps * SIMULATION_STEP_SECONDS, 6),
        "wall_clock_seconds": 0.0,
        "infrastructure_status": "valid",
    }


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anarres-policy-runner-protocol", type=int, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(arguments)
    if args.anarres_policy_runner_protocol != 1:
        parser.error("unsupported policy-runner protocol")
    request = json.loads(args.request.read_text(encoding="utf-8"))
    rows = [
        attempt(request, task, index, seed)
        for task in request["tasks"]
        for index, seed in enumerate(task["seeds"])
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    result = {
        "schema_version": "anarres.robotics-policy-runner-result.v1",
        "request_sha256": sha256_digest(request),
        "runner": {"name": "anarres-robotics-fixture-runner", "version": "1.0.0"},
        "artifacts": [],
    }
    (args.output / "runner-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
