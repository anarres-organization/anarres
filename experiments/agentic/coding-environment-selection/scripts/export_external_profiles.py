#!/usr/bin/env python3
"""Export AutoEnvScaling design metadata into environment-profile inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "data" / "external-forecast-panels.json"
DEFINITION = (
    "https://github.com/anarres-organization/anarres/blob/main/experiments/agentic/"
    "coding-environment-selection/README.md#source-separated-external-check"
)


def coordinate(name: str, value: bool, estimator: str, role: str) -> dict[str, object]:
    return {
        "name": name,
        "definition": {"uri": DEFINITION, "revision": "v1"},
        "role": role,
        "value": float(value),
        "unit": "indicator",
        "direction": "higher",
        "estimator": estimator,
        "sample_count": 1,
    }


def profile(panel: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    autoenv = panel["source_id"] == "auto_env_scaling"
    source = {
        "uri": (
            "https://github.com/MSR-Orchard/AutoEnvScaling"
            if autoenv
            else "https://arxiv.org/abs/2609.04128"
        ),
        "revision": "arXiv:2610.14163v1" if autoenv else "arXiv:2609.04128v1",
        "license": "Apache-2.0" if autoenv else "CC-BY-4.0",
    }
    coordinates = [
        coordinate(
            "policy_aligned_progression",
            candidate["policy_aligned_progression"],
            "source-native environment-process contract",
            "target_affinity",
        )
    ]
    if autoenv:
        coordinates.extend(
            [
                coordinate(
                    "validated_and_current_policy_calibrated",
                    candidate["validated_and_current_policy_calibrated"],
                    "source-reported validation and solver-calibration protocol",
                    "reliability",
                ),
                coordinate(
                    "solver_trajectory_feedback",
                    candidate["solver_trajectory_feedback"],
                    "source-reported access to current-solver trajectories and failures",
                    "target_affinity",
                ),
            ]
        )
    else:
        coordinates.extend(
            [
                coordinate(
                    "verified_progressive_lineage",
                    candidate["verified_progressive_lineage"],
                    "source-reported oracle, no-op, rubric, and lineage contract",
                    "coverage",
                ),
                coordinate(
                    "policy_response_scheduler",
                    candidate["policy_response_scheduler"],
                    "source-reported reward-threshold lineage scheduler",
                    "signal",
                ),
            ]
        )
    return {
        "schema_version": "anarres.environment-profile-input.v1",
        "environment_id": f"{panel['panel_id']}::{candidate['id']}",
        "domain": "agentic-terminal-coding",
        "subject": {"kind": "policy", "id": panel["solver"], "revision": "source-reported"},
        "producer": {
            "kind": "study-exporter",
            "id": "anarres-agentic-coding-external-check",
            "revision": "v1",
        },
        "source": source,
        "measurement_contract": {
            "kind": "source-native-design-audit",
            "id": "agentic-coding-policy-aligned-progression-v1",
            "revision": "v1",
            "repetitions": 1,
            "cost_unit": "matched_training_steps",
        },
        "qualification_checks": [
            {
                "check_id": "matched-training-contract",
                "category": "measurement",
                "status": "pass",
                "severity": "error",
                "summary": panel["matched_contract"] + ".",
            },
            {
                "check_id": "training-outcomes-excluded",
                "category": "source",
                "status": "pass",
                "severity": "error",
                "summary": (
                    "The exported profile contains design metadata and no trained-policy score."
                ),
            },
        ],
        "coordinates": coordinates,
        "attributes": {
            "panel_id": panel["panel_id"],
            "candidate_id": candidate["id"],
            "proposer": panel["proposer"],
            "chronology": "retrospective_source_separated_external_check",
        },
    }


def export(output: Path) -> list[Path]:
    data = json.loads(PANELS.read_text())
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for panel in data["panels"]:
        for candidate in panel["candidates"]:
            filename = f"{panel['panel_id']}-{candidate['id'].replace('_', '-')}.profile-input.json"
            path = output / filename
            path.write_text(json.dumps(profile(panel, candidate), indent=2, sort_keys=True) + "\n")
            paths.append(path)
    return paths


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: export_external_profiles.py OUTPUT_DIRECTORY")
    for path in export(Path(sys.argv[1])):
        print(path)


if __name__ == "__main__":
    main()
