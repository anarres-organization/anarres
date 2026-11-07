#!/usr/bin/env python3
"""Validate one completed Vero agent-socket runtime receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class ReceiptError(ValueError):
    """Raised when a runtime receipt is incomplete or inconsistent."""


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def validate(receipt: dict[str, Any], protocol: dict[str, Any]) -> None:
    for field in ("attempt_id", "task_id", "started_at", "ended_at"):
        if not isinstance(receipt.get(field), str) or not receipt[field]:
            raise ReceiptError(f"missing receipt field: {field}")
    if receipt["started_at"] >= receipt["ended_at"]:
        raise ReceiptError("receipt timestamps are not ordered")

    if "@sha256:" not in receipt["image_reference"] and not receipt["image_reference"].startswith(
        "sha256:"
    ):
        raise ReceiptError("runtime image is not identified by an immutable digest")
    for field in (
        "model_artifact_digest",
        "inference_config_digest",
        "workspace_pre_sha256",
        "workspace_post_sha256",
        "image_id",
    ):
        if not is_sha256(receipt.get(field)):
            raise ReceiptError(f"invalid SHA-256 receipt field: {field}")

    if not receipt.get("container_runtime_version"):
        raise ReceiptError("container runtime version is missing")
    if not receipt.get("container_removed"):
        raise ReceiptError("attempt container was not removed")
    if receipt.get("infrastructure_errors"):
        raise ReceiptError("attempt contains an infrastructure error")

    limits = receipt.get("resource_limits")
    if not isinstance(limits, dict):
        raise ReceiptError("resource limits are missing")
    for field in (
        "cpus",
        "pids",
        "maximum_command_seconds",
        "maximum_output_bytes",
        "maximum_file_bytes",
    ):
        if not isinstance(limits.get(field), int | float) or limits[field] <= 0:
            raise ReceiptError(f"invalid resource limit: {field}")
    if (
        limits["maximum_command_seconds"]
        > protocol["probe_design"]["maximum_wall_seconds_per_attempt"]
    ):
        raise ReceiptError("one command can exceed the complete attempt wall-time limit")
    if not isinstance(limits.get("memory"), str) or not limits["memory"]:
        raise ReceiptError("memory limit is missing")

    methods = receipt.get("methods")
    if not isinstance(methods, dict):
        raise ReceiptError("agent-socket method counts are missing")
    if methods.get("agent/initialize") != 1:
        raise ReceiptError("receipt must contain exactly one agent initialization")
    if methods.get("sandbox/execute", 0) < 1:
        raise ReceiptError("receipt contains no model-facing sandbox execution")
    if set(methods) - {"agent/initialize", "sandbox/execute", "sandbox/readFile"}:
        raise ReceiptError("receipt contains an undeclared agent-socket method")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    validate(
        json.loads(args.receipt.read_text(encoding="utf-8")),
        json.loads(args.protocol.read_text(encoding="utf-8")),
    )
    print("validated completed Vero agent-socket runtime receipt")


if __name__ == "__main__":
    main()
