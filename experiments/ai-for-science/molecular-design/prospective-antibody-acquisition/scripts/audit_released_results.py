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
    by_assay: dict[str, dict[str, float]] = defaultdict(dict)
    for row in results["strategy_curves"]:
        by_assay[row["assay"]][row["strategy"]] = row["mean_curve_auc"]

    strategy_metrics: dict[str, dict[str, float]] = {}
    for strategy in sorted(next(iter(by_assay.values()))):
        regrets: list[float] = []
        best_credits: list[float] = []
        pairwise_credits: list[float] = []
        utilities: list[float] = []
        for assay_values in by_assay.values():
            utility = assay_values[strategy]
            best = max(assay_values.values())
            worst = min(assay_values.values())
            winners = [name for name, value in assay_values.items() if value == best]
            regrets.append(0.0 if best == worst else (best - utility) / (best - worst))
            best_credits.append(1.0 / len(winners) if strategy in winners else 0.0)
            pairwise_credits.append(
                sum(
                    1.0 if utility > value else 0.5 if utility == value else 0.0
                    for name, value in assay_values.items()
                    if name != strategy
                )
                / (len(assay_values) - 1)
            )
            utilities.append(utility)
        strategy_metrics[strategy] = {
            "mean_curve_auc": float(np.mean(utilities)),
            "mean_normalized_regret": float(np.mean(regrets)),
            "mean_pairwise_credit": float(np.mean(pairwise_credits)),
            "mean_best_strategy_credit": float(np.mean(best_credits)),
        }

    ucb_minus_greedy = [values["ucb"] - values["greedy"] for values in by_assay.values()]
    ucb_minus_random = [values["ucb"] - values["random"] for values in by_assay.values()]
    rng = np.random.default_rng(20261112)
    boot = []
    for _ in range(20_000):
        indices = rng.integers(0, len(ucb_minus_greedy), size=len(ucb_minus_greedy))
        boot.append(float(np.mean([ucb_minus_greedy[index] for index in indices])))
    return {
        "schema_version": 1,
        "study_id": results["study_id"],
        "status": "POST_RELEASE_FIXED_STRATEGY_AUDIT",
        "results_sha256": sha256_path(results_path),
        "strategy_metrics": strategy_metrics,
        "frozen_ucb_contrasts": {
            "ucb_minus_greedy_by_assay": dict(zip(by_assay, ucb_minus_greedy, strict=True)),
            "mean_ucb_minus_greedy_curve_auc": float(np.mean(ucb_minus_greedy)),
            "mean_ucb_minus_greedy_95_interval": [
                float(np.quantile(boot, 0.025)),
                float(np.quantile(boot, 0.975)),
            ],
            "ucb_minus_random_by_assay": dict(zip(by_assay, ucb_minus_random, strict=True)),
            "assays_where_ucb_exceeds_random": sum(value > 0 for value in ucb_minus_random),
        },
        "interpretation": (
            "The frozen UCB rule is best on three of six assays, exceeds random on all six, "
            "and has the highest mean raw curve utility. Greedy is best on the other three "
            "assays and has lower normalized allocation regret. The panel supports a competitive "
            "UCB prediction while leaving UCB-versus-greedy selection unresolved."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.results)
    args.output.write_bytes(canonical_json_bytes(result))
    print(args.output)


if __name__ == "__main__":
    main()
