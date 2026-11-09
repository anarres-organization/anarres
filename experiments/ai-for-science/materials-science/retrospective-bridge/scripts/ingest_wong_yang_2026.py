#!/usr/bin/env python3
"""Join released uMLIP outcomes with common-start pre-training measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "wong_yang_2026_umlip_bias"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reconstruct(evaluation_path: Path, measurement_path: Path) -> dict:
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
    if evaluation["source_revision"] != measurement["source_revision"]:
        raise ValueError("evaluation and measurement revisions differ")

    measured = {(arm["panel_id"], arm["environment"]): arm for arm in measurement["arms"]}
    arms = []
    for evaluated in evaluation["arms"]:
        key = (evaluated["panel_id"], evaluated["environment"])
        if key not in measured:
            raise ValueError(f"missing pre-training measurement for {key}")
        probe = measured[key]
        if evaluated["training_configuration_count"] != probe["training_configuration_count"]:
            raise ValueError(f"budget mismatch for {key}")
        arms.append(
            {
                "source_id": SOURCE_ID,
                "panel_id": evaluated["panel_id"],
                "training_configuration_count": evaluated["training_configuration_count"],
                "environment": evaluated["environment"],
                "pre_outcome_measurements": probe["measurements"],
                "outcome": evaluated["outcome"],
                "provenance": {
                    "training_dataset_relative_path": probe["dataset_relative_path"],
                    "training_dataset_sha256": probe["dataset_sha256"],
                    "fine_tuned_model_relative_path": evaluated["model_relative_path"],
                    "fine_tuned_model_sha256": evaluated["model_sha256"],
                },
            }
        )

    if len(arms) != 10 or len({arm["panel_id"] for arm in arms}) != 5:
        raise ValueError("expected five two-arm matched panels")
    for panel_id in sorted({arm["panel_id"] for arm in arms}):
        panel = [arm for arm in arms if arm["panel_id"] == panel_id]
        values = [arm["outcome"]["energy_mae_meV_per_atom"] for arm in panel]
        best, worst = min(values), max(values)
        span = worst - best
        for arm in panel:
            value = arm["outcome"]["energy_mae_meV_per_atom"]
            arm["derived"] = {
                "native_utility": -value,
                "panel_normalized_utility": 1.0 if span == 0 else (worst - value) / span,
                "panel_normalized_regret": 0.0 if span == 0 else (value - best) / span,
            }

    arms.sort(key=lambda arm: (arm["training_configuration_count"], arm["environment"]))
    return {
        "artifact": "wong_yang_2026_umlip_bias_panels_v1",
        "source_id": SOURCE_ID,
        "source_revision": evaluation["source_revision"],
        "panel_count": 5,
        "arm_count": 10,
        "primary_outcome": "independent-test energy MAE per atom",
        "normalization": (
            "within matched training-configuration budget; lower energy MAE maps to higher utility"
        ),
        "interpretation_boundary": [
            "The primary outcome follows the released independent-test energy analysis.",
            "Force errors are retained as target-specific sensitivity outcomes.",
            (
                "All pre-outcome measurements use the shared released starting potential on the "
                "exact training configurations."
            ),
        ],
        "input_artifacts": {
            "evaluation_sha256": sha256(evaluation_path),
            "measurement_sha256": sha256(measurement_path),
            "starting_model_sha256": measurement["starting_model_sha256"],
            "test_contract": evaluation["test_contract"],
        },
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = reconstruct(args.evaluation, args.measurement)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
