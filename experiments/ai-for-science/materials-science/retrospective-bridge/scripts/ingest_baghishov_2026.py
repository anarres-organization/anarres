#!/usr/bin/env python3
"""Reconstruct matched leverage-sampling panels from Baghishov et al."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

REVISION = "b982ccd33e981eab2f6527d56b407f9297b1cfb1"
BUDGETS = (100, 200, 350, 500, 750, 1000, 1500, 2250, 3000)
EXPECTED_SHA256 = {
    100: "173f8d38b920517839ba74982cde81dd5ebad46b4b9ebe36b277810dfc3e5337",
    200: "c3a97322fb39f04e2d0b5953c047b2d1fcd7fae165c40c4db5e72ecc6b69937c",
    350: "2619af9cb4e4052353096a6efed01eb4e3e11202171c43927159fd89a61ed1f8",
    500: "196e4566a21f477f66d513e80b204f7c99e4851fd90bc9cc8d1fa984caeaea8d",
    750: "96144dc436073052c5782c9ef12913a9656003062a36ea5912c5deddf36bec4f",
    1000: "38744087a5cd15efb45b07086718e96fe63a228f7f697e69d7815f478e2a128b",
    1500: "a3d3473872d19635d7bbce8cf802f3ff6e751c0b9d1ae49c92933bfba2b09cdc",
    2250: "7b9009e5cab008fa2a7f716318b90690bdfcefb689a022977e505a933e93d5d6",
    3000: "64906d74c841db08a524ef3b88215633fa6071b5f5c607b89d3c53e7beb009db",
}
METHOD_COORDINATES = {
    "Random": {
        "uses_descriptor_coverage": 0,
        "uses_energy_leverage": 0,
        "uses_force_block_leverage": 0,
    },
    "Leverage": {
        "uses_descriptor_coverage": 1,
        "uses_energy_leverage": 1,
        "uses_force_block_leverage": 0,
    },
    "Block Leverage": {
        "uses_descriptor_coverage": 1,
        "uses_energy_leverage": 0,
        "uses_force_block_leverage": 1,
    },
}
ENDPOINTS = {
    "testing_energy_rmse": "Testing Energy RMSE",
    "testing_force_rmse": "Testing Force RMSE",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(arms: list[dict]) -> None:
    utilities = [-arm["outcome"]["mean_rmse"] for arm in arms]
    low, high = min(utilities), max(utilities)
    span = high - low
    for arm, native in zip(arms, utilities, strict=False):
        normalized = 0.5 if np.isclose(span, 0.0) else (native - low) / span
        arm["derived"] = {
            "native_utility": native,
            "panel_normalized_utility": float(normalized),
            "panel_normalized_regret": float(1.0 - normalized),
        }


def ingest(repository: Path) -> dict:
    source = repository / "data" / "sampling_methods_comparison"
    output_arms = []
    source_files = {}
    for budget in BUDGETS:
        path = source / str(budget) / "results.csv"
        digest = sha256(path)
        if digest != EXPECTED_SHA256[budget]:
            raise ValueError(f"checksum mismatch for budget {budget}: {digest}")
        source_files[str(budget)] = {
            "relative_path": str(path.relative_to(repository)),
            "sha256": digest,
        }
        grouped: dict[str, list[dict]] = defaultdict(list)
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                grouped[row["Sampling Method"]].append(row)
        if set(grouped) != set(METHOD_COORDINATES):
            raise ValueError(f"unexpected methods at budget {budget}: {sorted(grouped)}")
        if any(len(rows) != 50 for rows in grouped.values()):
            raise ValueError(f"expected 50 realizations per method at budget {budget}")

        for endpoint, column in ENDPOINTS.items():
            panel = []
            for method, rows in grouped.items():
                values = np.asarray([float(row[column]) for row in rows])
                panel.append(
                    {
                        "source_id": "baghishov_2026_application_specific_mlip",
                        "panel_id": (
                            f"baghishov_2026_application_specific_mlip:budget_{budget}:{endpoint}"
                        ),
                        "training_configuration_count": budget,
                        "endpoint": endpoint,
                        "sampling_method": method,
                        "pre_outcome_measurements": {
                            **METHOD_COORDINATES[method],
                            "training_configuration_count": budget,
                            "training_pool_fraction": budget / 10000.0,
                        },
                        "outcome": {
                            "mean_rmse": float(values.mean()),
                            "rmse_standard_deviation": float(values.std(ddof=1)),
                            "released_realizations": len(values),
                        },
                    }
                )
            normalize(panel)
            output_arms.extend(panel)
    return {
        "artifact": "baghishov_2026_leverage_sampling_panels_v1",
        "source_id": "baghishov_2026_application_specific_mlip",
        "source_revision": REVISION,
        "panel_count": len(BUDGETS) * len(ENDPOINTS),
        "arm_count": len(output_arms),
        "primary_outcome": (
            "mean testing RMSE across 50 released realizations, evaluated separately for "
            "energy and forces"
        ),
        "normalization": "negative RMSE, min-max normalized within budget and endpoint",
        "matched_contract": {
            "candidate_pool_size": 10000,
            "qSNAP_2Jmax": 10,
            "DFT_precision_level": 6,
            "energy_to_force_weight": 150,
        },
        "source_files": source_files,
        "interpretation_boundary": [
            "Energy and force endpoints are repeated views of the same sampling decisions.",
            "The released files contain 50 realizations per method and budget.",
            (
                "Leverage scores use descriptor matrices and do not require DFT labels for the "
                "selected configurations."
            ),
        ],
        "arms": output_arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "data"
        / "baghishov_2026_leverage_panels.json",
    )
    args = parser.parse_args()
    result = ingest(args.repository)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": result["panel_count"], "arms": result["arm_count"]}))


if __name__ == "__main__":
    main()
