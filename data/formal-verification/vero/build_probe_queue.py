#!/usr/bin/env python3
"""Build the frozen, outcome-blind Vero policy-probe queue."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class QueueError(ValueError):
    """Raised when the queue inputs or an existing queue are inconsistent."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordering_key(queue_id: str, benchmark_id: str, mode: str, replicate: int) -> str:
    identity = f"{queue_id}\0{benchmark_id}\0{mode}\0{replicate}"
    return hashlib.sha256(identity.encode()).hexdigest()


def build_queue(
    protocol: dict[str, Any], panel: dict[str, Any], *, protocol_sha256: str, panel_sha256: str
) -> dict[str, Any]:
    design = protocol["probe_design"]
    repositories = panel["repositories"]
    if design["repositories"] != len(repositories):
        raise QueueError("protocol and panel repository counts disagree")
    queue_id = f"{protocol['protocol_id']}-queue"
    namespace = design.get("attempt_namespace")
    entries = []
    for repository in repositories:
        for mode in design["modes"]:
            for replicate in range(1, design["independent_attempts_per_repository_mode"] + 1):
                benchmark_id = repository["benchmark_id"]
                parts = [benchmark_id, mode]
                if namespace:
                    parts.append(namespace)
                attempt_id = "-".join(parts) + f"-r{replicate:02d}"
                token_field = (
                    "controller_token_stop_threshold_per_attempt"
                    if "controller_token_stop_threshold_per_attempt" in design
                    else "maximum_cumulative_model_tokens_per_attempt"
                )
                entries.append(
                    {
                        "attempt_id": attempt_id,
                        "benchmark_id": benchmark_id,
                        "source_language": repository["source_language"],
                        "mode": mode,
                        "replicate": replicate,
                        "task_id": f"{benchmark_id}:{mode}",
                        "expected_specifications": repository["specifications"],
                        (
                            "controller_token_stop_threshold"
                            if token_field == "controller_token_stop_threshold_per_attempt"
                            else "maximum_model_tokens"
                        ): design[token_field],
                        "maximum_wall_seconds": design["maximum_wall_seconds_per_attempt"],
                        "maximum_agent_turns": design["maximum_agent_turns_per_attempt"],
                        "ordering_key": ordering_key(queue_id, benchmark_id, mode, replicate),
                    }
                )
    entries.sort(key=lambda record: record["ordering_key"])
    for position, record in enumerate(entries, start=1):
        record["queue_position"] = position
    if len(entries) != design["total_attempts"]:
        raise QueueError("generated queue length disagrees with the protocol")
    return {
        "schema_version": "anarres.formal-verification-probe-queue.v1",
        "queue_id": queue_id,
        "status": "frozen_before_model_attempts",
        "ordering": "ascending SHA-256 of queue ID, benchmark ID, mode, and replicate",
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha256,
        "panel_sha256": panel_sha256,
        "attempts": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_queue(
        json.loads(args.protocol.read_text(encoding="utf-8")),
        json.loads(args.panel.read_text(encoding="utf-8")),
        protocol_sha256=digest(args.protocol),
        panel_sha256=digest(args.panel),
    )
    rendered = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise QueueError("frozen queue does not match its inputs")
        print("validated frozen Vero policy-probe queue")
        return
    if args.output.exists():
        raise QueueError("--output already exists; use --check to validate it")
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {len(expected['attempts'])} frozen attempts to {args.output}")


if __name__ == "__main__":
    main()
