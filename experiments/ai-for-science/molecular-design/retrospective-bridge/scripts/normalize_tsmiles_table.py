#!/usr/bin/env python3
"""Normalize the published JNK3 t-SMILES representation and augmentation panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from html_tables import parse_first_table


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_model(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"(.+)\[R([0-9]+)\]", value)
    if not match:
        raise ValueError(f"unexpected model label: {value!r}")
    return match.group(1), int(match.group(2))


def optional_float(value: str) -> float | None:
    return None if value in {"", "nan", "NaN", "N/A"} else float(value)


def parse_panel(path: Path) -> list[dict[str, Any]]:
    rows = parse_first_table(path)
    if len(rows) != 22 or len(rows[0]) != 7:
        raise ValueError(f"unexpected Table 2 shape: {[len(row) for row in rows]}")
    records = []
    for row in rows[1:]:
        model, rounds = parse_model(row[0])
        records.append(
            {
                "condition": model,
                "training_rounds": rounds,
                "valid_fraction": float(row[1]),
                "novelty_fraction": float(row[2]),
                "fcd": float(row[3]),
                "active_novel_fraction": float(row[4]),
                "fbt_novel": optional_float(row[5]),
                "fragment_novel": optional_float(row[6]),
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table-html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = parse_panel(args.table_html)
    payload = {
        "schema_version": "anarres.molecular.tsmiles_jnk3_bridge.v1",
        "claim_boundary": (
            "This published JNK3 panel changes molecular representation, training "
            "augmentation, transfer learning, and training duration. It audits data "
            "and representation dependence but is not a fixed-trainer environment "
            "comparison or a source of pre-training profile coordinates."
        ),
        "source": {
            "article": (
                "t-SMILES: a fragment-based molecular representation framework "
                "for de novo ligand design"
            ),
            "doi": "10.1038/s41467-024-49388-6",
            "license": "CC BY 4.0",
            "table_url": "https://www.nature.com/articles/s41467-024-49388-6/tables/2",
            "table_html_sha256": sha256(args.table_html),
        },
        "support": {
            "target": "JNK3",
            "published_conditions": len(records),
            "outcome_metrics": 6,
        },
        "records": records,
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
