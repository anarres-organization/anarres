"""Helpers for emitting environment-profile inputs from domain adapters.

Domain adapters own scientific measurement. This module only assembles the
versioned interchange record consumed by the native Anarres CLI.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROFILE_INPUT_SCHEMA = "anarres.environment-profile-input.v1"


class MissingEvidenceError(ValueError):
    """Raised when an adapter cannot support a profile from its native record."""


def coordinate(
    *,
    name: str,
    definition_uri: str,
    definition_revision: str,
    role: str,
    value: float,
    unit: str,
    direction: str,
    estimator: str,
    sample_count: int,
    uncertainty: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one coordinate without interpreting its scientific meaning."""

    result: dict[str, Any] = {
        "name": _required_text("name", name),
        "definition": {
            "uri": _required_text("definition_uri", definition_uri),
            "revision": _required_text("definition_revision", definition_revision),
        },
        "role": _required_text("role", role),
        "value": _finite_number("value", value),
        "unit": _required_text("unit", unit),
        "direction": _required_text("direction", direction),
        "estimator": _required_text("estimator", estimator),
        "sample_count": _positive_integer("sample_count", sample_count),
    }
    if uncertainty is not None:
        result["uncertainty"] = dict(uncertainty)
    return result


def qualification_check(
    *,
    check_id: str,
    category: str,
    status: str,
    severity: str,
    summary: str,
) -> dict[str, str]:
    """Build one qualification result while preserving unknown and failure states."""

    return {
        "check_id": _required_text("check_id", check_id),
        "category": _required_text("category", category),
        "status": _required_text("status", status),
        "severity": _required_text("severity", severity),
        "summary": _required_text("summary", summary),
    }


def local_artifact(
    *,
    role: str,
    path: Path,
    uri: str,
    media_type: str,
    license_id: str,
    producing_run: str | None = None,
) -> dict[str, Any]:
    """Reference an existing native artifact by its exact bytes."""

    if not path.is_file():
        raise MissingEvidenceError(f"native artifact does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    reference: dict[str, Any] = {
        "uri": _required_text("uri", uri),
        "sha256": f"sha256:{digest.hexdigest()}",
        "media_type": _required_text("media_type", media_type),
        "size_bytes": path.stat().st_size,
        "license": _required_text("license_id", license_id),
    }
    if producing_run is not None:
        reference["producing_run"] = _required_text("producing_run", producing_run)
    return {"role": _required_text("role", role), "reference": reference}


def build_profile_input(
    *,
    environment_id: str,
    domain: str,
    subject: Mapping[str, str],
    producer: Mapping[str, str],
    source: Mapping[str, str],
    measurement_contract: Mapping[str, Any],
    qualification_checks: Sequence[Mapping[str, Any]],
    coordinates: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]] = (),
    attributes: Mapping[str, str | int | float | bool] | None = None,
) -> dict[str, Any]:
    """Assemble a profile input from measurements owned by a domain adapter.

    At least one coordinate and one qualification check are required. The
    native CLI performs the authoritative schema and compatibility validation.
    """

    if not coordinates:
        raise MissingEvidenceError(
            "the native record contains no profile coordinates; do not infer them from outcomes"
        )
    if not qualification_checks:
        raise MissingEvidenceError("the native record contains no qualification evidence")
    return {
        "schema_version": PROFILE_INPUT_SCHEMA,
        "environment_id": _required_text("environment_id", environment_id),
        "domain": _required_text("domain", domain),
        "subject": dict(subject),
        "producer": dict(producer),
        "source": dict(source),
        "measurement_contract": dict(measurement_contract),
        "qualification_checks": [dict(check) for check in qualification_checks],
        "coordinates": [dict(item) for item in coordinates],
        "artifacts": [dict(artifact) for artifact in artifacts],
        "attributes": dict(attributes or {}),
    }


def write_profile_input(path: Path, profile: Mapping[str, Any], *, force: bool = False) -> None:
    """Write a deterministic profile input atomically without silent replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise FileExistsError(path)
    payload = json.dumps(profile, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if force:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise FileExistsError(path) from None
            temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _finite_number(name: str, value: float) -> float:
    number = float(value)
    if not (float("-inf") < number < float("inf")):
        raise ValueError(f"{name} must be finite")
    return number
