#!/usr/bin/env python3
"""Score a fixed molecular panel under the frozen qualifying-hit contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "attempt_id",
    "canonical_smiles",
    "infrastructure_status",
    "valid",
    "vina_affinity",
    "qed",
    "synthetic_accessibility",
    "chemical_filters_pass",
    "posebusters_all_valid",
    "strain_energy",
    "clash_score",
    "interaction_score",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = REQUIRED_FIELDS - set(record)
            if missing:
                raise ValueError(f"line {line_number} missing fields: {sorted(missing)}")
            attempt_id = str(record["attempt_id"])
            if attempt_id in seen:
                raise ValueError(f"duplicate attempt_id: {attempt_id}")
            seen.add(attempt_id)
            records.append(record)
    if not records:
        raise ValueError("endpoint record file is empty")
    return records


def score_record(record: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    infrastructure_valid = record["infrastructure_status"] == "ok"
    canonical_smiles = str(record["canonical_smiles"]).strip()
    numeric = {
        field: finite_number(record[field])
        for field in (
            "vina_affinity",
            "qed",
            "synthetic_accessibility",
            "strain_energy",
            "clash_score",
            "interaction_score",
        )
    }
    checks = {
        "infrastructure_valid": infrastructure_valid,
        "valid": record["valid"] is True and bool(canonical_smiles) and "." not in canonical_smiles,
        "vina_affinity": numeric["vina_affinity"] is not None
        and numeric["vina_affinity"] <= thresholds["vina_affinity_maximum"],
        "qed": numeric["qed"] is not None
        and numeric["qed"] > thresholds["qed_strictly_greater_than"],
        "synthetic_accessibility": numeric["synthetic_accessibility"] is not None
        and numeric["synthetic_accessibility"]
        < thresholds["synthetic_accessibility_strictly_less_than"],
        "chemical_filters": record["chemical_filters_pass"] is True,
        "posebusters": record["posebusters_all_valid"] is True,
        "strain_energy": numeric["strain_energy"] is not None
        and numeric["strain_energy"] <= thresholds["strain_energy_maximum"],
        "clash_score": numeric["clash_score"] is not None
        and numeric["clash_score"] <= thresholds["clash_score_maximum"],
        "interaction_score": numeric["interaction_score"] is not None
        and numeric["interaction_score"] >= thresholds["interaction_score_minimum"],
    }
    return {
        "attempt_id": str(record["attempt_id"]),
        "canonical_smiles": canonical_smiles,
        "checks": checks,
        "qualifies": all(checks.values()),
    }


def score(records_path: Path, thresholds_path: Path) -> dict[str, Any]:
    records = load_records(records_path)
    threshold_result = json.loads(thresholds_path.read_text())
    if threshold_result.get("contract") != "q07820-qualifying-hit-v1":
        raise ValueError("unexpected threshold contract")
    thresholds = threshold_result["instantiated_thresholds"]
    scored = [score_record(record, thresholds) for record in records]
    infrastructure_failures = [
        item for item in scored if not item["checks"]["infrastructure_valid"]
    ]
    if infrastructure_failures:
        status = "invalid_infrastructure_failure"
        unique_hits: set[str] = set()
        qualifying_attempts: int | None = None
        unique_qualifying_molecules: int | None = None
    else:
        status = "complete"
        unique_hits = {item["canonical_smiles"] for item in scored if item["qualifies"]}
        qualifying_attempts = sum(item["qualifies"] for item in scored)
        unique_qualifying_molecules = len(unique_hits)
    failed_gate_counts = Counter(
        gate for item in scored for gate, passed in item["checks"].items() if not passed
    )
    return {
        "schema_version": "1.0",
        "contract": threshold_result["contract"],
        "status": status,
        "inputs": {
            "records_sha256": sha256_file(records_path),
            "thresholds_sha256": sha256_file(thresholds_path),
        },
        "attempts": len(records),
        "infrastructure_failures": len(infrastructure_failures),
        "qualifying_attempts": qualifying_attempts,
        "unique_qualifying_molecules": unique_qualifying_molecules,
        "unique_qualifying_hit_rate": (
            len(unique_hits) / len(records) if status == "complete" else None
        ),
        "failed_gate_counts": dict(sorted(failed_gate_counts.items())),
        "scored_records": scored,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = score(args.records, args.thresholds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
