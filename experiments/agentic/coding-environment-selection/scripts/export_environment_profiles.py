#!/usr/bin/env python3
"""Export agentic-coding candidates into the shared environment-profile input."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "data" / "panels.json"
DEFINITION = "https://github.com/anarres-organization/anarres/blob/main/experiments/agentic/coding-environment-selection/README.md#representation"


def coordinate(
    name: str, role: str, value: float, unit: str, direction: str, estimator: str, count: int
) -> dict[str, object]:
    return {
        "name": name,
        "definition": {"uri": DEFINITION, "revision": "v1"},
        "role": role,
        "value": value,
        "unit": unit,
        "direction": direction,
        "estimator": estimator,
        "sample_count": count,
    }


def profile(panel: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    tmax = panel["panel_id"] == "tmax_public_pool_comparison"
    count = 128 if tmax else 16
    source_uri = (
        "https://github.com/hamishivi/tmax" if tmax else "https://github.com/Zhiyuan-Zeng/RLVE"
    )
    source_revision = "arxiv:2606.23321v1" if tmax else "b2dd0b6f726ee2ebc8e2c0fb2af0796414f18cb2"
    source_license = "Apache-2.0" if tmax else "MIT"
    subject_id = "Qwen/Qwen3.5-9B" if tmax else "Nemotron-Research-Reasoning-Qwen-1.5B-v2"
    subject_revision = (
        "c202236235762e1c871ad0ccb60c8ee5ba337b9a"
        if tmax
        else "a8e647c7a46f04e84ce732d6fa3fa627ba343b8d"
    )
    measurement_id = (
        "tmax-common-reference-bridge-v1" if tmax else "rlve-prospective-mixture-probe-v1"
    )
    qualification = (
        "Common reference-policy records are complete for the candidate pool."
        if tmax
        else "The candidate mixture and starting-policy measurement were frozen before outcomes."
    )
    coordinates = [
        coordinate(
            "readiness",
            "reliability",
            candidate["readiness"],
            "normalized_score",
            "contextual",
            panel["feature_contract"]["readiness"],
            count,
        ),
        coordinate(
            "reward_information",
            "signal",
            candidate["reward_information"],
            "entropy_nats",
            "higher",
            panel["feature_contract"]["reward_information"],
            count,
        ),
        coordinate(
            "mean_log_output_tokens",
            "cost",
            candidate["cost"],
            "log_tokens_per_attempt",
            "lower",
            panel["feature_contract"]["cost"],
            count,
        ),
        coordinate(
            "target_affinity",
            "target_affinity",
            candidate["target_affinity"],
            "normalized_score",
            "higher",
            panel["feature_contract"]["target_affinity"],
            count,
        ),
    ]
    if "truncation_rate" in candidate:
        coordinates.append(
            coordinate(
                "truncation_rate",
                "reliability",
                candidate["truncation_rate"],
                "fraction",
                "lower",
                "fraction of common-reference attempts truncated",
                count,
            )
        )
    return {
        "schema_version": "anarres.environment-profile-input.v1",
        "environment_id": f"{panel['panel_id']}::{candidate['id']}",
        "domain": "agentic-terminal-coding",
        "subject": {"kind": "policy", "id": subject_id, "revision": subject_revision},
        "producer": {
            "kind": "study-exporter",
            "id": "anarres-agentic-coding-public-panels",
            "revision": "v1",
        },
        "source": {"uri": source_uri, "revision": source_revision, "license": source_license},
        "measurement_contract": {
            "kind": "policy-response-probe",
            "id": measurement_id,
            "revision": "v1",
            "repetitions": 4 if tmax else 1,
            "cost_unit": "generated_output_tokens",
        },
        "qualification_checks": [
            {
                "check_id": "measurement-records-complete",
                "category": "measurement",
                "status": "pass",
                "severity": "error",
                "summary": qualification,
            },
            {
                "check_id": "training-outcomes-excluded",
                "category": "source",
                "status": "pass",
                "severity": "error",
                "summary": "The profile contains no trained-policy outcome.",
            },
        ],
        "coordinates": coordinates,
        "attributes": {
            "panel_id": panel["panel_id"],
            "candidate_id": candidate["id"],
            "chronology": panel["chronology"],
        },
    }


def export(output: Path) -> list[Path]:
    data = json.loads(PANELS.read_text())
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for panel in data["panels"]:
        prefix = "tmax" if panel["panel_id"].startswith("tmax") else "rlve"
        for candidate in panel["candidates"]:
            path = output / f"{prefix}-{candidate['id'].replace('_', '-')}.profile-input.json"
            path.write_text(json.dumps(profile(panel, candidate), indent=2, sort_keys=True) + "\n")
            paths.append(path)
    return paths


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: export_environment_profiles.py OUTPUT_DIRECTORY")
    for path in export(Path(sys.argv[1])):
        print(path)


if __name__ == "__main__":
    main()
