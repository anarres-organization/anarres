"""Small reference CLI for environment processing."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from anarres.core import sha256_digest

from .metrics import GroupMeasurement, compute_coordinates
from .qualification import Qualification, qualify_group


def build_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    groups = payload.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("probe input must contain a non-empty groups list")

    processed: list[dict[str, Any]] = []
    measurements: list[GroupMeasurement] = []
    status_counts: Counter[str] = Counter()

    for raw in groups:
        task_id = str(raw["task_id"])
        result = qualify_group(
            oracle_passed=bool(raw["oracle_passed"]),
            noop_passed=bool(raw["noop_passed"]),
            infrastructure_valid=bool(raw["infrastructure_valid"]),
            rewards=tuple(float(value) for value in raw.get("rewards", [])),
        )
        status_counts[result.status.value] += 1
        processed.append(
            {"task_id": task_id, "status": result.status.value, "reason": result.reason}
        )

        if result.status in {Qualification.ADMITTED, Qualification.RESERVE}:
            measurements.append(
                GroupMeasurement(
                    task_id=task_id,
                    admitted_advantage_mass=float(raw.get("admitted_advantage_mass", 0.0)),
                    generated_action_tokens=int(raw["generated_action_tokens"]),
                )
            )

    if not measurements:
        raise ValueError("probe produced no scientifically valid groups")

    coordinates = compute_coordinates(measurements)
    manifest: dict[str, Any] = {
        "schema_version": "anarres.environment-manifest.v1",
        "environment_id": str(payload["environment_id"]),
        "policy_id": str(payload["policy_id"]),
        "policy_revision": str(payload["policy_revision"]),
        "source_license": str(payload["source_license"]),
        "source_revision": str(payload["source_revision"]),
        "source_uri": str(payload["source_uri"]),
        "probe_contract": payload["probe_contract"],
        "status_counts": dict(sorted(status_counts.items())),
        "coordinates": asdict(coordinates),
        "groups": processed,
        "input_digest": sha256_digest(payload),
    }
    manifest["manifest_digest"] = sha256_digest(manifest)
    return manifest


def probe(input_path: Path, output_path: Path) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    manifest = build_manifest(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="anarres-env")
    commands = root.add_subparsers(dest="command", required=True)
    probe_command = commands.add_parser("probe", help="Process a frozen policy-probe result")
    probe_command.add_argument("input", type=Path)
    probe_command.add_argument("--output", required=True, type=Path)
    return root


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "probe":
        probe(arguments.input, arguments.output)


if __name__ == "__main__":
    main()
