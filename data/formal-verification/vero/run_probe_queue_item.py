#!/usr/bin/env python3
"""Execute, validate, and grade one frozen Vero queue entry."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class QueueItemError(RuntimeError):
    """Raised when a queue item cannot run without violating the frozen contract."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QueueItemError(f"expected an object in {path.name}")
    return value


def select_entry(queue: dict[str, Any], attempt_id: str) -> dict[str, Any]:
    matches = [record for record in queue["attempts"] if record["attempt_id"] == attempt_id]
    if len(matches) != 1:
        raise QueueItemError("attempt ID is absent or duplicated in the frozen queue")
    return matches[0]


def validate_queue_contract(
    queue: dict[str, Any], *, protocol_path: Path, panel_path: Path
) -> None:
    if queue.get("status") != "frozen_before_model_attempts":
        raise QueueItemError("queue is not frozen")
    if queue.get("protocol_sha256") != digest(protocol_path):
        raise QueueItemError("queue disagrees with the probe protocol")
    if queue.get("panel_sha256") != digest(panel_path):
        raise QueueItemError("queue disagrees with the development panel")


def run_stage(name: str, command: list[str], root: Path) -> dict[str, Any]:
    log_path = root / f"{name}.log"
    started = datetime.now(UTC).isoformat()
    with log_path.open("wb") as log:
        result = subprocess.run(command, check=False, stdout=log, stderr=subprocess.STDOUT)
    return {
        "stage": name,
        "started_at": started,
        "ended_at": datetime.now(UTC).isoformat(),
        "return_code": result.returncode,
        "log": log_path.name,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-pin", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--containment", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    parser.add_argument("--inference-contract", type=Path, required=True)
    parser.add_argument("--vibe", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--sandbox-server", type=Path, required=True)
    parser.add_argument("--materializer", type=Path, required=True)
    parser.add_argument("--attempt-runner", type=Path, required=True)
    parser.add_argument("--attempt-validator", type=Path, required=True)
    parser.add_argument("--grader", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    required = (
        args.queue,
        args.source,
        args.source_pin,
        args.split,
        args.panel,
        args.protocol,
        args.containment,
        args.runtime_lock,
        args.controller_lock,
        args.inference_contract,
        args.vibe,
        args.sandbox_server,
        args.materializer,
        args.attempt_runner,
        args.attempt_validator,
        args.grader,
    )
    for path in required:
        if not path.exists():
            raise QueueItemError(f"required path does not exist: {path}")
    work_root = args.work_root.resolve(strict=True)
    output_root = args.output_root.resolve(strict=True)
    queue = read_object(args.queue)
    validate_queue_contract(queue, protocol_path=args.protocol, panel_path=args.panel)
    entry = select_entry(queue, args.attempt_id)

    root = output_root / args.attempt_id
    if root.exists():
        raise QueueItemError(
            "attempt output already exists; scientific attempts are not overwritten"
        )
    root.mkdir(mode=0o700)
    task = root / "task"
    materialization = root / "materialization-receipt.json"
    attempt_output = root / "attempt"
    grade_output = root / "grade"
    receipt_path = root / "queue-item-receipt.json"
    receipt: dict[str, Any] = {
        "schema_version": "anarres.formal-verification-queue-item.v1",
        "queue_id": queue["queue_id"],
        "queue_sha256": digest(args.queue),
        "attempt_id": entry["attempt_id"],
        "queue_position": entry["queue_position"],
        "task_id": entry["task_id"],
        "status": "running",
        "stages": [],
    }

    commands = [
        (
            "materialize",
            [
                sys.executable,
                str(args.materializer),
                "--source",
                str(args.source),
                "--pin",
                str(args.source_pin),
                "--split",
                str(args.split),
                "--panel",
                str(args.panel),
                "--benchmark-id",
                entry["benchmark_id"],
                "--mode",
                entry["mode"],
                "--output",
                str(task),
                "--receipt",
                str(materialization),
            ],
        ),
        (
            "attempt",
            [
                sys.executable,
                str(args.attempt_runner),
                "--attempt-id",
                entry["attempt_id"],
                "--task",
                str(task),
                "--materialization-receipt",
                str(materialization),
                "--output",
                str(attempt_output),
                "--work-root",
                str(work_root),
                "--vibe",
                str(args.vibe),
                "--image",
                args.image,
                "--docker",
                args.docker,
                "--protocol",
                str(args.protocol),
                "--containment",
                str(args.containment),
                "--runtime-lock",
                str(args.runtime_lock),
                "--controller-lock",
                str(args.controller_lock),
                "--inference-contract",
                str(args.inference_contract),
                "--sandbox-server",
                str(args.sandbox_server),
            ],
        ),
        (
            "validate",
            [
                sys.executable,
                str(args.attempt_validator),
                "--attempt",
                str(attempt_output / "attempt-receipt.json"),
                "--sandbox",
                str(attempt_output / "sandbox-receipt.json"),
                "--export",
                str(attempt_output / "vibe-output" / "export.json"),
                "--protocol",
                str(args.protocol),
                "--containment",
                str(args.containment),
                "--runtime-lock",
                str(args.runtime_lock),
                "--controller-lock",
                str(args.controller_lock),
                "--inference-contract",
                str(args.inference_contract),
                "--materialization",
                str(materialization),
            ],
        ),
        (
            "grade",
            [
                sys.executable,
                str(args.grader),
                "--source",
                str(args.source),
                "--source-pin",
                str(args.source_pin),
                "--panel",
                str(args.panel),
                "--split",
                str(args.split),
                "--benchmark-id",
                entry["benchmark_id"],
                "--mode",
                entry["mode"],
                "--task",
                str(task),
                "--attempt-receipt",
                str(attempt_output / "attempt-receipt.json"),
                "--sandbox-receipt",
                str(attempt_output / "sandbox-receipt.json"),
                "--vibe-export",
                str(attempt_output / "vibe-output" / "export.json"),
                "--output",
                str(grade_output),
            ],
        ),
    ]
    try:
        for name, command in commands:
            stage = run_stage(name, command, root)
            receipt["stages"].append(stage)
            if stage["return_code"] != 0:
                receipt["status"] = "failed_unclassified"
                raise QueueItemError(f"{name} failed; inspect {stage['log']}")
        receipt["status"] = "graded"
        receipt["grade_receipt_sha256"] = digest(grade_output / "grade-receipt.json")
    finally:
        receipt["ended_at"] = datetime.now(UTC).isoformat()
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
