"""Portable robotics input contract shared by source drivers and policy runners."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

INFRASTRUCTURE_STATUSES = (
    "valid",
    "reset_failed",
    "simulator_error",
    "checkpoint_error",
    "timeout",
    "runtime_error",
)
TERMINATIONS = ("success", "failure", "truncated")


class RoboticsContractError(ValueError):
    """Raised when a source or attempt violates the portable robotics contract."""


@dataclass(frozen=True)
class EpisodeUnit:
    """The independent unit of a source and the key that groups repeated attempts."""

    unit: str
    grouping_key: str


@dataclass(frozen=True)
class SourceDescription:
    """Native scientific meaning of one candidate source, reported by its driver."""

    environment_id: str
    native_format: str
    driver_version: str
    revision: str
    license: str
    content_digest: str
    episode_unit: EpisodeUnit
    episodes: int
    observation_fields: tuple[str, ...]
    action_fields: tuple[str, ...]
    language_field: str | None
    task_field: str | None
    cost_fields: dict[str, str]
    success_definition: str
    reset_semantics: str
    max_steps: int
    evaluation_contract_digest: str
    missing: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        for field in ("observation_fields", "action_fields", "missing"):
            record[field] = list(record[field])
        return record


def require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RoboticsContractError(f"{field} must be a non-empty string")
    return value


def validate_attempt(row: dict[str, Any]) -> None:
    """Check the invariants of one robotics probe attempt beyond its JSON schema."""

    if row.get("schema_version") != "anarres.robotics-probe-attempt.v1":
        raise RoboticsContractError("unsupported robotics attempt schema")
    status = row.get("infrastructure_status")
    if status not in INFRASTRUCTURE_STATUSES:
        raise RoboticsContractError(f"unknown infrastructure status: {status}")
    if status == "valid":
        if row.get("termination") not in TERMINATIONS:
            raise RoboticsContractError("a valid attempt must record its termination")
        if not isinstance(row.get("success"), bool):
            raise RoboticsContractError("a valid attempt must record closed-loop success")
        if row["success"] != (row["termination"] == "success"):
            raise RoboticsContractError("success and termination disagree")
    elif row.get("success") is not None or row.get("termination") is not None:
        raise RoboticsContractError(
            "an infrastructure failure must not record a scientific outcome"
        )
