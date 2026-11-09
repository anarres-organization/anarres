#!/usr/bin/env python3
"""Reconstruct the published UDD and MD active-learning cross-test matrix."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

SOURCE_ID = "kulichenko_2023_udd"
ENVIRONMENTS = {
    "md350": {
        "temperature_K": 350,
        "uses_uncertainty_bias": 0,
        "high_energy_region_count": 105,
    },
    "udd350": {
        "temperature_K": 350,
        "uses_uncertainty_bias": 1,
        "high_energy_region_count": 289,
    },
    "md600": {
        "temperature_K": 600,
        "uses_uncertainty_bias": 0,
        "high_energy_region_count": 290,
    },
    "md1000": {
        "temperature_K": 1000,
        "uses_uncertainty_bias": 0,
        "high_energy_region_count": 394,
    },
}

# Supplementary Table 2. Rows are held-out test environments and columns are
# training environments. Values are energy RMSE in kcal/mol.
RMSE = {
    "md350": {"md350": 0.25, "udd350": 0.34, "md600": 0.41, "md1000": 0.37},
    "udd350": {"md350": 4.78, "udd350": 0.65, "md600": 0.92, "md1000": 0.73},
    "md600": {"md350": 4.43, "udd350": 0.57, "md600": 0.62, "md1000": 0.67},
    "md1000": {"md350": 9.93, "udd350": 1.28, "md600": 2.72, "md1000": 0.87},
}


def reconstruct() -> dict:
    arms = []
    for target, outcomes in RMSE.items():
        target_coordinates = ENVIRONMENTS[target]
        for training_environment, rmse in outcomes.items():
            source_coordinates = ENVIRONMENTS[training_environment]
            arms.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": f"{SOURCE_ID}:glycine:test_{target}",
                    "molecule": "glycine",
                    "target_environment": target,
                    "training_environment": training_environment,
                    "training_configuration_count": 1040,
                    "pre_outcome_measurements": source_coordinates
                    | {
                        "temperature_gap_to_target_K": abs(
                            source_coordinates["temperature_K"]
                            - target_coordinates["temperature_K"]
                        ),
                        "uncertainty_bias_matches_target": int(
                            source_coordinates["uses_uncertainty_bias"]
                            == target_coordinates["uses_uncertainty_bias"]
                        ),
                        "high_energy_count_gap_to_target": abs(
                            source_coordinates["high_energy_region_count"]
                            - target_coordinates["high_energy_region_count"]
                        ),
                    },
                    "outcome": {"energy_rmse_kcal_per_mol": rmse},
                    "replication": {
                        "independent_environment_runs": 3,
                        "training_run_count": 1,
                        "heldout_runs_combined": 2,
                    },
                    "provenance": {
                        "outcome_source": "Supplementary Table 2",
                        "coverage_source": "main-text Figure 2 analysis",
                    },
                }
            )

    panels: dict[str, list[dict]] = defaultdict(list)
    for arm in arms:
        panels[arm["panel_id"]].append(arm)
    for panel_arms in panels.values():
        values = [arm["outcome"]["energy_rmse_kcal_per_mol"] for arm in panel_arms]
        best, worst = min(values), max(values)
        span = worst - best
        for arm in panel_arms:
            value = arm["outcome"]["energy_rmse_kcal_per_mol"]
            arm["derived"] = {
                "native_utility": -value,
                "panel_normalized_utility": 1.0 if span == 0 else (worst - value) / span,
                "panel_normalized_regret": 0.0 if span == 0 else (value - best) / span,
            }

    ordered = sorted(arms, key=lambda arm: (arm["panel_id"], arm["training_environment"]))
    return {
        "artifact": "kulichenko_2023_udd_cross_test_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(panels),
        "arm_count": len(ordered),
        "primary_outcome": "energy_rmse_kcal_per_mol",
        "matched_contract": {
            "training_configuration_count": 1040,
            "molecule": "glycine",
            "training_runs_per_environment": 1,
            "heldout_runs_per_target_environment": 2,
        },
        "normalization": "within held-out target environment; lower RMSE maps to higher utility",
        "arms": ordered,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = reconstruct()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
