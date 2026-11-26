"""One-leader independent Bernoulli sensitivity with randomized ties."""

from __future__ import annotations

import bisect
import math
import random

from selection_law import BASELINE, binomial_pmf, phi, score_distribution


def leader_rate(ratio: float, baseline: float) -> float:
    variance = phi(baseline) * ratio
    if not 0 < baseline < 1 or not math.isfinite(ratio) or ratio <= 1 or variance > 0.25:
        raise ValueError("impossible variance ratio")
    low = (1 - math.sqrt(1 - 4 * variance)) / 2
    return low if baseline <= 0.5 else 1 - low


def pcs_exact(leader: float, trials: int, candidates: int, baseline: float = BASELINE) -> float:
    if type(candidates) is not int or candidates < 2 or phi(leader) + 1e-15 < phi(baseline):
        raise ValueError("invalid leader or candidates")
    followers = score_distribution(trials, baseline)
    leads = score_distribution(trials, leader)
    below = result = 0.0
    m = candidates - 1
    for score, f in sorted(followers.items()):
        win = math.fsum(
            math.comb(m, j) * f**j * below**(m - j) / (j + 1) for j in range(m + 1)
        )
        result += leads[score] * win
        below += f
    return min(1.0, max(0.0, result))


def grid_plan(target: float, leader: float, candidates: int, baseline: float = BASELINE) -> dict:
    if not 0 < target < 1:
        raise ValueError("invalid target")
    grid = (25, 50, 100, 200, 400, 700, 1000, 1600, 2400, 3200, 4800, 6400, 10000)
    for n in grid:
        pcs = pcs_exact(leader, n, candidates, baseline)
        if pcs >= target:
            return {"first_tested_n_meeting_target": n, "pcs": pcs, "tested_grid": grid}
    return {
        "first_tested_n_meeting_target": None,
        "pcs_at_grid_max": pcs,
        "tested_grid": grid,
    }


def racing_pcs(
    ratio: float,
    candidates: int,
    keep: int,
    pilot_fraction: float,
    replicates: int = 4000,
    total: int = 4000,
    seed: int = 20261124,
    baseline: float = BASELINE,
) -> dict:
    if not 2 <= candidates or not 1 <= keep <= candidates or not 0 < pilot_fraction <= 1 or replicates < 1:
        raise ValueError("invalid racing design")
    pilot = int(total * pilot_fraction / candidates)
    final = (total - pilot * candidates) // keep
    if pilot < 1:
        raise ValueError("zero pilot budget")
    lead = leader_rate(ratio, baseline)

    def cdf(n, p):
        if n == 0:
            return [1.0]
        result = []
        s = 0.0
        for mass in binomial_pmf(n, p):
            s += mass
            result.append(s)
        result[-1] = 1.0
        return result

    first = [cdf(pilot, p) for p in (lead, baseline)]
    second = [cdf(final, p) for p in (lead, baseline)]
    rng = random.Random(seed)
    wins = 0
    for _ in range(replicates):
        counts = [bisect.bisect_left(first[int(i != 0)], rng.random()) for i in range(candidates)]
        indices = list(range(candidates))
        rng.shuffle(indices)
        survivors = sorted(
            indices, key=lambda i: counts[i] * (pilot - counts[i]), reverse=True
        )[:keep]
        for i in survivors:
            counts[i] += bisect.bisect_left(second[int(i != 0)], rng.random())
        rng.shuffle(survivors)
        winner = max(survivors, key=lambda i: counts[i] * (pilot + final - counts[i]))
        wins += winner == 0
    p = wins / replicates
    z = 1.95996398454
    den = 1 + z * z / replicates
    center = (p + z * z / (2 * replicates)) / den
    half = z * math.sqrt(p * (1 - p) / replicates + z * z / (4 * replicates**2)) / den
    return {
        "pcs": p,
        "wilson95": [center - half, center + half],
        "replicates": replicates,
        "pilot_per_arm": pilot,
        "final_per_survivor": final,
        "spent": pilot * candidates + final * keep,
    }
