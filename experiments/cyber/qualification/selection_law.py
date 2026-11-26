"""Conditional iid binary-reward planning; not usable signal per token."""

from __future__ import annotations

import math

BASELINE = 0.035  # hypothetical until a level-2 rerun


def phi(p: float) -> float:
    if not 0 <= p <= 1:
        raise ValueError("invalid probability")
    return p * (1 - p)


def advantage_mass(k: int, group_size: int) -> float:
    if (
        type(k) is not int
        or type(group_size) is not int
        or not 0 <= k <= group_size
        or group_size < 2
    ):
        raise ValueError("invalid group")
    return 2 * k * (group_size - k) / (group_size - 1)


def grouping_law(p: float, group_size: int) -> dict:
    if type(group_size) is not int or group_size < 2:
        raise ValueError("invalid group size")
    raw = 2 * phi(p)
    coverage = max(0.0, 1 - p**group_size - (1 - p)**group_size)
    return {
        "mixed_probability": coverage,
        "generated_rollouts_per_group": group_size,
        "retained_rollouts_per_generated_group": group_size * coverage,
        "raw_mass_per_generated_rollout": raw,
        "raw_mass_per_retained_rollout": raw / coverage if coverage else None,
        "generated_rollouts_per_retained_group": group_size / coverage if coverage else None,
        "admitted_rollouts_if_all_mixed_groups_admitted": group_size * coverage,
    }


def binomial_pmf(n: int, p: float) -> list[float]:
    if type(n) is not int or n < 1 or not 0 <= p <= 1:
        raise ValueError("invalid binomial parameters")
    if p == 0:
        return [1.0] + [0.0] * n
    if p == 1:
        return [0.0] * n + [1.0]
    mode = min(n, int((n + 1) * p))
    mass = [0.0] * (n + 1)
    mass[mode] = 1.0
    for k in range(mode, n):
        mass[k + 1] = mass[k] * (n - k) / (k + 1) * p / (1 - p)
    for k in range(mode, 0, -1):
        mass[k - 1] = mass[k] * k / (n - k + 1) * (1 - p) / p
    total = math.fsum(mass)
    return [x / total for x in mass]


def score_distribution(n: int, p: float) -> dict[int, float]:
    dist = {}
    for k, weight in enumerate(binomial_pmf(n, p)):
        score = k * (n - k)
        dist[score] = dist.get(score, 0.0) + weight
    return dist


def expected_max(p: float, candidates: int, trials: int = 400) -> float:
    if type(candidates) is not int or candidates < 1:
        raise ValueError("invalid number of candidates")
    acc = result = 0.0
    for score, weight in sorted(score_distribution(trials, p).items()):
        result += score / trials**2 * ((acc + weight)**candidates - acc**candidates)
        acc += weight
    return result


def validate_counts(counts: list[int], trials: int) -> None:
    if (
        type(trials) is not int
        or trials < 1
        or not counts
        or any(type(k) is not int or not 0 <= k <= trials for k in counts)
    ):
        raise ValueError("invalid counts or trials")
    if len(counts) * trials > 10000:
        raise ValueError("conditional enumeration limited to 10000 draws")


def winner_p_value(counts: list[int], trials: int = 400) -> float:
    """Exact conditional global homogeneous-rate test (inclusive max score)."""
    validate_counts(counts, trials)
    arms = len(counts)
    total = min(sum(counts), arms * trials - sum(counts))
    observed = max(k * (trials - k) for k in counts)
    if observed == 0:
        return 1.0
    allowed = [
        (k, math.comb(trials, k))
        for k in range(min(trials, total) + 1)
        if k * (trials - k) < observed
    ]
    dp = [1] + [0] * total
    for _ in counts:
        nxt = [0] * (total + 1)
        for i, w in enumerate(dp):
            if w:
                for k, m in allowed:
                    if i + k > total:
                        break
                    nxt[i + k] += w * m
        dp = nxt
    denom = math.comb(arms * trials, total)
    return (denom - dp[total]) / denom


def report(counts: list[int], trials: int = 400, alpha: float = 0.05) -> dict:
    if not 0 < alpha < 1:
        raise ValueError("invalid alpha")
    validate_counts(counts, trials)
    scores = [k * (trials - k) for k in counts]
    raw = max(scores)
    p = winner_p_value(counts, trials)
    return {
        "winner_indices": [i for i, x in enumerate(scores) if x == raw],
        "selected_plugin_reward_variance": raw / trials**2,
        "global_homogeneity_p": p,
        "reject_global_homogeneity": p <= alpha,
        "effect_estimate": "not selection-adjusted; independent confirmation required",
    }


if __name__ == "__main__":
    print(grouping_law(BASELINE, 8))
    print(report([34, 14, 12, 16, 11, 15, 13, 9, 17, 10]))
