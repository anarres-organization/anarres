"""Adapter side of the external policy-runner protocol.

Anarres never imports a policy framework. It writes a request, and only an
explicit execution launches the runner executable that the user installed.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from anarres.core import EnvironmentSource, sha256_digest

from ..contract import RoboticsContractError, SourceDescription, require_text, validate_attempt
from ..drivers.base import SourceDriver

PROTOCOL_VERSION = 1
LIMIT_FIELDS = {"max_steps", "wall_clock_seconds"}


def build_request(
    source: EnvironmentSource,
    description: SourceDescription,
    driver: SourceDriver,
    *,
    policy: str,
    policy_revision: str,
    limits: dict[str, int],
) -> dict[str, Any]:
    if set(limits) != LIMIT_FIELDS or any(
        not isinstance(value, int) or value <= 0 for value in limits.values()
    ):
        raise RoboticsContractError(f"limits must be positive integers for {sorted(LIMIT_FIELDS)}")
    return {
        "schema_version": "anarres.robotics-policy-runner-request.v1",
        "protocol_version": PROTOCOL_VERSION,
        "policy": {
            "id": require_text(policy, "policy"),
            "revision": require_text(policy_revision, "policy_revision"),
        },
        "source": {
            "environment_id": source.environment_id,
            "revision": source.revision,
            "content_digest": description.content_digest,
        },
        "driver": {"native_format": driver.native_format, "version": driver.version},
        "evaluation_contract_digest": description.evaluation_contract_digest,
        "tasks": driver.tasks(source),
        "limits": dict(sorted(limits.items())),
    }


def ordered_attempts(request: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"task_id": task["task_id"], "sample_index": index, "seed": seed}
        for task in request["tasks"]
        for index, seed in enumerate(task["seeds"])
    ]


def _write_once(path: Path, value: dict[str, Any]) -> None:
    if path.is_file():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise RoboticsContractError(
                f"{path.name} already contains a different immutable record"
            )
        return
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def plan(request: dict[str, Any], output: Path) -> dict[str, Any]:
    """Write the request and the ordered execution plan. Launches nothing."""

    output.mkdir(parents=True, exist_ok=True)
    attempts = ordered_attempts(request)
    record = {
        "schema_version": "anarres.robotics-probe-plan.v1",
        "request_sha256": sha256_digest(request),
        "attempts": attempts,
    }
    record["plan_sha256"] = sha256_digest(record)
    _write_once(output / "request.json", request)
    _write_once(output / "plan.json", record)
    return {
        "status": "planned",
        "plan": str(output / "plan.json"),
        "plan_sha256": record["plan_sha256"],
        "attempts": len(attempts),
        "runner_launched": False,
    }


def execute(runner: list[str], output: Path) -> dict[str, Any]:
    """Launch the runner on a planned request and check its attempts without scoring them."""

    request_path = output / "request.json"
    plan_record = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if sha256_digest(request) != plan_record["request_sha256"]:
        raise RoboticsContractError("request.json changed after planning")
    try:
        process = subprocess.run(
            [
                *runner,
                "--anarres-policy-runner-protocol",
                str(PROTOCOL_VERSION),
                "--request",
                str(request_path),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=request["limits"]["wall_clock_seconds"],
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "runner_failed",
            "infrastructure_status": "timeout",
            "wall_clock_seconds": request["limits"]["wall_clock_seconds"],
        }
    if process.returncode != 0:
        return {
            "status": "runner_failed",
            "infrastructure_status": "runtime_error",
            "returncode": process.returncode,
            "stderr_tail": process.stderr[-2000:],
        }
    result = read_runner_result(output / "runner-result.json")
    if result["request_sha256"] != plan_record["request_sha256"]:
        raise RoboticsContractError("runner result is bound to a different request")
    rows = read_attempts(output / "attempts.jsonl")
    expected = {
        (item["task_id"], item["sample_index"], item["seed"]) for item in plan_record["attempts"]
    }
    observed = {(row["task_id"], row["sample_index"], row["seed"]) for row in rows}
    if len(observed) != len(rows):
        raise RoboticsContractError("runner produced duplicate attempts")
    if observed - expected:
        raise RoboticsContractError("runner produced attempts outside the plan")
    statuses = Counter(row["infrastructure_status"] for row in rows)
    return {
        "status": "complete" if observed == expected else "incomplete",
        "planned_attempts": len(expected),
        "received_attempts": len(rows),
        "infrastructure_statuses": dict(sorted(statuses.items())),
        "runner": result["runner"],
        "outcomes_scored": False,
    }


def read_runner_result(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RoboticsContractError("runner exited without writing runner-result.json")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("schema_version") != "anarres.robotics-policy-runner-result.v1":
        raise RoboticsContractError("unsupported policy-runner result schema")
    runner = result.get("runner")
    if not isinstance(runner, dict):
        raise RoboticsContractError("runner result must identify the runner")
    require_text(runner.get("name"), "runner.name")
    require_text(runner.get("version"), "runner.version")
    return result


def read_attempts(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            validate_attempt(row)
        except RoboticsContractError as error:
            raise RoboticsContractError(f"attempts.jsonl line {number}: {error}") from error
        rows.append(row)
    return rows
