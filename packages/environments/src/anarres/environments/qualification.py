"""Task qualification with explicit scientific and infrastructure outcomes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class Qualification(StrEnum):
    ADMITTED = "admitted"
    RESERVE = "reserve"
    REPAIR = "repair"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class QualificationResult:
    status: Qualification
    reason: str


def qualify_group(
    *,
    oracle_passed: bool,
    noop_passed: bool,
    infrastructure_valid: bool,
    rewards: Sequence[float],
) -> QualificationResult:
    """Classify a measured prompt group without hiding infrastructure failure."""

    if not infrastructure_valid:
        return QualificationResult(Qualification.REPAIR, "infrastructure_invalid")
    if not oracle_passed:
        return QualificationResult(Qualification.QUARANTINE, "oracle_failed")
    if noop_passed:
        return QualificationResult(Qualification.QUARANTINE, "noop_accepted")
    if not rewards:
        return QualificationResult(Qualification.REPAIR, "missing_rewards")
    if max(rewards) == min(rewards):
        return QualificationResult(Qualification.RESERVE, "zero_reward_variance")
    return QualificationResult(Qualification.ADMITTED, "mixed_valid_group")
