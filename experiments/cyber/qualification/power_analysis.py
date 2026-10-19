"""Prespecified paired-binary power calculations for cyber qualification.

This approximation sizes an isolated task panel for a paired trained-versus-
warm-start comparison. Final inference uses paired task-cluster resampling; this
calculation is a design gate, not the analysis itself.
"""

from __future__ import annotations

import argparse
import math
from statistics import NormalDist


def required_tasks(
    effect: float,
    discordance: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Return the normal-approximation task count for a paired binary contrast."""

    if not 0 < effect < 1:
        raise ValueError("effect must lie in (0, 1)")
    if not 0 < discordance <= 1:
        raise ValueError("discordance must lie in (0, 1]")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must lie in (0, 1)")
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return math.ceil(z * z * discordance / (effect * effect))


def detectable_effect(
    tasks: int,
    discordance: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
) -> float:
    """Return the normal-approximation detectable paired-binary effect."""

    if tasks < 1:
        raise ValueError("tasks must be positive")
    if not 0 < discordance <= 1:
        raise ValueError("discordance must lie in (0, 1]")
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return z * math.sqrt(discordance / tasks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discordance", type=float, default=0.20)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--power", type=float, default=0.80)
    arguments = parser.parse_args()

    for effect in (0.05, 0.06, 0.07, 0.08, 0.09, 0.10):
        count = required_tasks(
            effect,
            arguments.discordance,
            alpha=arguments.alpha,
            power=arguments.power,
        )
        print(f"effect={effect:.2f} required_tasks={count}")
    for tasks in (128, 192, 256, 320, 384, 512):
        effect = detectable_effect(
            tasks,
            arguments.discordance,
            alpha=arguments.alpha,
            power=arguments.power,
        )
        print(f"tasks={tasks} detectable_effect={effect:.6f}")


if __name__ == "__main__":
    main()
