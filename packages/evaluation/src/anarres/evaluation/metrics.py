"""Small dependency-free evaluation primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def pass_at_one(outcomes: Sequence[bool | int | float]) -> float:
    """Return mean per-response success, not pass@k."""

    if not outcomes:
        raise ValueError("pass@1 requires at least one outcome")
    values = [float(outcome) for outcome in outcomes]
    if any(value not in {0.0, 1.0} for value in values):
        raise ValueError("pass@1 outcomes must be binary")
    return sum(values) / len(values)


def paired_utility(
    trained: Sequence[bool | int | float], warm_start: Sequence[bool | int | float]
) -> float:
    """Return the paired change in pass@1 from a shared evaluation panel."""

    if len(trained) != len(warm_start):
        raise ValueError("paired utility requires panels of equal length")
    return pass_at_one(trained) - pass_at_one(warm_start)


def allocation_regret(utilities: Mapping[str, float], selected: str) -> float:
    """Return utility lost by selecting one environment instead of the best observed one."""

    if not utilities:
        raise ValueError("allocation regret requires at least one environment")
    if selected not in utilities:
        raise KeyError(f"unknown selected environment: {selected}")
    return max(utilities.values()) - utilities[selected]
