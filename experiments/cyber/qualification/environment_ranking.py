"""Comparing two environments by signal density: a symmetric exact test.

Signal density is proportional to p (1 - p), so two environments with success
probabilities p and 1 - p carry the same signal. Any comparison that ranks
environments by success rate therefore ranks the wrong quantity, and the
hypothesis a comparison should test is equality of p (1 - p), not equality of p.

This module builds that test from the binomial likelihood. Each environment
contributes two sufficient statistics, successes s and trials t, because tasks
are independent and the per-task group size only enters through the trial count.
The null sets p (1 - p) equal across the two environments while leaving the
common value free, so the likelihood has to be profiled over that value and over
which side of one half each environment sits.

The module also reports the smallest density ratio a fixed budget can detect, and
shows that a verifier with false negatives breaks the p against 1 - p symmetry in
a fixed direction.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass

CHI_SQUARE_1DF_95 = 3.841
DEFAULT_TRIALS = 400


def phi(p: float) -> float:
    """Signal density per unit success probability, up to its token scale."""

    return p * (1 - p)


def phi_roots(value: float, *, higher: bool) -> float:
    """Success probability on a chosen side of one half with a given phi."""

    discriminant = 1 - 4 * value
    if discriminant < 0:
        raise ValueError("phi above one quarter has no success probability")
    root = math.sqrt(discriminant) / 2
    return 0.5 + root if higher else 0.5 - root


def log_likelihood(successes: int, trials: int, p: float) -> float:
    if p <= 0:
        return 0.0 if successes == 0 else -math.inf
    if p >= 1:
        return 0.0 if successes == trials else -math.inf
    if successes < 0 or successes > trials:
        raise ValueError("successes must lie within trials")
    return (
        math.lgamma(trials + 1)
        - math.lgamma(successes + 1)
        - math.lgamma(trials - successes + 1)
        + successes * math.log(p)
        + (trials - successes) * math.log(1 - p)
    )


@dataclass(frozen=True)
class Comparison:
    likelihood_ratio: float
    p_a: float
    p_b: float
    phi_a: float
    phi_b: float
    rejected_at_95: bool


def compare(successes_a: int, trials_a: int, successes_b: int, trials_b: int) -> Comparison:
    """Profile likelihood ratio for equal signal density across two environments."""

    p_a = successes_a / trials_a
    p_b = successes_b / trials_b
    unconstrained = log_likelihood(successes_a, trials_a, p_a) + log_likelihood(
        successes_b, trials_b, p_b
    )

    best = -math.inf
    for higher_a in (False, True):
        for higher_b in (False, True):
            low, high = 1e-12, 0.25 - 1e-12
            for _ in range(160):
                left = low + (high - low) / 3
                right = high - (high - low) / 3
                if _constrained(
                    left, successes_a, trials_a, successes_b, trials_b, higher_a, higher_b
                ) < (
                    _constrained(
                        right, successes_a, trials_a, successes_b, trials_b, higher_a, higher_b
                    )
                ):
                    low = left
                else:
                    high = right
            candidate = _constrained(
                (low + high) / 2,
                successes_a,
                trials_a,
                successes_b,
                trials_b,
                higher_a,
                higher_b,
            )
            best = max(best, candidate)
    statistic = max(0.0, 2 * (unconstrained - best))
    return Comparison(
        likelihood_ratio=statistic,
        p_a=p_a,
        p_b=p_b,
        phi_a=phi(p_a),
        phi_b=phi(p_b),
        rejected_at_95=statistic > CHI_SQUARE_1DF_95,
    )


def _constrained(
    value: float,
    successes_a: int,
    trials_a: int,
    successes_b: int,
    trials_b: int,
    higher_a: bool,
    higher_b: bool,
) -> float:
    first = phi_roots(value, higher=higher_a)
    second = phi_roots(value, higher=higher_b)
    return log_likelihood(successes_a, trials_a, first) + log_likelihood(
        successes_b, trials_b, second
    )


def rejection_rate(
    p_a: float,
    p_b: float,
    trials: int = DEFAULT_TRIALS,
    draws: int = 300,
    seed: int = 20_260_112,
) -> float:
    """Rejection rate of the equal-density test at the 95 percent point."""

    generator = random.Random(seed)
    hits = 0
    for _ in range(draws):
        successes_a = sum(1 for _ in range(trials) if generator.random() < p_a)
        successes_b = sum(1 for _ in range(trials) if generator.random() < p_b)
        hits += compare(successes_a, trials, successes_b, trials).rejected_at_95
    return hits / draws


def minimum_detectable(
    baseline: float,
    trials: int = DEFAULT_TRIALS,
    target_power: float = 0.8,
    draws: int = 200,
) -> dict[str, dict[str, float]]:
    """Closest detectable density on each side, at 95 percent level and target power."""

    result = {}
    for label, start, stop, step in (
        ("higher", baseline + 0.005, 0.5, 0.005),
        ("lower", baseline - 0.005, 0.0, -0.005),
    ):
        probe = start
        while step > 0 and probe <= stop or step < 0 and probe >= stop:
            rate = rejection_rate(baseline, probe, trials, draws=draws)
            if rate >= target_power:
                result[label] = {
                    "p": round(probe, 4),
                    "phi": round(phi(probe), 4),
                    "ratio": round(phi(probe) / phi(baseline), 3),
                    "power": round(rate, 3),
                }
                break
            probe += step
        if label not in result:
            raise SystemExit(f"no {label} density reaches the target power")
    return result


def verifier_symmetry_break(false_negative: float) -> list[dict[str, float]]:
    """How a false-negative rate separates a density pair that was symmetric."""

    rows = []
    for p in (0.10, 0.25, 0.50, 0.75, 0.90):
        partner = 1 - p
        reported = p * (1 - false_negative)
        reported_partner = partner * (1 - false_negative)
        rows.append(
            {
                "p": p,
                "partner": partner,
                "phi_clean": round(phi(p), 4),
                "phi_reported": round(phi(reported), 4),
                "phi_partner_reported": round(phi(reported_partner), 4),
                "ratio": round(phi(reported) / phi(reported_partner), 3),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()

    print("symmetry: phi(p) equals phi(1 - p)")
    for p in (0.035, 0.10, 0.25, 0.50, 0.75, 0.90):
        print(f"  p={p:5.3f} phi={phi(p):.4f}  p'={1 - p:5.3f} phi={phi(1 - p):.4f}")
        if abs(phi(p) - phi(1 - p)) > 1e-12:
            raise SystemExit("symmetry identity fails")
    print()

    print("calibration of the equal-density test at the 95 percent point")
    for p_a, p_b in ((0.035, 0.035), (0.10, 0.90), (0.25, 0.75)):
        rate = rejection_rate(p_a, p_b, draws=200, seed=99 + int(p_a * 1000))
        print(f"  equal density ({p_a}, {p_b}) rejection {rate:.3f}")
        if rate > 0.10:
            raise SystemExit("null rejection rate is not near the nominal level")
    print()

    print("power at 400 trials per environment, baseline p = 0.035")
    print("  p     phi    ratio   power")
    for p_b in (0.02, 0.05, 0.08, 0.12, 0.20, 0.35):
        rate = rejection_rate(0.035, p_b, draws=200)
        print(f"  {p_b:5.3f}  {phi(p_b):.4f}  {phi(p_b) / phi(0.035):5.2f}  {rate:.3f}")
    print()

    print("minimum detectable density at 400 trials per environment")
    detectable = minimum_detectable(0.035)
    for label, entry in detectable.items():
        print(
            f"  {label:6s} p = {entry['p']:.3f}, phi = {entry['phi']:.4f}, "
            f"ratio {entry['ratio']:.2f} at power {entry['power']:.3f}"
        )
    print()

    print("symmetry break under a verifier with 38 percent false negatives")
    print("   p     partner  phi_clean  phi_reported  phi_partner  ratio")
    for row in verifier_symmetry_break(0.38):
        print(
            f"  {row['p']:5.2f}  {row['partner']:7.2f}  {row['phi_clean']:9.4f}  "
            f"{row['phi_reported']:12.4f}  {row['phi_partner_reported']:11.4f}  "
            f"{row['ratio']:5.2f}"
        )
        if row["p"] < 0.5 and row["ratio"] >= 1:
            raise SystemExit("the snap toward one half did not favour the easier task")
    print()

    print("verdict for a 400-rollout panel")
    print(
        f"  densities between {detectable['lower']['ratio']:.2f} and "
        f"{detectable['higher']['ratio']:.2f} times the baseline are indistinguishable "
        "at 95 percent confidence with 80 percent power"
    )


if __name__ == "__main__":
    main()
