#!/usr/bin/env python3
"""Reconstruct matched random-subset uncertainty panels from Svahn et al."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

SOURCE_ID = "svahn_2026_cluster_mlip_limits"
TARGETS = {
    "EC": {
        "temperature_K": 313,
        "density": 1.312,
        "diffusion": 8.0,
        "mass_kg": 1.462303889780969e-23,
        "viscosity_Pa_s": 1.93e-3,
    },
    "EMC": {
        "temperature_K": 298,
        "density": 1.006,
        "diffusion": 18.3,
        "mass_kg": 1.1582317925845882e-23,
        "viscosity_Pa_s": 0.65e-3,
    },
}
KB = 1.380649e-23
XI = 2.837298


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_size_correction(row: dict[str, str]) -> float:
    composition = row["Composition"]
    target = TARGETS[composition]
    density_kg_m3 = float(row["Density /g*cm-3"]) * 1000.0
    box_length_m = (target["mass_kg"] / density_kg_m3) ** (1.0 / 3.0)
    correction_m2_s = (
        XI
        * KB
        * target["temperature_K"]
        / (6.0 * math.pi * target["viscosity_Pa_s"] * box_length_m)
    )
    return correction_m2_s * 1e10


def normalize(arms: list[dict]) -> None:
    utilities = [arm["derived"]["native_utility"] for arm in arms]
    low, high = min(utilities), max(utilities)
    for arm in arms:
        value = arm["derived"]["native_utility"]
        arm["derived"]["panel_normalized_utility"] = (
            0.5 if high == low else (value - low) / (high - low)
        )


def reconstruct(source_csv: Path) -> dict:
    with source_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = [
        row
        for row in rows
        if row["Data set"] in {"Clusters-Small", "Clusters-Medium"}
        and row["Labels"] == "wB97X-D3"
        and int(row["Seed ID"]) == 1
        and int(row["Sample ID"]) in {1, 2, 3}
        and row["Composition"] in TARGETS
    ]
    panels: dict[str, list[dict]] = {}
    for row in selected:
        dataset = row["Data set"]
        composition = row["Composition"]
        sample = int(row["Sample ID"])
        density = float(row["Density /g*cm-3"])
        corrected_diffusion = float(row["Diff. coeff. /1e6 cm2*s-1"]) + finite_size_correction(row)
        for endpoint, observed in (
            ("density_g_cm3", density),
            ("diffusion_1e-6_cm2_s", corrected_diffusion),
        ):
            target_key = "density" if endpoint.startswith("density") else "diffusion"
            target = TARGETS[composition][target_key]
            panel_id = f"{SOURCE_ID}:{dataset}:{composition}:{endpoint}"
            arm = {
                "source_id": SOURCE_ID,
                "panel_id": panel_id,
                "data_budget": dataset,
                "composition": composition,
                "endpoint": endpoint,
                "candidate": f"random_subset_{sample}",
                "pre_outcome_measurements": {
                    "same_structure_count_within_panel": 1,
                    "same_molecular_composition_within_panel": 1,
                    "distinguishing_measurement_available": 0,
                },
                "outcome": {
                    "observed": observed,
                    "experimental_target": target,
                    "absolute_error": abs(observed - target),
                    "model_seed": 1,
                },
                "derived": {"native_utility": -abs(observed - target)},
            }
            panels.setdefault(panel_id, []).append(arm)
    assert len(panels) == 8
    assert all(len(arms) == 3 for arms in panels.values())
    for arms in panels.values():
        normalize(arms)
    arms = [arm for panel_id in sorted(panels) for arm in panels[panel_id]]
    return {
        "artifact": "svahn_2026_random_subset_uncertainty_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(panels),
        "arm_count": len(arms),
        "role": "uncertainty audit; excluded from predictive fitting",
        "normalization": (
            "within data budget, pure-solvent composition, and physical endpoint; "
            "lower absolute error from the reported experimental target maps to higher utility"
        ),
        "source_artifact": {
            "repository": "https://github.com/viktorsvahn/Limits_of_cluster_MLIPs",
            "repository_revision": "f7275efdd4955cbb6231a5711c9f4e4f130cce27",
            "source_pickle": "part2_results.pkl",
            "restricted_csv_sha256": sha256(source_csv),
        },
        "interpretation_boundary": [
            (
                "The three arms at each budget use different random cluster identities but the "
                "same molecular composition."
            ),
            (
                "No released pre-training measurement distinguishes the arms, so these panels "
                "estimate unresolved selection variability rather than predictor accuracy."
            ),
            (
                "The diffusion endpoint applies the finite-size correction used in the released "
                "analysis notebook."
            ),
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_csv", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = reconstruct(args.source_csv)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("panel_count", "arm_count")}, indent=2))


if __name__ == "__main__":
    main()
