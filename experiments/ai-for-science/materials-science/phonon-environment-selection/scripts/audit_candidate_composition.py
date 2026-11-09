#!/usr/bin/env python3
"""Describe frozen candidate composition after prospective scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    manifest_rows = json.loads(args.training_manifest.read_text(encoding="utf-8"))
    training = {
        row["record_id"]: row for row in manifest_rows if row["role"] == "gradient_train"
    }
    measurement = {}
    with args.measurement.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                measurement[row["record_id"]] = row
    if set(training) != set(measurement):
        raise ValueError("Training manifest and starting-model measurement identities differ")

    source_targets = [float(row["min_frequency"]) for row in training.values()]
    source = {
        "records": len(training),
        "stable_fraction": sum(value > -0.1 for value in source_targets) / len(source_targets),
        "unique_formulas": len({row["formula_reduced"] for row in training.values()}),
    }
    candidates = []
    for candidate, budgets in sorted(freeze["candidates"].items()):
        for budget, specification in sorted(budgets.items(), key=lambda item: int(item[0])):
            identities = specification["record_ids"]
            if len(identities) != int(budget) or len(identities) != len(set(identities)):
                raise ValueError(f"Invalid frozen membership: {candidate} {budget}")
            rows = [training[record_id] for record_id in identities]
            measured = [measurement[record_id] for record_id in identities]
            targets = [float(row["min_frequency"]) for row in rows]
            signals = [float(row["singleton_objective_signal"]) for row in measured]
            formulas = [row["formula_reduced"] for row in rows]
            candidates.append(
                {
                    "candidate": candidate,
                    "budget_structures": int(budget),
                    "records": len(rows),
                    "stable_fraction": sum(value > -0.1 for value in targets) / len(targets),
                    "unique_formulas": len(set(formulas)),
                    "formula_unique_fraction": len(set(formulas)) / len(formulas),
                    "minimum_frequency_quantiles_thz": {
                        "q05": quantile(targets, 0.05),
                        "q25": quantile(targets, 0.25),
                        "q50": quantile(targets, 0.50),
                        "q75": quantile(targets, 0.75),
                        "q95": quantile(targets, 0.95),
                    },
                    "singleton_signal_mean": statistics.fmean(signals),
                    "singleton_signal_median": statistics.median(signals),
                    "atoms_mean": statistics.fmean(float(row["atoms"]) for row in measured),
                    "graph_edges_mean": statistics.fmean(
                        float(row["graph_edges"]) for row in measured
                    ),
                }
            )
    result = {
        "schema_version": "1.0",
        "status": "retrospective_composition_audit_after_external_scoring",
        "interpretation_scope": "descriptive candidate composition; not a prospective prediction",
        "freeze_sha256": freeze["freeze_sha256"],
        "training_manifest_file_sha256": sha256(args.training_manifest),
        "measurement_file_sha256": sha256(args.measurement),
        "source_pool": source,
        "candidates": candidates,
    }
    result["composition_audit_sha256"] = canonical_digest(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"composition_audit_sha256={result['composition_audit_sha256']}")


if __name__ == "__main__":
    main()
