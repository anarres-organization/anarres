"""Prespecified equal alpha spending for the iid composite variance null."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from environment_ranking import variance_p


def thresholds(looks: tuple[int, ...], alpha: float = 0.05) -> Fraction:
    if (
        not looks
        or any(type(n) is not int or n < 1 for n in looks)
        or tuple(sorted(set(looks))) != looks
        or not 0 < alpha < 1
    ):
        raise ValueError("invalid prespecified looks or alpha")
    return Fraction(str(alpha)) / len(looks)


def decision(counts: list[tuple[int, int]], looks: tuple[int, ...], alpha: float = 0.05) -> dict:
    cut = thresholds(looks, alpha)
    if not 1 <= len(counts) <= len(looks):
        raise ValueError("invalid number of observed looks")
    prev_a = prev_b = prev_n = 0
    for (a, b), n in zip(counts, looks, strict=False):
        if (
            type(a) is not int
            or type(b) is not int
            or not (0 <= a - prev_a <= n - prev_n and 0 <= b - prev_b <= n - prev_n)
        ):
            raise ValueError("invalid cumulative counts")
        if variance_p(a, n, b, n) <= cut:
            return {"status": "reject", "n_per_arm": n}
        prev_a, prev_b, prev_n = a, b, n
    return {
        "status": "not_reject" if len(counts) == len(looks) else "continue",
        "n_per_arm": prev_n,
    }


def evaluate(p: float, q: float, looks: tuple[int, ...], alpha: float = 0.05) -> dict:
    """Finite-state evaluation (floating-point masses), limited to small designs."""
    cut = thresholds(looks, alpha)
    if not 0 <= p <= 1 or not 0 <= q <= 1 or looks[-1] > 100:
        raise ValueError("evaluation supports probabilities and at most 100 trials per arm")
    increments = (
        (0, 0, (1 - p) * (1 - q)),
        (1, 0, p * (1 - q)),
        (0, 1, (1 - p) * q),
        (1, 1, p * q),
    )
    states = {(0, 0): 1.0}
    rejected = spent = 0.0
    for n in range(1, looks[-1] + 1):
        nxt = defaultdict(float)
        for (a, b), w in states.items():
            for da, db, m in increments:
                if m:
                    nxt[a + da, b + db] += w * m
        if n in looks:
            for a, b in list(nxt):
                if variance_p(a, n, b, n) <= cut:
                    mass = nxt.pop((a, b))
                    rejected += mass
                    spent += n * mass
        states = nxt
    remainder = sum(states.values())
    return {
        "rejection_probability": rejected,
        "expected_trials_per_arm": spent + looks[-1] * remainder,
        "max_trials_per_arm": looks[-1],
        "mass_check": rejected + remainder,
    }
