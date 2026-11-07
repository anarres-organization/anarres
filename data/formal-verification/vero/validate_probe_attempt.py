#!/usr/bin/env python3
"""Validate one completed Vero policy-probe attempt and its linked receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_sandbox_receipt import ReceiptError
from validate_sandbox_receipt import validate as validate_sandbox


class AttemptReceiptError(ValueError):
    """Raised when a completed probe attempt is incomplete or inconsistent."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.removeprefix("sha256:")
    return len(normalized) == 64 and all(
        character in "0123456789abcdef" for character in normalized
    )


def validate(
    attempt: dict[str, Any],
    *,
    sandbox: dict[str, Any],
    exported: dict[str, Any],
    protocol: dict[str, Any],
    controller: dict[str, Any],
    inference: dict[str, Any],
    materialization: dict[str, Any],
    paths: dict[str, Path],
) -> None:
    if attempt.get("schema_version") != "anarres.formal-verification-attempt.v1":
        raise AttemptReceiptError("unknown attempt-receipt schema")
    for field in ("attempt_id", "task_id", "started_at", "ended_at", "vibe_version"):
        if not isinstance(attempt.get(field), str) or not attempt[field]:
            raise AttemptReceiptError(f"missing attempt field: {field}")
    if attempt["started_at"] >= attempt["ended_at"]:
        raise AttemptReceiptError("attempt timestamps are not ordered")
    if "3.1.0" not in attempt["vibe_version"]:
        raise AttemptReceiptError("attempt used the wrong Vibe version")
    if attempt.get("launcher_error") is not None:
        raise AttemptReceiptError("attempt contains a launcher error")
    if attempt.get("vibe_exit_code") not in {0, 3} or attempt.get("sandbox_exit_code") != 0:
        raise AttemptReceiptError("attempt did not end as a scorable scientific run")

    expected_hashes = {
        "protocol_sha256": digest(paths["protocol"]),
        "containment_sha256": digest(paths["containment"]),
        "runtime_lock_sha256": digest(paths["runtime_lock"]),
        "controller_lock_sha256": digest(paths["controller_lock"]),
        "inference_contract_sha256": digest(paths["inference_contract"]),
        "materialization_receipt_sha256": digest(paths["materialization"]),
        "vibe_export_sha256": digest(paths["export"]),
    }
    for field, expected in expected_hashes.items():
        if attempt.get(field) != expected:
            raise AttemptReceiptError(f"attempt hash disagrees with {field}")
    for field in ("task_pre_sha256", "task_post_sha256"):
        if not is_sha256(attempt.get(field)):
            raise AttemptReceiptError(f"invalid task hash: {field}")
    if attempt["task_pre_sha256"] != materialization["task_tree_sha256"]:
        raise AttemptReceiptError("attempt did not start from the materialized task")
    if attempt["task_id"] != f"{materialization['benchmark_id']}:{materialization['mode']}":
        raise AttemptReceiptError("attempt task identity disagrees with materialization")
    if attempt["environment_keys"] != controller["environment_allowlist"]:
        raise AttemptReceiptError("attempt environment disagrees with the controller lock")
    if attempt["tool_allowlist"] != controller["tool_allowlist"]:
        raise AttemptReceiptError("attempt tools disagree with the controller lock")

    outcome = exported.get("outcome")
    if attempt.get("outcome") != outcome or outcome in {
        None,
        "usage_error",
        "config_error",
        "infrastructure_failure",
        "aborted",
    }:
        raise AttemptReceiptError("Vibe export is missing or unscorable")
    if sandbox.get("attempt_id") != attempt["attempt_id"]:
        raise AttemptReceiptError("sandbox and launcher attempt identities disagree")
    if sandbox.get("task_id") != attempt["task_id"]:
        raise AttemptReceiptError("sandbox and launcher task identities disagree")
    if sandbox.get("inference_config_digest") != expected_hashes["inference_contract_sha256"]:
        raise AttemptReceiptError("sandbox used the wrong inference contract")
    if sandbox.get("model_artifact_digest") != inference["model"]["local_artifact_digest"]:
        raise AttemptReceiptError("sandbox used the wrong model artifact")
    try:
        validate_sandbox(sandbox, protocol)
    except ReceiptError as error:
        raise AttemptReceiptError(str(error)) from error


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in (
        "attempt",
        "sandbox",
        "export",
        "protocol",
        "containment",
        "runtime-lock",
        "controller-lock",
        "inference-contract",
        "materialization",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        "protocol": args.protocol,
        "containment": args.containment,
        "runtime_lock": args.runtime_lock,
        "controller_lock": args.controller_lock,
        "inference_contract": args.inference_contract,
        "materialization": args.materialization,
        "export": args.export,
    }
    loaded = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in {
            "attempt": args.attempt,
            "sandbox": args.sandbox,
            "exported": args.export,
            "protocol": args.protocol,
            "controller": args.controller_lock,
            "inference": args.inference_contract,
            "materialization": args.materialization,
        }.items()
    }
    validate(**loaded, paths=paths)
    print("validated completed Vero policy-probe attempt")


if __name__ == "__main__":
    main()
