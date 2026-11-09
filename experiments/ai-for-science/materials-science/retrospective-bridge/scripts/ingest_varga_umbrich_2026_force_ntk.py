#!/usr/bin/env python3
"""Reconstruct matched active-learning panels from Force-Aware NTK Table 1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SOURCE_ID = "varga_umbrich_2026_force_aware_ntk"
PAPER_PDF_SHA256 = "5dfb12e3c9dba05db026ace670883e29cdc6cb0aea106f46deb86aafa755fac8"
DATASETS = ("rgd", "t1x", "pmechdb")
METHODS = (
    "random",
    "activation",
    "committee_energy",
    "committee_force",
    "ntk_energy",
    "ntk_force",
    "ntk_energy_force",
)

# Exact values transcribed from Table 1 of arXiv:2605.13788v2. Lower is better.
TABLE_1 = {
    "rgd": {
        "energy_rmse_auc": (348.0, 326.0, 339.0, 334.0, 339.0, 338.0, 344.5),
        "force_rmse_auc": (4763.5, 4677.0, 4659.0, 4587.5, 4651.5, 4665.5, 4684.0),
        "final_energy_rmse": (13.0, 12.0, 12.0, 11.5, 12.0, 12.0, 12.0),
        "final_force_rmse": (188.5, 185.0, 186.0, 182.5, 186.0, 184.0, 186.0),
    },
    "t1x": {
        "energy_rmse_auc": (246.5, 164.0, 268.5, 250.0, 159.5, 178.5, 175.0),
        "force_rmse_auc": (2300.0, 1789.0, 2516.0, 2182.5, 1754.5, 1802.5, 1796.5),
        "final_energy_rmse": (6.5, 5.0, 5.5, 5.0, 5.0, 5.5, 5.0),
        "final_force_rmse": (62.0, 57.0, 60.0, 57.0, 57.0, 59.5, 60.5),
    },
    "pmechdb": {
        "energy_rmse_auc": (453.0, 427.0, 493.0, 457.5, 426.5, 433.5, 431.0),
        "force_rmse_auc": (2857.0, 2800.5, 2799.0, 2634.5, 2718.5, 2780.5, 2777.0),
        "final_energy_rmse": (17.0, 16.0, 19.0, 17.0, 16.0, 16.0, 16.5),
        "final_force_rmse": (113.5, 109.0, 107.0, 102.0, 106.5, 111.5, 109.5),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def measurements(method: str, metric: str) -> dict:
    is_random = method == "random"
    is_activation = method == "activation"
    is_committee = method.startswith("committee_")
    is_ntk = method.startswith("ntk_")
    uses_energy = method in {"committee_energy", "ntk_energy", "ntk_energy_force"}
    uses_force = method in {"committee_force", "ntk_force", "ntk_energy_force"}
    endpoint_is_energy = "energy" in metric
    return {
        "uses_model_relative_signal": int(not is_random),
        "uses_pretrained_representation": int(is_activation or is_ntk),
        "uses_diversity_aware_lcmd": int(is_activation or is_ntk),
        "uses_pointwise_committee_disagreement": int(is_committee),
        "uses_energy_signal": int(uses_energy),
        "uses_force_signal": int(uses_force),
        "acquisition_signal_matches_endpoint": int(
            (endpoint_is_energy and uses_energy) or (not endpoint_is_energy and uses_force)
        ),
        "forward_passes_per_candidate": 0 if is_random else (3 if is_committee else 1),
        "requires_parameter_derivatives": int(is_ntk),
        "models_maintained": 3 if is_committee else 1,
        "initial_label_count": 50,
        "labels_per_round": 150,
        "acquisition_rounds": 20,
        "maximum_label_count": 3050,
    }


def ingest(*, paper_pdf: Path | None = None) -> dict:
    if paper_pdf is not None and sha256(paper_pdf) != PAPER_PDF_SHA256:
        raise ValueError("checksum mismatch for arXiv paper PDF")

    arms = []
    for dataset in DATASETS:
        for metric, values in TABLE_1[dataset].items():
            panel_id = f"{SOURCE_ID}:{dataset}:{metric}"
            native_utilities = [-value for value in values]
            low, high = min(native_utilities), max(native_utilities)
            for method, outcome, utility in zip(METHODS, values, native_utilities, strict=True):
                normalized = 0.5 if high == low else (utility - low) / (high - low)
                arms.append(
                    {
                        "source_id": SOURCE_ID,
                        "panel_id": panel_id,
                        "dataset": dataset,
                        "metric": metric,
                        "environment": method,
                        "pre_outcome_measurements": measurements(method, metric),
                        "outcome": {
                            "reported_error": outcome,
                            "lower_is_better": True,
                            "independent_experiment_seeds": 2,
                        },
                        "derived": {
                            "native_utility": utility,
                            "panel_normalized_utility": normalized,
                            "panel_normalized_regret": 1.0 - normalized,
                        },
                    }
                )
    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "varga_umbrich_2026_force_aware_ntk_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": "arXiv:2605.13788v2",
        "panel_count": len({arm["panel_id"] for arm in arms}),
        "arm_count": len(arms),
        "primary_outcome": "energy or force RMSE area under the acquisition curve and final-round RMSE",
        "normalization": "negative error min-max normalized within dataset and metric",
        "matched_contract": {
            "fixed_test_fraction": 0.20,
            "fixed_validation_fraction": 0.10,
            "initial_label_count": 50,
            "labels_per_round": 150,
            "acquisition_rounds": 20,
            "maximum_label_count": 3050,
            "independent_experiment_seeds": 2,
        },
        "source_files": {
            "arXiv_2605.13788v2.pdf": {"sha256": PAPER_PDF_SHA256},
        },
        "interpretation_boundary": [
            "All seven acquisition arms share the downstream model, initial label count, labels per round, acquisition rounds, validation fraction, test fraction, and two-seed evaluation within each dataset.",
            "The three datasets remain separate holdout groups because each defines a distinct candidate pool and downstream task.",
            "The reported table contains two-seed means or midpoints rather than seed-level outcomes.",
            "These reactive-benchmark experiments overlap the experimental family summarized by arXiv:2605.03964, so the earlier paired round-gain panels are superseded in pooled fitting rather than double counted.",
            "The 200,000-structure OC20 experiment is excluded because exact arm-level numerical values are shown only in a figure.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(paper_pdf=args.paper_pdf)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
