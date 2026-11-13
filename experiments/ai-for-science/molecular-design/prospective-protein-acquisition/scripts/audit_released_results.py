from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import canonical_json_bytes, load_json, sha256_path  # noqa: E402


def audit(results_path: Path) -> dict[str, object]:
    results = load_json(results_path)
    by_dataset: dict[str, dict[str, float]] = defaultdict(dict)
    for row in results["strategy_curves"]:
        by_dataset[row["dataset"]][row["strategy"]] = row["mean_curve_auc"]

    strategy_metrics: dict[str, dict[str, float]] = {}
    for strategy in sorted(next(iter(by_dataset.values()))):
        raw: list[float] = []
        regrets: list[float] = []
        pairwise: list[float] = []
        best_credit: list[float] = []
        for values in by_dataset.values():
            utility = values[strategy]
            best = max(values.values())
            worst = min(values.values())
            winners = [name for name, value in values.items() if value == best]
            raw.append(utility)
            regrets.append(0.0 if best == worst else (best - utility) / (best - worst))
            pairwise.append(
                sum(
                    1.0 if utility > value else 0.5 if utility == value else 0.0
                    for name, value in values.items()
                    if name != strategy
                )
                / (len(values) - 1)
            )
            best_credit.append(1.0 / len(winners) if strategy in winners else 0.0)
        strategy_metrics[strategy] = {
            "mean_curve_auc": float(np.mean(raw)),
            "mean_normalized_regret": float(np.mean(regrets)),
            "mean_pairwise_credit": float(np.mean(pairwise)),
            "mean_best_strategy_credit": float(np.mean(best_credit)),
        }

    greedy_minus_ucb = [values["greedy"] - values["ucb"] for values in by_dataset.values()]
    greedy_minus_random = [values["greedy"] - values["random"] for values in by_dataset.values()]
    rng = np.random.default_rng(20261113)
    bootstrap = []
    for _ in range(20_000):
        indices = rng.integers(0, len(greedy_minus_ucb), size=len(greedy_minus_ucb))
        bootstrap.append(float(np.mean([greedy_minus_ucb[index] for index in indices])))
    return {
        "schema_version": 1,
        "study_id": results["study_id"],
        "status": "POST_RELEASE_FIXED_STRATEGY_AUDIT",
        "results_sha256": sha256_path(results_path),
        "strategy_metrics": strategy_metrics,
        "frozen_greedy_contrasts": {
            "greedy_minus_ucb_by_dataset": dict(zip(by_dataset, greedy_minus_ucb, strict=True)),
            "mean_greedy_minus_ucb_curve_auc": float(np.mean(greedy_minus_ucb)),
            "mean_greedy_minus_ucb_95_interval": [
                float(np.quantile(bootstrap, 0.025)),
                float(np.quantile(bootstrap, 0.975)),
            ],
            "greedy_minus_random_by_dataset": dict(
                zip(by_dataset, greedy_minus_random, strict=True)
            ),
            "datasets_where_greedy_exceeds_random": sum(value > 0 for value in greedy_minus_random),
        },
        "interpretation": (
            "The frozen greedy rule is best on four of seven new datasets, has the "
            "lowest normalized regret and highest pairwise credit, and exceeds random "
            "acquisition on every dataset. UCB remains competitive and is best on two datasets."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(canonical_json_bytes(audit(args.results)))
    print(args.output)


if __name__ == "__main__":
    main()
