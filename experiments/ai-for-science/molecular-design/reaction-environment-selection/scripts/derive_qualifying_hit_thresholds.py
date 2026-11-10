#!/usr/bin/env python3
"""Derive frozen Q07820 endpoint thresholds from public reference controls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections.abc import Iterable
from pathlib import Path

MOLGENBENCH_RECORD = "https://doi.org/10.5281/zenodo.20233505"
MOLGENBENCH_ARCHIVE_SHA256 = "e52ab106f35c1376fe181a7172caaf11da86c2ba21f89af9236ddadc17cdfb43"
MOLGENBENCH_COMMIT = "f7b6cec1892cb575dc3adee4f5a71ee16ef04c39"
POSECHECK_COMMIT = "57a1938d3c77eec0f930cf9fdf3f640393e5898c"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: Iterable[float], probability: float) -> float:
    """Return a linearly interpolated empirical percentile."""
    ordered = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not ordered:
        raise ValueError("at least one finite value is required")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1]")
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def read_sdf_property(path: Path, property_name: str) -> tuple[list[float], int]:
    values: list[float] = []
    records = 0
    pending = False
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line == "$$$$":
                records += 1
                pending = False
                continue
            if pending:
                try:
                    value = float(line)
                except ValueError:
                    pending = False
                    continue
                if math.isfinite(value):
                    values.append(value)
                pending = False
                continue
            if line.startswith(">") and f"<{property_name}>" in line:
                pending = True
    return values, records


def read_csv_column(path: Path, column: str) -> tuple[list[float], int]:
    values: list[float] = []
    rows = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"missing column {column!r} in {path}")
        for row in reader:
            rows += 1
            raw = row.get(column)
            if raw is None or raw.strip() == "":
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if math.isfinite(value):
                values.append(value)
    return values, rows


def read_csv_boolean(path: Path, column: str) -> tuple[int, int, int]:
    passed = 0
    present = 0
    rows = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"missing column {column!r} in {path}")
        for row in reader:
            rows += 1
            raw = (row.get(column) or "").strip().lower()
            if raw not in {"true", "false"}:
                continue
            present += 1
            passed += raw == "true"
    return passed, present, rows


def input_artifact(
    path: Path,
    media_type: str,
    uri: str,
    license_name: str,
    producing_run: str,
) -> dict[str, object]:
    return {
        "uri": uri,
        "path": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "media_type": media_type,
        "license": license_name,
        "producing_run": producing_run,
    }


def summarize(values: list[float], rows: int) -> dict[str, float | int]:
    if not values:
        raise ValueError("reference metric contains no finite values")
    return {
        "rows": rows,
        "finite": len(values),
        "minimum": min(values),
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.5),
        "p75": percentile(values, 0.75),
        "maximum": max(values),
    }


def derive(
    contract: Path,
    docked_actives: Path,
    interactions: Path,
    strain: Path,
    clashes: Path,
) -> dict[str, object]:
    contract_data = json.loads(contract.read_text())
    if contract_data.get("contract") != "q07820-qualifying-hit-v1":
        raise ValueError("unexpected qualifying-hit contract")
    affinities, affinity_rows = read_sdf_property(docked_actives, "vina_dock")
    interaction_values, interaction_rows = read_csv_column(interactions, "InteractionScore")
    strain_values, strain_rows = read_csv_column(strain, "StrainEnergy")
    clash_values, clash_rows = read_csv_column(clashes, "ClashScore")
    posebusters_passed, posebusters_present, posebusters_rows = read_csv_boolean(
        strain, "PoseBusterAllValid"
    )
    summaries = {
        "vina_affinity": summarize(affinities, affinity_rows),
        "interaction_score": summarize(interaction_values, interaction_rows),
        "strain_energy": summarize(strain_values, strain_rows),
        "clash_score": summarize(clash_values, clash_rows),
        "posebusters_all_valid": {
            "rows": posebusters_rows,
            "present": posebusters_present,
            "passed": posebusters_passed,
            "pass_fraction": posebusters_passed / posebusters_present,
        },
    }
    return {
        "schema_version": "1.0",
        "contract": contract_data["contract"],
        "target_id": contract_data["target_id"],
        "status": "reference_thresholds_instantiated_before_trained_policy_evaluation",
        "source": {
            "dataset": "MolGenBench Version4",
            "record": MOLGENBENCH_RECORD,
            "archive_sha256": MOLGENBENCH_ARCHIVE_SHA256,
            "license": "CC BY 4.0",
            "evaluator_commit": MOLGENBENCH_COMMIT,
            "posecheck_commit": POSECHECK_COMMIT,
            "producing_run": "q07820-reference-pose-metrics-v1",
        },
        "inputs": {
            "contract": input_artifact(
                contract,
                "application/json",
                "release://molecular-design/QUALIFYING_HIT_CONTRACT_V1.json",
                "Apache-2.0",
                "q07820-qualifying-hit-contract-v1",
            ),
            "docked_reference_actives": input_artifact(
                docked_actives,
                "chemical/x-mdl-sdfile",
                f"{MOLGENBENCH_RECORD}#Q07820-reference-docked-actives",
                "CC BY 4.0",
                "MolGenBench-Version4",
            ),
            "reference_interactions": input_artifact(
                interactions,
                "text/csv",
                f"{MOLGENBENCH_RECORD}#Q07820-reference-interactions",
                "CC BY 4.0",
                "MolGenBench-Version4",
            ),
            "reference_strain": input_artifact(
                strain,
                "text/csv",
                "derived://q07820-reference-pose-metrics-v1",
                "CC BY 4.0",
                "q07820-reference-pose-metrics-v1",
            ),
            "reference_clashes": input_artifact(
                clashes,
                "text/csv",
                "derived://q07820-reference-pose-metrics-v1",
                "CC BY 4.0",
                "q07820-reference-pose-metrics-v1",
            ),
        },
        "reference_summaries": summaries,
        "instantiated_thresholds": {
            "vina_affinity_maximum": summaries["vina_affinity"]["median"],
            "qed_strictly_greater_than": 0.5,
            "synthetic_accessibility_strictly_less_than": 5.0,
            "strain_energy_maximum": summaries["strain_energy"]["p75"],
            "clash_score_maximum": summaries["clash_score"]["p75"],
            "interaction_score_minimum": summaries["interaction_score"]["median"],
            "all_chemical_filters_required": True,
            "all_posebusters_checks_required": True,
        },
        "candidate_or_trained_policy_outcomes_read": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--docked-actives", type=Path, required=True)
    parser.add_argument("--interactions", type=Path, required=True)
    parser.add_argument("--strain", type=Path, required=True)
    parser.add_argument("--clashes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = derive(
        args.contract,
        args.docked_actives,
        args.interactions,
        args.strain,
        args.clashes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
