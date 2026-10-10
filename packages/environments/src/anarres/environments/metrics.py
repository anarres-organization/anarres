"""Policy-relative coordinates used by environment-utility studies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class GroupMeasurement:
    task_id: str
    admitted_advantage_mass: float
    generated_action_tokens: int


@dataclass(frozen=True, slots=True)
class EnvironmentCoordinates:
    rho_per_million_tokens: float
    effective_coverage: float
    total_admitted_advantage_mass: float
    generated_action_tokens: int
    prompt_count: int


def compute_coordinates(groups: Iterable[GroupMeasurement]) -> EnvironmentCoordinates:
    """Compute signal density and normalized effective prompt coverage.

    Effective coverage is zero when no admitted advantage mass is available.
    Negative advantage mass and non-positive generated-token counts are invalid.
    """

    measured = tuple(groups)
    if not measured:
        raise ValueError("at least one prompt group is required")
    if any(group.generated_action_tokens <= 0 for group in measured):
        raise ValueError("every prompt group must have positive generated action tokens")
    if any(group.admitted_advantage_mass < 0 for group in measured):
        raise ValueError("admitted advantage mass must be non-negative")

    masses = [group.admitted_advantage_mass for group in measured]
    total_mass = sum(masses)
    total_tokens = sum(group.generated_action_tokens for group in measured)
    rho = 1_000_000.0 * total_mass / total_tokens

    squared_mass = sum(mass * mass for mass in masses)
    coverage = 0.0 if squared_mass == 0 else (total_mass * total_mass) / squared_mass / len(masses)
    if not isfinite(rho) or not isfinite(coverage):
        raise ValueError("environment coordinates must be finite")

    return EnvironmentCoordinates(
        rho_per_million_tokens=rho,
        effective_coverage=coverage,
        total_admitted_advantage_mass=total_mass,
        generated_action_tokens=total_tokens,
        prompt_count=len(measured),
    )
