"""What comparing two environments on shared tasks buys.

An unpaired comparison measures each environment on its own task set. The task
set is part of the measurement, so the difference carries the mix variance of two
panels on top of the binomial variance of each panel. Pairing on shared tasks
removes that component, because each task contributes its difference directly.

This module decomposes the variance at the published panel and reports the factor
by which a paired design shrinks the standard error of the difference. The panel
is proxied by the published k vector, 37 tasks at 0 of 8, 12 at 1 of 8, and 1 at
2 of 8, and the proxy reproduces a total advantage mass of 24.0 against the
released 27.43. That gap makes the decomposition an order statement rather than a
forecast.
"""

from __future__ import annotations

import math
from math import comb

GROUP_SIZE = 8
TASKS = 50
PUBLISHED_K = (0,) * 37 + (1,) * 12 + (2,)
PUBLISHED_MASS = 27.43


def advantage_mass(k: int, group_size: int = GROUP_SIZE) -> float:
    return 2 * k * (group_size - k) / (group_size - 1)


def panel_moments(successes: int) -> tuple[float, float]:
    """Mean and variance of one task's group mass at p estimated as k / G."""

    p = successes / GROUP_SIZE
    if p <= 0 or p >= 1:
        return advantage_mass(successes), 0.0
    mean = 0.0
    second = 0.0
    for k in range(GROUP_SIZE + 1):
        weight = comb(GROUP_SIZE, k) * p**k * (1 - p) ** (GROUP_SIZE - k)
        value = advantage_mass(k)
        mean += weight * value
        second += weight * value * value
    return mean, second - mean * mean


def decomposition() -> dict[str, float | bool]:
    means = []
    variances = []
    for successes in PUBLISHED_K:
        mean, variance = panel_moments(successes)
        means.append(mean)
        variances.append(variance)
    total = sum(means)
    binomial = math.sqrt(sum(variances))
    mean_task = total / TASKS
    spread = math.sqrt(sum((value - mean_task) ** 2 for value in means) / (TASKS - 1))
    mix = math.sqrt(TASKS) * spread
    paired = math.sqrt(2) * binomial
    unpaired = math.sqrt(2) * math.sqrt(binomial**2 + mix**2)
    return {
        "proxy_mass": round(total, 2),
        "published_mass": PUBLISHED_MASS,
        "proxy_close": abs(total - PUBLISHED_MASS) / PUBLISHED_MASS < 0.15,
        "binomial_sd": round(binomial, 3),
        "mix_sd": round(mix, 3),
        "mix_over_binomial": round(mix / binomial, 3),
        "paired_difference_sd": round(paired, 3),
        "unpaired_difference_sd": round(unpaired, 3),
        "paired_gain": round(unpaired / paired, 3),
    }


def detectable_ratio(unpaired_ratio: float) -> float:
    """Apply the pairing factor to a detectable density ratio from an unpaired test."""

    return unpaired_ratio / decomposition()["paired_gain"]


def main() -> None:
    values = decomposition()
    print(f"panel proxy total mass {values['proxy_mass']} against released {PUBLISHED_MASS}")
    print(
        f"binomial sd {values['binomial_sd']}, mix sd {values['mix_sd']}, "
        f"ratio {values['mix_over_binomial']}"
    )
    print(
        f"difference sd: paired {values['paired_difference_sd']} "
        f"against unpaired {values['unpaired_difference_sd']}, "
        f"gain {values['paired_gain']}"
    )
    print()
    print("detectable density ratio carried over from the unpaired test")
    for ratio in (2.30, 1.80):
        print(f"  unpaired {ratio:.2f} -> paired {detectable_ratio(ratio):.2f}")
    print(f"  ratios below the gain of {values['paired_gain']:.2f} stay inside the floor")
    if not values["proxy_close"]:
        raise SystemExit("the panel proxy drifted away from the released mass")
    if values["paired_gain"] <= 1:
        raise SystemExit("pairing did not reduce the difference variance")


if __name__ == "__main__":
    main()
