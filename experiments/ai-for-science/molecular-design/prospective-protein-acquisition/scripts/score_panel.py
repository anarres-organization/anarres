from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CONTRACT_PATH,
    canonical_json_bytes,
    contract_hashes,
    load_json,
    sha256_path,
)


def score(unit_dir: Path, release_gate_path: Path) -> dict[str, object]:
    contract = load_json(CONTRACT_PATH)
    gate = load_json(release_gate_path)
    if gate["status"] != "RELEASE_GATE_PASSED__OUTCOMES_MAY_BE_OPENED":
        raise ValueError("release gate has not passed")
    if gate["contract_hashes"] != contract_hashes():
        raise ValueError("release-gate contract mismatch")

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in gate["records"]:
        path = unit_dir / record["filename"]
        if sha256_path(path) != record["sha256"]:
            raise ValueError(f"unit changed after release gate: {path}")
        unit = load_json(path)
        grouped[(unit["identity"]["dataset"], unit["identity"]["strategy"])].append(unit)

    selected = contract["prediction"]["selected_strategy"]
    curves: list[dict[str, object]] = []
    dataset_results: list[dict[str, object]] = []
    for dataset in contract["candidate_datasets"]:
        utilities: dict[str, float] = {}
        for strategy in sorted(contract["strategies"]):
            units = grouped[(dataset, strategy)]
            utilities[strategy] = float(
                np.mean([unit["outcome"]["normalized_curve_auc"] for unit in units])
            )
            curves.append(
                {
                    "dataset": dataset,
                    "strategy": strategy,
                    "mean_curve_auc": utilities[strategy],
                    "mean_endpoint_recall": float(
                        np.mean([unit["outcome"]["endpoint_recall"] for unit in units])
                    ),
                    "seed_curve_auc": {
                        str(unit["identity"]["seed"]): unit["outcome"]["normalized_curve_auc"]
                        for unit in sorted(units, key=lambda item: item["identity"]["seed"])
                    },
                }
            )
        best = max(utilities.values())
        worst = min(utilities.values())
        winners = [name for name, value in utilities.items() if value == best]
        dataset_results.append(
            {
                "dataset": dataset,
                "best_strategies": sorted(winners),
                "selected_strategy": selected,
                "selected_is_best_credit": 1.0 / len(winners) if selected in winners else 0.0,
                "selected_pairwise_credit": sum(
                    1.0
                    if utilities[selected] > value
                    else 0.5
                    if utilities[selected] == value
                    else 0.0
                    for name, value in utilities.items()
                    if name != selected
                )
                / (len(utilities) - 1),
                "selected_normalized_regret": (
                    0.0 if best == worst else (best - utilities[selected]) / (best - worst)
                ),
            }
        )

    primary = {
        "mean_normalized_regret": float(
            np.mean([row["selected_normalized_regret"] for row in dataset_results])
        ),
        "mean_pairwise_credit": float(
            np.mean([row["selected_pairwise_credit"] for row in dataset_results])
        ),
        "mean_best_strategy_credit": float(
            np.mean([row["selected_is_best_credit"] for row in dataset_results])
        ),
    }
    rng = np.random.default_rng(20261113)
    bootstrap = {name: [] for name in primary}
    for _ in range(20_000):
        indices = rng.integers(0, len(dataset_results), size=len(dataset_results))
        rows = [dataset_results[index] for index in indices]
        bootstrap["mean_normalized_regret"].append(
            float(np.mean([row["selected_normalized_regret"] for row in rows]))
        )
        bootstrap["mean_pairwise_credit"].append(
            float(np.mean([row["selected_pairwise_credit"] for row in rows]))
        )
        bootstrap["mean_best_strategy_credit"].append(
            float(np.mean([row["selected_is_best_credit"] for row in rows]))
        )
    return {
        "schema_version": 1,
        "study_id": contract["study_id"],
        "status": "SCORED_AFTER_COMPLETE_RELEASE_GATE",
        "prediction": contract["prediction"],
        "support": {
            "datasets": len(contract["candidate_datasets"]),
            "strategies": len(contract["strategies"]),
            "seeds": len(contract["seeds"]),
            "units": gate["unit_count"],
        },
        "primary_result": primary,
        "whole_dataset_bootstrap_95_intervals": {
            name: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
            for name, values in bootstrap.items()
        },
        "dataset_results": dataset_results,
        "strategy_curves": curves,
        "release_gate_sha256": sha256_path(release_gate_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--release-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(args.unit_dir, args.release_gate)
    args.output.write_bytes(canonical_json_bytes(result))
    print(args.output)


if __name__ == "__main__":
    main()
