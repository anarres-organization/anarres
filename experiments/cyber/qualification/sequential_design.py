"""An early-stopping design for comparing two environments' signal density.

The fixed protocol spends 400 rollouts per arm and looks once. A group-sequential
variant looks at 160, 320, and 480 trials per arm, rejects as soon as the profile
likelihood ratio crosses a boundary, and accepts as soon as the ratio falls below
one, which is the point where the data favour equal density. All error rates and
expected sample sizes below come from an exact dynamic program over the joint
lattice of successes, not from simulation.

Two facts make the exact evaluation cheap. The profile likelihood ratio for
equal density has a closed form: the null splits into p_a = p_b = p and
p_a = p, p_b = 1 - p, and each branch maximises at a rational point, so no
optimiser is needed. And the joint distribution of successes is a four-term
shift of the previous lattice, so one pass of vectorised shifts advances both
arms by one trial.
"""

from __future__ import annotations

import math

import numpy as np

NOMINAL = 400
DESIGN_TRIALS = 480
LOOKS = (160, 320, 480)
FUTILITY = 1.0
CRITICAL = 3.841459


def phi(p: float) -> float:
    return p * (1.0 - p)


def p_from_phi(value: float) -> float:
    """Lower of the two success rates that produce a given density."""

    discriminant = 1.0 - 4.0 * value
    if discriminant <= 0:
        return 0.5
    return (1.0 - math.sqrt(discriminant)) / 2.0


def _binomial_log_likelihood(k: np.ndarray, n: float, p: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        upper = np.where(k == 0, 0.0, k * np.log(np.clip(p, 1e-300, 1.0)))
        lower = np.where(n - k == 0, 0.0, (n - k) * np.log(np.clip(1.0 - p, 1e-300, 1.0)))
    return upper + lower


def profile_lr(a: np.ndarray, b: np.ndarray, n: float) -> np.ndarray:
    """Profile likelihood ratio for equal density, in closed form.

    The alternative fits each arm at its own rate. The null admits two branches:
    equal rates, and rates that sum to one, which is where equal density also
    holds. Each branch maximum sits at a rational point, so the statistic is a
    difference of log likelihoods with no numerical search.
    """

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    alternative = _binomial_log_likelihood(a, n, np.clip(a / n, 1e-12, 1 - 1e-12)) + (
        _binomial_log_likelihood(b, n, np.clip(b / n, 1e-12, 1 - 1e-12))
    )
    common = np.clip((a + b) / (2.0 * n), 1e-12, 1 - 1e-12)
    equal_branch = _binomial_log_likelihood(a, n, common) + _binomial_log_likelihood(b, n, common)
    mirrored = np.clip((a + n - b) / (2.0 * n), 1e-12, 1 - 1e-12)
    mirror_branch = _binomial_log_likelihood(a, n, mirrored) + _binomial_log_likelihood(
        b, n, 1.0 - mirrored
    )
    return np.maximum(2.0 * (alternative - np.maximum(equal_branch, mirror_branch)), 0.0)


def evaluate(
    p_a: float,
    p_b: float,
    critical: float,
    futility: float | None = None,
    trials: int = DESIGN_TRIALS,
    looks: tuple[int, ...] = LOOKS,
) -> dict[str, float]:
    """Exact rejection probability, expected trials, and stopping mix for one pair."""

    if looks[-1] != trials:
        raise ValueError("the last look must be the final trial count")
    mass = np.zeros((trials + 1, trials + 1))
    mass[0, 0] = 1.0
    rejected = 0.0
    expected = 0.0
    early = 0.0
    for step in range(1, trials + 1):
        source = mass[:trials, :trials]
        nxt = np.zeros_like(mass)
        nxt[:trials, :trials] += source * ((1.0 - p_a) * (1.0 - p_b))
        nxt[1 : trials + 1, :trials] += source * (p_a * (1.0 - p_b))
        nxt[:trials, 1 : trials + 1] += source * ((1.0 - p_a) * p_b)
        nxt[1 : trials + 1, 1 : trials + 1] += source * (p_a * p_b)
        mass = nxt
        if step in looks:
            ia, ib = np.nonzero(mass > 0.0)
            weights = mass[ia, ib]
            statistic = profile_lr(ia.astype(float), ib.astype(float), float(step))
            hit = statistic > critical
            rejected += weights[hit].sum()
            expected += step * weights[hit].sum()
            stop = hit.copy()
            if futility is not None and step > looks[0]:
                stop |= statistic < futility
            expected += step * weights[stop & ~hit].sum()
            early += weights[stop].sum()
            mass[ia[stop], ib[stop]] = 0.0
    expected += trials * mass.sum()
    return {
        "rejection_probability": float(rejected),
        "expected_trials": float(expected),
        "stopped_early_fraction": float(early),
    }


def fixed_power(p_a: float, p_b: float, trials: int, critical: float = CRITICAL) -> float:
    """Rejection probability of the single-look test at the same nominal size."""

    counts = np.arange(trials + 1, dtype=float)
    from scipy.stats import binom

    outer = np.outer(binom.pmf(counts, trials, p_a), binom.pmf(counts, trials, p_b))
    statistic = profile_lr(counts[:, None], counts[None, :], float(trials))
    return float(outer[statistic > critical].sum())


def calibrate(target: float = 0.05, low: float = 3.0, high: float = 9.0) -> float:
    for _ in range(12):
        middle = (low + high) / 2.0
        result = evaluate(0.035, 0.035, middle, FUTILITY)
        if result["rejection_probability"] > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def battery() -> list[dict[str, float]]:
    critical = calibrate()
    base = 0.035
    rows = []
    for ratio in (2.3, 1.8, 1.5):
        rival = p_from_phi(phi(base) * ratio)
        fixed = fixed_power(base, rival, NOMINAL)
        sequential = evaluate(base, rival, critical, FUTILITY)
        rows.append(
            {
                "ratio": ratio,
                "rival_rate": rival,
                "fixed_power": fixed,
                "sequential_power": sequential["rejection_probability"],
                "sequential_trials": sequential["expected_trials"],
                "saving": 1.0 - sequential["expected_trials"] / NOMINAL,
            }
        )
    return rows


def main() -> None:
    critical = calibrate()
    null = evaluate(0.035, 0.035, critical, FUTILITY)
    print(f"boundary {critical:.3f} at looks {LOOKS}, futility {FUTILITY}")
    print(
        f"null: alpha {null['rejection_probability']:.4f}, "
        f"expected trials {null['expected_trials']:.0f} "
        f"against {NOMINAL} fixed"
    )
    print()
    print("ratio  fixed power  seq power  seq trials  saving vs fixed 400")
    for row in battery():
        line = "%.1f   %.3f      %.3f     %.0f        %+.0f%%" % (
            row["ratio"],
            row["fixed_power"],
            row["sequential_power"],
            row["sequential_trials"],
            row["saving"] * 100,
        )
        print(line)
    if not null["rejection_probability"] <= 0.055:
        raise SystemExit("the boundary does not hold the size")
    if not null["expected_trials"] < NOMINAL:
        raise SystemExit("the sequential design costs more than fixed under the null")
    strongest = battery()[0]
    if strongest["sequential_power"] < 0.85:
        raise SystemExit("power fell below the fixed protocol")
    if strongest["saving"] <= 0:
        raise SystemExit("the sequential design did not save trials under the alternative")


if __name__ == "__main__":
    main()
