"""What a screening budget buys when several environments compete.

One leader against K - 1 identical followers, all measured at the same number of
rollouts per arm. The probability of identifying the leader is exact, because the
arms are independent and the leader only has to beat the largest of the followers:

    PCS(leader, n, K) = sum over k of f_lead(k) * S(k)^(K - 1)

Two questions follow. How much budget does a given separation need, and does
reallocating the same budget between a pilot and a final round help? The first is
exact; the second is evaluated on seeded panels and cross-checked against the
exact single-round answer.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import binom

BASELINE = 0.035
LEADERS = {2.3: 0.0849, 1.5: 0.0535, 1.2: 0.0430}
TOTAL = 4000


def phi(p):
    return p * (1.0 - p)


def pcs_exact(leader: float, trials: int, candidates: int, baseline: float = BASELINE) -> float:
    """Exact probability that the leader's arm has the largest density estimate."""

    counts = np.arange(trials + 1)
    values = (counts / trials) * (1.0 - counts / trials)
    order = np.argsort(values)
    follower_cdf = np.cumsum(binom.pmf(counts, trials, baseline)[order])
    survivor = np.empty_like(values)
    survivor[order] = follower_cdf
    return float((binom.pmf(counts, trials, leader) * survivor ** (candidates - 1)).sum())


def trials_for_pcs(
    target: float, leader: float, candidates: int, high: int = 8000, baseline: float = BASELINE
) -> int:
    """Smallest per-arm count that reaches the target identification probability."""

    low = 1
    while low < high:
        middle = (low + high) // 2
        if pcs_exact(leader, middle, candidates, baseline) >= target:
            high = middle
        else:
            low = middle + 1
    return low


def even_split_pcs(ratio: float, candidates: int, total: int = TOTAL) -> float:
    return pcs_exact(LEADERS[ratio], total // candidates, candidates)


def racing_pcs(
    ratio: float,
    candidates: int,
    keep: int,
    pilot_fraction: float,
    replicates: int = 4000,
    total: int = TOTAL,
    seed: int = 20261124,
) -> float:
    """Seeded two-stage screen: a pilot on every arm, then depth on the survivors."""

    generator = np.random.default_rng(seed)
    truth = np.array([LEADERS[ratio]] + [BASELINE] * (candidates - 1))
    pilot = int(total * pilot_fraction / candidates)
    final = int((total - pilot * candidates) / keep)
    first = generator.binomial(pilot, truth, size=(replicates, candidates))
    estimate = (first / pilot) * (1.0 - first / pilot)
    survivors = np.argsort(-estimate, axis=1)[:, :keep]
    mask = np.zeros((replicates, candidates), dtype=bool)
    mask[np.arange(replicates)[:, None], survivors] = True
    second = generator.binomial(final, truth, size=(replicates, candidates))
    combined = (first + second) / (pilot + final)
    combined = combined * (1.0 - combined)
    return float(np.mean(np.where(mask, combined, -1.0).argmax(axis=1) == 0))


def equivalent_trials(ratio: float, candidates: int, target: float) -> int:
    """Per-arm count an even split would need to match a racing probability."""

    return trials_for_pcs(target, LEADERS[ratio], candidates)


def budget_table() -> list[dict[str, float]]:
    rows = []
    for ratio in (2.3, 1.5, 1.2):
        for candidates in (6, 10):
            for trials in (200, 400, 700, 1000, 1600):
                rows.append(
                    {
                        "ratio": ratio,
                        "candidates": candidates,
                        "trials": trials,
                        "pcs": pcs_exact(LEADERS[ratio], trials, candidates),
                    }
                )
    return rows


def racing_table() -> list[dict[str, float]]:
    rows = []
    for ratio in (2.3, 1.5):
        for candidates in (6, 10):
            even = even_split_pcs(ratio, candidates)
            best = racing_pcs(ratio, candidates, 4, 0.5)
            rows.append(
                {
                    "ratio": ratio,
                    "candidates": candidates,
                    "even": even,
                    "racing": best,
                    "gain": best - even,
                    "equivalent_trials": float(equivalent_trials(ratio, candidates, best)),
                }
            )
    return rows


def main() -> None:
    print("ratio  K   trials  PCS")
    for row in budget_table():
        print(
            "%.1f   %2d  %5d   %.3f" % (row["ratio"], row["candidates"], row["trials"], row["pcs"])
        )
    print()
    print("ratio  K   even   racing  gain   even trials at the same PCS")
    for row in racing_table():
        print(
            "%.1f   %2d  %.3f  %.3f   %+.3f  %d"
            % (
                row["ratio"],
                row["candidates"],
                row["even"],
                row["racing"],
                row["gain"],
                row["equivalent_trials"],
            )
        )
    if pcs_exact(LEADERS[1.5], 400, 10) >= pcs_exact(LEADERS[1.5], 700, 10):
        raise SystemExit("identification probability is not increasing in trials")
    if pcs_exact(LEADERS[1.5], 1600, 10) < 0.95:
        raise SystemExit("four times the budget does not certify a 1.5 times leader")
    rows = racing_table()
    margin = [row for row in rows if row["ratio"] == 1.5 and row["candidates"] == 10][0]
    if margin["gain"] < 0.05:
        raise SystemExit("racing did not beat the even split at the screening margin")
    if margin["equivalent_trials"] < 450:
        raise SystemExit("racing is not worth at least a tenth of the budget")


if __name__ == "__main__":
    main()
