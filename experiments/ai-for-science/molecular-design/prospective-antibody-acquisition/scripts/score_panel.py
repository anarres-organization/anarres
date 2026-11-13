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


def mean(values: list[float]) -> float:
    return float(np.mean(values))


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
        key = (unit["identity"]["assay"], unit["identity"]["strategy"])
        grouped[key].append(unit)

    strategy_rows: list[dict[str, object]] = []
    assay_metrics: list[dict[str, object]] = []
    selected = contract["prediction"]["selected_strategy"]
    for assay in contract["candidate_assays"]:
        utilities: dict[str, float] = {}
        endpoints: dict[str, float] = {}
        for strategy in sorted(contract["strategies"]):
            units = grouped[(assay, strategy)]
            utilities[strategy] = mean(
                [float(unit["outcome"]["normalized_curve_auc"]) for unit in units]
            )
            endpoints[strategy] = mean(
                [float(unit["outcome"]["endpoint_recall"]) for unit in units]
            )
            strategy_rows.append(
                {
                    "assay": assay,
                    "strategy": strategy,
                    "mean_curve_auc": utilities[strategy],
                    "mean_endpoint_recall": endpoints[strategy],
                    "seed_curve_auc": {
                        str(unit["identity"]["seed"]): unit["outcome"]["normalized_curve_auc"]
                        for unit in sorted(units, key=lambda item: item["identity"]["seed"])
                    },
                }
            )
        best = max(utilities.values())
        worst = min(utilities.values())
        tolerance = 1e-12
        winners = [name for name, value in utilities.items() if abs(value - best) <= tolerance]
        normalized_regret = 0.0 if best == worst else (best - utilities[selected]) / (best - worst)
        pairwise_credit = sum(
            1.0 if utilities[selected] > value else 0.5 if utilities[selected] == value else 0.0
            for name, value in utilities.items()
            if name != selected
        ) / (len(utilities) - 1)
        assay_metrics.append(
            {
                "assay": assay,
                "best_strategies": sorted(winners),
                "selected_strategy": selected,
                "selected_is_best_credit": 1.0 / len(winners) if selected in winners else 0.0,
                "selected_pairwise_credit": pairwise_credit,
                "selected_normalized_regret": normalized_regret,
            }
        )

    point = {
        "mean_normalized_regret": mean(
            [row["selected_normalized_regret"] for row in assay_metrics]
        ),
        "mean_pairwise_credit": mean([row["selected_pairwise_credit"] for row in assay_metrics]),
        "mean_best_strategy_credit": mean(
            [row["selected_is_best_credit"] for row in assay_metrics]
        ),
    }
    rng = np.random.default_rng(20261112)
    bootstrap: dict[str, list[float]] = {key: [] for key in point}
    for _ in range(20_000):
        sample = rng.integers(0, len(assay_metrics), size=len(assay_metrics))
        rows = [assay_metrics[index] for index in sample]
        bootstrap["mean_normalized_regret"].append(
            mean([row["selected_normalized_regret"] for row in rows])
        )
        bootstrap["mean_pairwise_credit"].append(
            mean([row["selected_pairwise_credit"] for row in rows])
        )
        bootstrap["mean_best_strategy_credit"].append(
            mean([row["selected_is_best_credit"] for row in rows])
        )
    intervals = {
        key: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
        for key, values in bootstrap.items()
    }
    return {
        "schema_version": 1,
        "study_id": contract["study_id"],
        "status": "SCORED_AFTER_COMPLETE_RELEASE_GATE",
        "prediction": contract["prediction"],
        "support": {
            "assays": len(contract["candidate_assays"]),
            "strategies": len(contract["strategies"]),
            "seeds": len(contract["seeds"]),
            "units": gate["unit_count"],
        },
        "primary_result": point,
        "whole_assay_bootstrap_95_intervals": intervals,
        "assay_results": assay_metrics,
        "strategy_curves": strategy_rows,
        "release_gate_sha256": sha256_path(release_gate_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--release-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(args.unit_dir, args.release_gate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(args.output)


if __name__ == "__main__":
    main()
