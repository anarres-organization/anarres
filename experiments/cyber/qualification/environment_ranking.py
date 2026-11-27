"""Exact tests of raw binary reward variance in an iid planning model."""

from __future__ import annotations

import math
from fractions import Fraction
from functools import lru_cache


def phi(p: float) -> float:
    if not 0 <= p <= 1:
        raise ValueError("invalid probability")
    return p * (1 - p)


def validate(a: int, na: int, b: int, nb: int) -> None:
    if (
        any(type(v) is not int for v in (a, na, b, nb))
        or min(na, nb) < 1
        or not (0 <= a <= na and 0 <= b <= nb)
    ):
        raise ValueError("invalid binomial counts")


@lru_cache(maxsize=4096)
def conditional_tails(na: int, nb: int, total: int) -> tuple[int, tuple[int, ...], int]:
    lo = max(0, total - nb)
    hi = min(na, total)
    weights = [math.comb(na, k) * math.comb(nb, total - k) for k in range(lo, hi + 1)]
    by_weight = {}
    for w in weights:
        by_weight[w] = by_weight.get(w, 0) + w
    running = 0
    for w in sorted(by_weight):
        running += by_weight[w]
        by_weight[w] = running
    return lo, tuple(by_weight[w] for w in weights), math.comb(na + nb, total)


def equality_p(a: int, na: int, b: int, nb: int) -> Fraction:
    validate(a, na, b, nb)
    lo, tails, denom = conditional_tails(na, nb, a + b)
    return Fraction(tails[a - lo], denom)


def variance_p(a: int, na: int, b: int, nb: int) -> Fraction:
    # H0 is the union of p_A=p_B and p_A=1-p_B; reject only both branches.
    return max(equality_p(a, na, b, nb), equality_p(a, na, nb - b, nb))


def compare(a: int, na: int, b: int, nb: int, alpha: float = 0.05) -> dict:
    if not 0 < alpha < 1:
        raise ValueError("invalid alpha")
    p = variance_p(a, na, b, nb)
    return {
        "variance_a_plugin": phi(a / na),
        "variance_b_plugin": phi(b / nb),
        "equal_rate_p": float(equality_p(a, na, b, nb)),
        "mirror_rate_p": float(equality_p(a, na, nb - b, nb)),
        "union_null_p": float(p),
        "reject": p <= Fraction(str(alpha)),
    }


def binomial_pmf(n: int, p: float) -> list[float]:
    if type(n) is not int or not 0 <= n <= 1000 or not 0 <= p <= 1:
        raise ValueError("invalid enumeration size or probability")
    return [math.comb(n, k) * p**k * (1 - p)**(n - k) for k in range(n + 1)]


def fixed_power(p: float, q: float, n: int, alpha: float = 0.05) -> float:
    if not 0 < alpha < 1 or not 1 <= n <= 500:
        raise ValueError("invalid fixed design")
    pa, pb = binomial_pmf(n, p), binomial_pmf(n, q)
    cut = Fraction(str(alpha))
    return math.fsum(
        x * y
        for a, x in enumerate(pa) if x
        for b, y in enumerate(pb) if y and variance_p(a, n, b, n) <= cut
    )


def observed_rate(p: float, fn: float = 0, fp: float = 0) -> float:
    if not all(0 <= v <= 1 for v in (p, fn, fp)):
        raise ValueError("invalid channel")
    return p * (1 - fn) + (1 - p) * fp


def invert_channel(q: float, fn: float = 0, fp: float = 0) -> float:
    if not all(0 <= v <= 1 for v in (q, fn, fp)) or fn + fp == 1:
        raise ValueError("invalid or nonidentifiable channel")
    p = (q - fp) / (1 - fn - fp)
    if not -1e-12 <= p <= 1 + 1e-12:
        raise ValueError("observation incompatible with channel")
    return min(1.0, max(0.0, p))


if __name__ == "__main__":
    print(compare(40, 400, 360, 400))
