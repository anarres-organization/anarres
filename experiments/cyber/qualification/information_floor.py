"""Fixed-budget bounds for homogeneous Bernoulli best-arm selection."""

from __future__ import annotations

import math

BASELINE = 0.035  # Conditional planning input, not a validated level-2 rate.


def observed_rate(p: float, false_negative: float = 0.0, false_positive: float = 0.0) -> float:
    if not all(0 <= x <= 1 for x in (p, false_negative, false_positive)):
        raise ValueError("probabilities must lie in [0, 1]")
    return p * (1 - false_negative) + (1 - p) * false_positive


def bernoulli_kl(p: float, q: float) -> float:
    """D(Ber(p) || Ber(q)), including directional boundary cases."""
    if not 0 <= p <= 1 or not 0 <= q <= 1:
        raise ValueError("probabilities must lie in [0, 1]")
    if p == q:
        return 0.0
    if q in (0, 1):
        return math.inf
    a = p * math.log(p / q) if p else 0.0
    b = (1 - p) * math.log((1 - p) / (1 - q)) if p < 1 else 0.0
    return a + b


def bounds(p: float, q: float, candidates: int = 10, error: float = 0.05) -> tuple[float, float]:
    """Necessary and sufficient per-arm counts under the declared model.

    One of K arms has known higher rate q, all others rate p. Independent
    Bernoulli draws, equal fixed n per arm, uniformly correct identification
    across leader identities. The upper bound uses max counts with any tie rule.
    The lower bound is a pairwise leader-swap change of measure.
    """
    if not 0 <= p <= q <= 1 or candidates < 2 or not 0 < error < 0.5:
        raise ValueError("require 0 <= p <= q <= 1, K >= 2, 0 < error < 0.5")
    if p == q:
        return math.inf, math.inf
    information = bernoulli_kl(p, q) + bernoulli_kl(q, p)
    lower = max(1, math.ceil(bernoulli_kl(1 - error, error) / information))
    affinity = math.sqrt(p * q) + math.sqrt((1 - p) * (1 - q))
    if affinity == 0:
        return lower, 1
    exponent = -2 * math.log(affinity)
    if exponent <= 0:
        return lower, math.inf
    upper = max(1, math.ceil(math.log((candidates - 1) / error) / exponent))
    return lower, upper


def binomial_pmf(n: int, p: float) -> list[float]:
    if n < 0 or not 0 <= p <= 1:
        raise ValueError("invalid binomial parameters")
    if p == 0:
        return [1.0] + [0.0] * n
    if p == 1:
        return [0.0] * n + [1.0]
    # Recurrence from the mode avoids underflow of the initial mass.
    mode = min(n, int((n + 1) * p))
    mass = [0.0] * (n + 1)
    mass[mode] = 1.0
    for k in range(mode, n):
        mass[k + 1] = mass[k] * (n - k) / (k + 1) * p / (1 - p)
    for k in range(mode, 0, -1):
        mass[k - 1] = mass[k] * k / (n - k + 1) * (1 - p) / p
    total = math.fsum(mass)
    return [x / total for x in mass]


def probability_correct(n: int, p: float, q: float, candidates: int = 10) -> float:
    """Binomial enumeration for max-count selection with uniform random ties."""
    if candidates < 2 or not 0 <= p <= q <= 1:
        raise ValueError("invalid selection parameters")
    followers = binomial_pmf(n, p)
    leader = binomial_pmf(n, q)
    m = candidates - 1
    below = 0.0
    result = 0.0
    for f, l in zip(followers, leader, strict=True):
        # Conditional on the leader count: j tied, all remaining followers lower.
        win = math.fsum(
            math.comb(m, j) * f**j * below ** (m - j) / (j + 1)
            for j in range(m + 1)
        )
        result += l * win
        below += f
    return min(1.0, max(0.0, result))


def main() -> None:
    print("Conditional homogeneous iid planning; K=10, error=.05")
    print("ratio    lower    sufficient    PCS at n=400")
    for ratio in (1.2, 1.5, 2.3, 3.0):
        q = BASELINE * ratio
        lo, hi = bounds(BASELINE, q)
        print(f"{ratio:4.1f} {lo:8} {hi:13} {probability_correct(400, BASELINE, q):13.6f}")
    print("Common verifier corruption, p=.035, q=.0805:")
    for fn, fp in ((0, 0), (0.38, 0), (0, 0.10)):
        p, q = (observed_rate(x, fn, fp) for x in (BASELINE, BASELINE * 2.3))
        print(f"FN={fn:.2f} FP={fp:.2f}: observed=({p:.6f}, {q:.6f}), bounds={bounds(p, q)}")


if __name__ == "__main__":
    main()
