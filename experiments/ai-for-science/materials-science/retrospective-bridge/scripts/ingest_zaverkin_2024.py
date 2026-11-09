#!/usr/bin/env python3
"""Build matched active-learning panels from Zaverkin et al. (2024)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


SOURCE_ID = "zaverkin_2024_uncertainty_biased_md"

# Exact means and standard deviations from Tables 1 and 2.  The main active-
# learning experiments use a maximum dataset size of 512 configurations.
ALANINE = {
    "random_300K": {"temperature_K": 300, "coverage": (0.58, 0.03), "energy": (34.09, 6.29), "force": (0.191, 0.019), "selection": 0, "bias": 0, "hydrogen_bias": 0},
    "random_600K": {"temperature_K": 600, "coverage": (0.76, 0.04), "energy": (31.44, 4.77), "force": (0.143, 0.015), "selection": 0, "bias": 0, "hydrogen_bias": 0},
    "random_1200K": {"temperature_K": 1200, "coverage": (0.95, 0.01), "energy": (19.83, 4.62), "force": (0.116, 0.017), "selection": 0, "bias": 0, "hydrogen_bias": 0},
    "uncertainty_300K": {"temperature_K": 300, "coverage": (0.58, 0.03), "energy": (30.29, 5.47), "force": (0.149, 0.019), "selection": 1, "bias": 0, "hydrogen_bias": 0},
    "uncertainty_600K": {"temperature_K": 600, "coverage": (0.89, 0.00), "energy": (26.03, 2.23), "force": (0.116, 0.012), "selection": 1, "bias": 0, "hydrogen_bias": 0},
    "uncertainty_1200K": {"temperature_K": 1200, "coverage": (0.97, 0.01), "energy": (1.47, 0.09), "force": (0.055, 0.002), "selection": 1, "bias": 0, "hydrogen_bias": 0},
    "uncertainty_biased_300K_with_H": {"temperature_K": 300, "coverage": (0.87, 0.02), "energy": (5.09, 5.40), "force": (0.082, 0.016), "selection": 1, "bias": 1, "hydrogen_bias": 1},
    "uncertainty_biased_300K_without_H": {"temperature_K": 300, "coverage": (0.94, 0.01), "energy": (1.97, 0.88), "force": (0.071, 0.003), "selection": 1, "bias": 1, "hydrogen_bias": 0},
}

MIL53 = {
    600: {
        "random_0MPa": {"pressure_MPa": 0, "selection": 0, "bias": 0, "energy": (1.62, 0.52), "force": (0.062, 0.002), "stress": (145.3, 35.49)},
        "random_250MPa": {"pressure_MPa": 250, "selection": 0, "bias": 0, "energy": (0.84, 0.09), "force": (0.057, 0.001), "stress": (63.8, 15.82)},
        "uncertainty_0MPa": {"pressure_MPa": 0, "selection": 1, "bias": 0, "energy": (1.17, 0.36), "force": (0.058, 0.002), "stress": (90.81, 32.82)},
        "uncertainty_250MPa": {"pressure_MPa": 250, "selection": 1, "bias": 0, "energy": (0.57, 0.05), "force": (0.052, 0.001), "stress": (42.72, 1.37)},
        "uncertainty_biased_0MPa": {"pressure_MPa": 0, "selection": 1, "bias": 1, "energy": (0.57, 0.08), "force": (0.051, 0.001), "stress": (36.60, 1.46)},
    },
    300: {
        "random_0MPa": {"pressure_MPa": 0, "selection": 0, "bias": 0, "energy": (1.04, 0.26), "force": (0.058, 0.001), "stress": (70.49, 6.61)},
        "random_250MPa": {"pressure_MPa": 250, "selection": 0, "bias": 0, "energy": (0.58, 0.08), "force": (0.055, 0.002), "stress": (52.19, 2.22)},
        "uncertainty_0MPa": {"pressure_MPa": 0, "selection": 1, "bias": 0, "energy": (0.88, 0.20), "force": (0.056, 0.001), "stress": (58.57, 5.94)},
        "uncertainty_250MPa": {"pressure_MPa": 250, "selection": 1, "bias": 0, "energy": (0.48, 0.01), "force": (0.054, 0.000), "stress": (39.88, 1.76)},
        "uncertainty_biased_0MPa": {"pressure_MPa": 0, "selection": 1, "bias": 1, "energy": (0.49, 0.09), "force": (0.052, 0.001), "stress": (33.89, 3.06)},
    },
}


def _base_measurements(*, temperature: int, selection: int, bias: int, coverage: float | None) -> dict:
    target_temperature = 1200 if coverage is not None else 600
    return {
        "uses_uncertainty_selection": selection,
        "uses_uncertainty_bias": bias,
        "adaptive_acquisition": int(bool(selection or bias)),
        "generation_temperature_K": temperature,
        "temperature_gap_to_test_K": abs(temperature - target_temperature),
        "structural_coverage": coverage,
        "training_configuration_count": 512,
    }


def reconstruct() -> dict:
    by_panel: dict[str, list[dict]] = defaultdict(list)
    for environment, values in ALANINE.items():
        coverage, coverage_sd = values["coverage"]
        measurements = _base_measurements(
            temperature=values["temperature_K"],
            selection=values["selection"],
            bias=values["bias"],
            coverage=coverage,
        ) | {"coverage_sd": coverage_sd, "uses_hydrogen_bias": values["hydrogen_bias"]}
        for endpoint, unit in (("energy", "meV_per_atom"), ("force", "eV_per_angstrom")):
            mean, sd = values[endpoint]
            panel_id = f"{SOURCE_ID}:alanine_1200K_test:{endpoint}_rmse"
            by_panel[panel_id].append({
                "source_id": SOURCE_ID,
                "panel_id": panel_id,
                "system": "alanine_dipeptide",
                "evaluation_distribution": "1200K_MD",
                "environment": environment,
                "endpoint": f"{endpoint}_rmse_{unit}",
                "pre_outcome_measurements": measurements,
                "outcome": {"mean_rmse": mean, "sd_across_runs": sd, "independent_runs": 5},
            })

    for temperature, environments in MIL53.items():
        for environment, values in environments.items():
            measurements = _base_measurements(
                temperature=temperature,
                selection=values["selection"],
                bias=values["bias"],
                coverage=None,
            ) | {"generation_pressure_MPa": values["pressure_MPa"]}
            for endpoint, unit in (("energy", "meV_per_atom"), ("force", "eV_per_angstrom"), ("stress", "MPa")):
                mean, sd = values[endpoint]
                panel_id = f"{SOURCE_ID}:mil53_generation_{temperature}K_600K_test:{endpoint}_rmse"
                by_panel[panel_id].append({
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "system": "MIL-53(Al)",
                    "evaluation_distribution": "600K_first_principles_MD",
                    "environment": environment,
                    "endpoint": f"{endpoint}_rmse_{unit}",
                    "pre_outcome_measurements": measurements,
                    "outcome": {"mean_rmse": mean, "sd_across_runs": sd, "independent_runs": 3},
                })

    arms = []
    for panel_arms in by_panel.values():
        errors = [arm["outcome"]["mean_rmse"] for arm in panel_arms]
        best, worst = min(errors), max(errors)
        span = worst - best
        for arm in panel_arms:
            error = arm["outcome"]["mean_rmse"]
            arm["derived"] = {
                "native_utility": -error,
                "panel_normalized_utility": 1.0 if span == 0 else (worst - error) / span,
                "panel_normalized_regret": 0.0 if span == 0 else (error - best) / span,
            }
            arms.append(arm)
    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "zaverkin_2024_uncertainty_biased_md_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(by_panel),
        "arm_count": len(arms),
        "primary_outcome": "mean terminal RMSE from primary-paper Tables 1 and 2",
        "normalization": "negative RMSE, min-max normalized within physical system, acquisition-temperature context, and endpoint",
        "matched_contract": {
            "maximum_training_and_validation_configurations": 512,
            "alanine_independent_runs": 5,
            "mil53_independent_runs": 3,
        },
        "source_archive": {
            "doi": "10.5281/zenodo.10776838",
            "license": "CC-BY-NC-4.0",
            "files": {
                "ala2-ffs.zip": {"bytes": 146129485, "md5": "c9d5bc06e12b0923457635f9323dc07d"},
                "mil53.zip": {"bytes": 559281684, "md5": "306b7344c15a4f211b9b8d2784416081"},
            },
        },
        "interpretation_boundary": [
            "These are adaptive environment-generation experiments, so acquisition and uncertainty-measurement cost is separate from the matched 512-configuration final training budget.",
            "The 500-configuration metadynamics baseline is excluded from the matched panels.",
            "Alanine coverage is measured directly in collective-variable space; the paper does not report the same scalar coverage coordinate for MIL-53(Al).",
        ],
        "arms": arms,
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
