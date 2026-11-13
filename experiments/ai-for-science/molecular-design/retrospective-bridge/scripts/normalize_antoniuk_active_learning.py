#!/usr/bin/env python3
"""Normalize the released Antoniuk et al. active-learning evidence.

The source CSV contains the initial 10k molecular dataset and the first three
active-learning acquisitions with DFT outcomes. The article's exact Table 2
provides the matched 500-call generation comparison. These are downstream
results and remain separate from Anarres pre-training profile coordinates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean
from typing import Any

from html_tables import parse_first_table

EXPECTED_CSV_SHA256 = "e93312e9c44bbe6901296691343178b4e8295533a7bcb8375aee0f420b874cfa"
EXPECTED_BATCHES = {"10k": 10206, "batch_1": 980, "batch_2": 2433, "batch_3": 48040}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percent_count(value: str) -> tuple[float | None, int | None, int | None]:
    if value == "-":
        return None, None, None
    match = re.fullmatch(r"([0-9.]+)% \(([0-9]+)/([0-9]+)\)", value)
    if not match:
        if value == "100%":
            return 100.0, None, None
        raise ValueError(f"unexpected percentage cell: {value!r}")
    return float(match.group(1)), int(match.group(2)), int(match.group(3))


def parse_table(path: Path) -> list[dict[str, Any]]:
    rows = parse_first_table(path)
    if len(rows) != 6 or len(rows[0]) != 8:
        raise ValueError(f"unexpected Table 2 shape: {[len(row) for row in rows]}")
    records = []
    for row in rows[1:]:
        if len(row) == 1:
            continue
        stable_pct, stable_count, stable_total = percent_count(row[5])
        top_pct, top_count, top_total = percent_count(row[6])
        sota_pct, sota_count, sota_total = percent_count(row[7])
        records.append(
            {
                "approach": row[0],
                "oracle_budget": None if row[0] == "Training Dataset Screening" else 500,
                "valid_fraction": float(row[1]),
                "top_dft_density_g_per_cc": float(row[2]),
                "top_dft_heat_of_formation_kcal_per_mol": float(row[3]),
                "top_multi_property_score": float(row[4]),
                "dft_stable_percent": stable_pct,
                "dft_stable_count": stable_count,
                "dft_stable_total": stable_total,
                "top_molecule_percent": top_pct,
                "top_molecule_count": top_count,
                "top_molecule_total": top_total,
                "sota_molecule_percent": sota_pct,
                "sota_molecule_count": sota_count,
                "sota_molecule_total": sota_total,
            }
        )
    if len(records) != 4:
        raise ValueError(f"expected four Table 2 records, found {len(records)}")
    return records


def parse_source_csv(path: Path) -> list[dict[str, Any]]:
    if sha256(path) != EXPECTED_CSV_SHA256:
        raise ValueError("supplementary CSV SHA-256 mismatch")
    batches: dict[str, list[dict[str, Any]]] = {name: [] for name in EXPECTED_BATCHES}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        expected = (
            "smiles",
            "batch_id",
            "DFT_density",
            "DFT_HoF",
            "is_DFT_success",
            "is_charge_balanced",
            "SA_score",
        )
        if tuple(reader.fieldnames or ()) != expected:
            raise ValueError(f"unexpected supplementary columns: {reader.fieldnames}")
        for row in reader:
            if row["batch_id"] not in batches:
                raise ValueError(f"unexpected batch: {row['batch_id']}")
            numeric = {
                key: float(row[key])
                for key in ("DFT_density", "DFT_HoF", "SA_score")
                if row[key] not in {"", "NA"}
            }
            if any(not math.isfinite(value) for value in numeric.values()):
                raise ValueError("non-finite DFT record")
            success = row["is_DFT_success"] == "True"
            if success and not {"DFT_density", "DFT_HoF"}.issubset(numeric):
                raise ValueError("a successful DFT record lacks its reported properties")
            batches[row["batch_id"]].append(
                {
                    "success": success,
                    "charge_balanced": row["is_charge_balanced"] == "True",
                    **numeric,
                }
            )
    if {name: len(rows) for name, rows in batches.items()} != EXPECTED_BATCHES:
        raise ValueError("unexpected batch support")
    records = []
    for name, rows in batches.items():
        successes = [row for row in rows if row["success"]]
        records.append(
            {
                "batch_id": name,
                "molecules": len(rows),
                "dft_successes": len(successes),
                "dft_success_fraction": len(successes) / len(rows),
                "charge_balanced_fraction": mean(row["charge_balanced"] for row in rows),
                "successful_density_mean": mean(row["DFT_density"] for row in successes),
                "successful_density_max": max(row["DFT_density"] for row in successes),
                "successful_heat_of_formation_mean": mean(row["DFT_HoF"] for row in successes),
                "successful_heat_of_formation_max": max(row["DFT_HoF"] for row in successes),
                "sa_score_mean": mean(row["SA_score"] for row in rows),
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table-html", type=Path, required=True)
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = {
        "schema_version": "anarres.molecular.antoniuk_active_learning_bridge.v1",
        "claim_boundary": (
            "This is a direct closed-loop active-learning intervention and a released "
            "acquisition history. It is not a prospective Anarres environment-selection "
            "test, and its outcomes remain outside pre-training profile coordinates."
        ),
        "source": {
            "article": (
                "Active learning enables generation of molecules that advance "
                "the known Pareto front"
            ),
            "doi": "10.1038/s41524-025-01924-8",
            "correction_doi": "10.1038/s41524-026-02039-4",
            "license": "CC BY 4.0",
            "table_url": "https://www.nature.com/articles/s41524-025-01924-8/tables/2",
            "table_html_sha256": sha256(args.table_html),
            "supplementary_csv_url": (
                "https://static-content.springer.com/esm/art%3A10.1038%2F"
                "s41524-025-01924-8/MediaObjects/41524_2025_1924_MOESM2_ESM.csv"
            ),
            "supplementary_csv_size_bytes": args.source_csv.stat().st_size,
            "supplementary_csv_sha256": sha256(args.source_csv),
        },
        "support": {
            "table_approaches": 4,
            "matched_generation_approaches": 3,
            "matched_dft_oracle_budget": 500,
            "released_molecule_records": sum(EXPECTED_BATCHES.values()),
            "released_batches": len(EXPECTED_BATCHES),
        },
        "table_2_records": parse_table(args.table_html),
        "released_batch_summaries": parse_source_csv(args.source_csv),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "output_sha256": sha256(args.output),
                "support": payload["support"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
