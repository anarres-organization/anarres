#!/usr/bin/env python3
"""Build paired method-versus-random panels from exact transfer-table values."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "varga_umbrich_2026_pretrained_acquisition"
SOURCE_BUNDLE_SHA256 = "d41e257505d9ed835d036062f3b1430d05084ac73083bba7a66631c2877522b0"
PAPER_TEX_SHA256 = "ae9aeb233f32a6b5692579c0a408135b0df8972b35effdf3ccbfbba4dbcec458"
TRANSFER_TABLE_SHA256 = "eb6accab45047eb1e0f52e135917e69a43f5bf717ad1bbcdef8eb1889d6f41ea"

DATASETS = ("pmechdb", "rgd", "t1x_mixed")
METRICS = ("energy_rmse", "force_rmse", "energy_mae", "force_mae")
ROUND_GAINS = {
    "activation_lcmd": {
        "energy_rmse": (15.0, 22.2, 77.8),
        "force_rmse": (20.0, 10.0, 44.4),
        "energy_mae": (5.0, 10.0, 61.5),
        "force_mae": (0.0, 0.0, 15.0),
    },
    "ntk_lcmd": {
        "energy_rmse": (20.0, 11.1, 83.3),
        "force_rmse": (25.0, 10.0, 50.0),
        "energy_mae": (5.0, 15.0, 61.5),
        "force_mae": (0.0, 0.0, 25.0),
    },
    "committee_energy": {
        "energy_rmse": (-23.5, 11.1, 27.8),
        "force_rmse": (25.0, 15.0, 0.0),
        "energy_mae": (-31.6, 5.0, -13.3),
        "force_mae": (-5.0, 0.0, 0.0),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def measurements(environment: str, metric: str) -> dict:
    is_random = environment == "paired_random"
    is_activation = environment == "activation_lcmd"
    is_ntk = environment == "ntk_lcmd"
    is_committee = environment == "committee_energy"
    return {
        "uses_pretrained_representation_kernel": int(is_activation or is_ntk),
        "uses_model_relative_signal": int(not is_random),
        "uses_lcmd_structural_coverage": int(is_activation or is_ntk),
        "uses_pointwise_committee_disagreement": int(is_committee),
        "acquisition_signal_matches_energy_endpoint": int(
            is_committee and metric.startswith("energy")
        ),
        "forward_passes_per_candidate": 0 if is_random else (3 if is_committee else 1),
        "backward_passes_per_candidate": int(is_ntk),
        "models_maintained": 3 if is_committee else 1,
        "initial_label_count": 50,
        "labels_per_round": 150,
        "acquisition_rounds": 20,
        "maximum_label_count": 3050,
    }


def ingest(
    *,
    paper_tex: Path | None = None,
    transfer_table: Path | None = None,
    source_bundle: Path | None = None,
) -> dict:
    checks = (
        (paper_tex, PAPER_TEX_SHA256, "paper source"),
        (transfer_table, TRANSFER_TABLE_SHA256, "transfer table"),
        (source_bundle, SOURCE_BUNDLE_SHA256, "arXiv source bundle"),
    )
    for path, expected, label in checks:
        if path is not None and sha256(path) != expected:
            raise ValueError(f"checksum mismatch for {label}")

    arms = []
    for method, metrics in ROUND_GAINS.items():
        for metric, gains in metrics.items():
            for dataset, gain in zip(DATASETS, gains, strict=True):
                panel_id = f"{SOURCE_ID}:{method}:{dataset}:{metric}"
                panel = []
                for environment, utility in ((method, gain), ("paired_random", 0.0)):
                    panel.append(
                        {
                            "source_id": SOURCE_ID,
                            "panel_id": panel_id,
                            "dataset": dataset,
                            "metric": metric,
                            "comparison_method": method,
                            "environment": environment,
                            "pre_outcome_measurements": measurements(environment, metric),
                            "outcome": {
                                "round_gain_percent_vs_paired_random": utility,
                                "independent_experiment_seeds": 2,
                            },
                        }
                    )
                utilities = [arm["outcome"]["round_gain_percent_vs_paired_random"] for arm in panel]
                low, high = min(utilities), max(utilities)
                for arm, utility in zip(panel, utilities, strict=True):
                    normalized = 0.5 if high == low else (utility - low) / (high - low)
                    arm["derived"] = {
                        "native_utility": utility,
                        "panel_normalized_utility": normalized,
                        "panel_normalized_regret": 1.0 - normalized,
                    }
                arms.extend(panel)
    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "varga_umbrich_2026_transfer_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": "arXiv:2605.03964v2",
        "panel_count": len({arm["panel_id"] for arm in arms}),
        "arm_count": len(arms),
        "primary_outcome": "percentage reduction in rounds to a method-specific shared target",
        "normalization": "round gain min-max normalized within method, dataset, and metric",
        "matched_contract": {
            "fixed_test_fraction": 0.20,
            "fixed_validation_fraction": 0.10,
            "initial_label_count": 50,
            "labels_per_round": 150,
            "acquisition_rounds": 20,
            "independent_experiment_seeds": 2,
        },
        "source_files": {
            "arXiv_source_bundle": {"sha256": SOURCE_BUNDLE_SHA256},
            "arxiv_version.tex": {"sha256": PAPER_TEX_SHA256},
            "icml/icml_tables/transferability.tex": {"sha256": TRANSFER_TABLE_SHA256},
        },
        "interpretation_boundary": [
            "Each method is compared only with its paired random curve because the "
            "shared target used to compute round gain is method-specific.",
            "Activation, NTK, and committee gains therefore define separate binary "
            "decisions and are never treated as directly comparable utilities.",
            "The aggregate T1x table is excluded because it averages three candidate "
            "pools and leaves no independent material or dataset holdout group.",
            "Exact round gains come from the manuscript table; underlying per-round "
            "numerical histories and seed-level outcomes were not released.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-tex", type=Path)
    parser.add_argument("--transfer-table", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(
        paper_tex=args.paper_tex,
        transfer_table=args.transfer_table,
        source_bundle=args.source_bundle,
    )
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
