"""Two laws for team-level rollouts: grouping cannot buy signal, selection inflates it.

The first law is negative. For a group of G rollouts drawn uniformly at success
rate p, expected advantage mass is 2Gp(1 - p) exactly, so mass per rollout is
2p(1 - p) for every G. Filtering out groups whose rollouts all agree, a common
implementation habit, removes mass only in proportion to the coverage it also
removes, so the mass per token falls to 2p(1 - p) times the coverage.

The second law prices screening. Choose the best of K environments at a fixed
budget and the winner's reported density is biased upward even when every
environment is identical. The bias has an exact expression, and the corrected
report needs a two-regime rule because a blind correction erases real champions.

All quantities below are exact or fixed-seed, and every script path asserts on
drift.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import binom

TRIALS = 400
BASELINE = 0.035
ALPHA = 0.05


def phi(p: float) -> float:
    return p * (1.0 - p)


def advantage_mass(k: int, group_size: int) -> float:
    return 2.0 * k * (group_size - k) / (group_size - 1)


def grouping_law(p: float, group_size: int) -> dict[str, float]:
    """Per-token mass, the exact ceiling, and what group filtering costs."""

    counts = np.arange(group_size + 1)
    weights = binom.pmf(counts, group_size, p)
    mass = np.array([advantage_mass(int(k), group_size) for k in counts])
    expected = float((weights * mass).sum())
    coverage = 1.0 - p**group_size - (1.0 - p) ** group_size
    return {
        "per_rollout": expected / group_size,
        "ceiling": 2.0 * p * (1.0 - p),
        "coverage": coverage,
        "filtered_per_token": expected / group_size * coverage,
    }


def _sorted_density(trials: int) -> tuple[np.ndarray, np.ndarray]:
    counts = np.arange(trials + 1)
    values = (counts / trials) * (1.0 - counts / trials)
    order = np.argsort(values)
    return values[order], order


def expected_max(p: float, candidates: int, trials: int = TRIALS) -> float:
    """Exact expectation of the largest density estimate among K identical arms."""

    values, order = _sorted_density(trials)
    cdf = np.cumsum(binom.pmf(np.arange(trials + 1), trials, p)[order])
    previous = np.concatenate(([0.0], cdf[:-1]))
    return float(np.sum(values * (cdf**candidates - previous**candidates)))


def invert_max(observed: float, candidates: int, trials: int = TRIALS) -> float:
    """Density whose expected panel maximum equals the observed winner."""

    low, high = 1e-4, 0.2
    for _ in range(34):
        middle = (low + high) / 2.0
        if expected_max(middle, candidates, trials) > observed:
            high = middle
        else:
            low = middle
    return (low + high) / 2.0


def winner_p_value(counts: np.ndarray, trials: int = TRIALS) -> float:
    """Exact tail probability of seeing this large a winner under homogeneity."""

    values, order = _sorted_density(trials)
    pooled = float(counts.sum()) / (trials * len(counts))
    winner = int(np.argmax((counts / trials) * (1.0 - counts / trials)))
    observed = (counts[winner] / trials) * (1.0 - counts[winner] / trials)
    tail_mass = float(
        np.sum(binom.pmf(np.arange(trials + 1), trials, pooled)[order][values <= observed])
    )
    return float(1.0 - tail_mass ** len(counts))


def report(
    counts: np.ndarray, trials: int = TRIALS, alpha: float = ALPHA
) -> dict[str, float | str]:
    """Two-regime answer: certify a champion, or report the panel as homogeneous."""

    winner = int(np.argmax((counts / trials) * (1.0 - counts / trials)))
    raw = float((counts[winner] / trials) * (1.0 - counts[winner] / trials))
    pvalue = winner_p_value(counts, trials)
    if pvalue <= alpha:
        return {"regime": "champion", "raw": raw, "corrected": raw, "pvalue": pvalue}
    inside = invert_max(raw, len(counts), trials)
    return {"regime": "homogeneous", "raw": raw, "corrected": inside, "pvalue": pvalue}


def bias_table(trials: int = TRIALS) -> list[dict[str, float]]:
    rows = []
    for candidates in (5, 10, 20):
        rows.append(
            {
                "candidates": candidates,
                "expected_max_at_baseline": expected_max(BASELINE, candidates, trials),
                "inflation": expected_max(BASELINE, candidates, trials) / phi(BASELINE),
            }
        )
    return rows


def validation(
    replicates: int = 500, trials: int = TRIALS, seed: int = 20261124
) -> list[dict[str, float]]:
    """Fixed-seed check of the reporting rule on a null panel and on real leaders."""

    generator = np.random.default_rng(seed)
    scenarios = {
        "null": [BASELINE] * 10,
        "leader_2_3": [0.0849] + [BASELINE] * 9,
        "leader_1_5": [0.0535] + [BASELINE] * 9,
    }
    rows = []
    for name, truth in scenarios.items():
        counts = generator.binomial(trials, truth, size=(replicates, len(truth)))
        answers = [report(counts[i], trials) for i in range(replicates)]
        estimates = np.array([answer["corrected"] for answer in answers])
        best = max(phi(q) for q in truth)
        rows.append(
            {
                "scenario": name,
                "mean_reported": float(estimates.mean()),
                "ratio_to_truth": float(estimates.mean() / best),
                "claim_rate": float(
                    np.mean([answer["regime"] == "champion" for answer in answers])
                ),
            }
        )
    return rows


def main() -> None:
    law = grouping_law(BASELINE, 8)
    print(
        "grouping: per rollout %.4f, ceiling %.4f, coverage %.4f, "
        "per token after filtering %.4f"
        % (law["per_rollout"], law["ceiling"], law["coverage"], law["filtered_per_token"])
    )
    print()
    print("candidates  expected max  inflation at the baseline")
    for row in bias_table():
        print(
            "%10d  %.4f        x%.2f"
            % (row["candidates"], row["expected_max_at_baseline"], row["inflation"])
        )
    print()
    print("scenario       mean reported  ratio to truth  claim rate")
    for row in validation():
        print(
            "%-13s  %.4f         x%.2f           %.3f"
            % (row["scenario"], row["mean_reported"], row["ratio_to_truth"], row["claim_rate"])
        )
    if abs(law["per_rollout"] - law["ceiling"]) > 1e-12:
        raise SystemExit("the per-rollout mass does not match the ceiling")
    if abs(law["filtered_per_token"] - law["per_rollout"] * law["coverage"]) > 1e-12:
        raise SystemExit("the filtering cost does not match coverage")
    rows = bias_table()
    if not all(row["inflation"] > 1.0 for row in rows):
        raise SystemExit("the panel maximum is not inflated at the baseline")
    check = validation()
    if check[0]["ratio_to_truth"] > 1.10:
        raise SystemExit("the null panel is still inflated after correction")
    if check[1]["ratio_to_truth"] < 0.90:
        raise SystemExit("the correction erased a real champion")
    if check[1]["claim_rate"] < 0.85:
        raise SystemExit("the rule fails to certify a leader it can resolve")


if __name__ == "__main__":
    main()
