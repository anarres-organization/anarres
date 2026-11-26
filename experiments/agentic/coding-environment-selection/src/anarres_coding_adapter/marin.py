"""Validation for Marin's released fixed-validation sweep record."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class MarinEvidenceError(ValueError):
    """Raised when a Marin evidence record violates its public contract."""


EXPECTED_COLUMNS = (
    "dataset",
    "recipe",
    "job",
    "attempt",
    "step",
    "pass_at_1",
    "passes",
    "total",
    "avg_score",
    "split_seed",
    "split_revision",
    "contaminated",
    "status",
)
ALLOWED_STATUSES = {
    "authoritative",
    "authoritative_policy_stop",
    "authoritative_user_stop",
    "discarded_by_gang_restart",
    "superseded_by_repaired_reeval",
}
AUTHORITATIVE_STATUSES = {
    "authoritative",
    "authoritative_policy_stop",
    "authoritative_user_stop",
}


def sha256(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(row: dict[str, str], field: str, number: int) -> int:
    try:
        value = int(row[field])
    except (KeyError, ValueError) as error:
        raise MarinEvidenceError(f"row {number}: {field} must be an integer") from error
    return value


def _number(row: dict[str, str], field: str, number: int) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise MarinEvidenceError(f"row {number}: {field} must be numeric") from error
    return value


def audit_fixed_validation(
    path: Path,
    *,
    expected_sha256: str,
    source_revision: str,
    source_license: str,
) -> dict[str, Any]:
    """Validate provenance, accounting, and comparison boundaries in the CSV."""

    if not path.is_file():
        raise MarinEvidenceError(f"fixed-validation CSV is missing: {path}")
    if len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256
    ):
        raise MarinEvidenceError(
            "expected SHA-256 must contain 64 lowercase hexadecimal characters"
        )
    if not source_revision.strip():
        raise MarinEvidenceError("source revision must be non-empty")
    if not source_license.strip():
        raise MarinEvidenceError("source license or usage terms must be recorded")
    observed_sha256 = sha256(path)
    if observed_sha256 != expected_sha256:
        raise MarinEvidenceError(
            f"fixed-validation digest mismatch: expected {expected_sha256}, found {observed_sha256}"
        )

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise MarinEvidenceError(
                "fixed-validation CSV columns do not match the pinned contract"
            )
        rows = list(reader)
    if not rows:
        raise MarinEvidenceError("fixed-validation CSV contains no rows")

    status_counts: Counter[str] = Counter()
    datasets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    identities: set[tuple[str, str, str, int, int, str]] = set()
    for number, row in enumerate(rows, start=2):
        for field in ("dataset", "recipe", "job", "split_revision", "status"):
            if not row[field].strip():
                raise MarinEvidenceError(f"row {number}: {field} must be non-empty")
        status = row["status"]
        if status not in ALLOWED_STATUSES:
            raise MarinEvidenceError(f"row {number}: unsupported status '{status}'")
        attempt = _integer(row, "attempt", number)
        step = _integer(row, "step", number)
        passes = _integer(row, "passes", number)
        total = _integer(row, "total", number)
        split_seed = _integer(row, "split_seed", number)
        pass_at_1 = _number(row, "pass_at_1", number)
        avg_score = _number(row, "avg_score", number)
        if min(attempt, step, passes, split_seed) < 0 or total <= 0 or passes > total:
            raise MarinEvidenceError(f"row {number}: invalid non-negative count or total")
        if not 0.0 <= pass_at_1 <= 1.0:
            raise MarinEvidenceError(f"row {number}: pass_at_1 lies outside [0, 1]")
        if not math.isfinite(avg_score):
            raise MarinEvidenceError(f"row {number}: avg_score must be finite")
        if abs(pass_at_1 - passes / total) > 1e-12:
            raise MarinEvidenceError(f"row {number}: pass_at_1 does not equal passes / total")
        if row["contaminated"] not in {"true", "false"}:
            raise MarinEvidenceError(f"row {number}: contaminated must be true or false")
        identity = (row["dataset"], row["recipe"], row["job"], attempt, step, status)
        if identity in identities:
            raise MarinEvidenceError(f"row {number}: duplicate checkpoint identity")
        identities.add(identity)
        status_counts[status] += 1
        datasets[row["dataset"]].append(
            {
                "recipe": row["recipe"],
                "split_seed": split_seed,
                "split_revision": row["split_revision"],
                "contaminated": row["contaminated"] == "true",
                "status": status,
            }
        )

    dataset_reports = {}
    for dataset, records in sorted(datasets.items()):
        authoritative = [record for record in records if record["status"] in AUTHORITATIVE_STATUSES]
        recipes = sorted({record["recipe"] for record in authoritative})
        split_contracts = sorted(
            {(record["split_seed"], record["split_revision"]) for record in authoritative}
        )
        contaminated_rows = sum(record["contaminated"] for record in authoritative)
        comparison_groups = []
        for seed, revision in split_contracts:
            group = [
                record
                for record in authoritative
                if record["split_seed"] == seed and record["split_revision"] == revision
            ]
            group_recipes = sorted({record["recipe"] for record in group})
            group_contaminated = sum(record["contaminated"] for record in group)
            comparison_groups.append(
                {
                    "seed": seed,
                    "revision": revision,
                    "rows": len(group),
                    "recipes": group_recipes,
                    "contaminated_rows": group_contaminated,
                    "qualified": len(group_recipes) >= 2 and group_contaminated == 0,
                }
            )
        dataset_reports[dataset] = {
            "rows": len(records),
            "authoritative_rows": len(authoritative),
            "recipes": recipes,
            "split_contracts": [
                {"seed": seed, "revision": revision} for seed, revision in split_contracts
            ],
            "contaminated_authoritative_rows": contaminated_rows,
            "comparison_groups": comparison_groups,
            "qualified_comparison_groups": sum(group["qualified"] for group in comparison_groups),
            "within_dataset_comparison_qualified": any(
                group["qualified"] for group in comparison_groups
            ),
            "all_authoritative_rows_share_one_split_contract": len(split_contracts) == 1,
        }

    return {
        "status": "qualified_evidence_record",
        "path": str(path),
        "sha256": observed_sha256,
        "source_revision": source_revision,
        "source_license": source_license,
        "rows": len(rows),
        "datasets": dataset_reports,
        "status_counts": dict(sorted(status_counts.items())),
        "cross_dataset_allocation_comparable": False,
        "comparison_boundary": (
            "Each dataset may support matched recipe comparisons under its own split contract. "
            "Different datasets do not share one held-out target and cannot be ranked as a single "
            "environment-allocation decision."
        ),
        "policy_probe_available": False,
        "training_started_by_audit": False,
    }
