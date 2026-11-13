#!/usr/bin/env python3
"""Normalize selected published Saturn source-data panels.

The architecture/augmentation panel is a direct component study reported as
ten-run mean and standard deviation. The five-target hit-ratio panel contains
the released ten-run values. Neither panel is promoted to a pre-training
environment coordinate.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any

from openpyxl import load_workbook


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean_sd(value: str) -> tuple[float, float]:
    parts = value.split("±")
    if len(parts) != 2:
        raise ValueError(f"expected mean±sd, received {value!r}")
    return float(parts[0]), float(parts[1])


def oracle_burden(value: str) -> tuple[float, float, int]:
    match = re.fullmatch(r"([0-9.]+)±([0-9.]+) \(([0-9]+)\)", value)
    if not match:
        raise ValueError(f"invalid oracle-burden cell: {value!r}")
    return float(match.group(1)), float(match.group(2)), int(match.group(3))


def architecture_panel(path: Path) -> list[dict[str, Any]]:
    ws = load_workbook(path, read_only=True, data_only=True)["Just Mamba"]
    records: list[dict[str, Any]] = []
    model: str | None = None
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(value is None for value in row):
            continue
        if row[0] is not None:
            model = str(row[0])
        if model is None or row[1] is None:
            raise ValueError("architecture row lacks model or augmentation rounds")
        yield_mean, yield_sd = mean_sd(str(row[2]))
        diversity_mean, diversity_sd = mean_sd(str(row[3]))
        scaffold_mean, scaffold_sd = mean_sd(str(row[4]))
        repeats_mean, repeats_sd = mean_sd(str(row[8]))
        ob1_mean, ob1_sd, ob1_success = oracle_burden(str(row[5]))
        ob10_mean, ob10_sd, ob10_success = oracle_burden(str(row[6]))
        ob100_mean, ob100_sd, ob100_success = oracle_burden(str(row[7]))
        records.append(
            {
                "study": "saturn_2026",
                "evidence_tier": "direct_component_intervention_published_aggregate",
                "panel": "architecture_by_augmentation_rounds",
                "model": model,
                "augmentation_rounds": int(row[1]),
                "oracle_budget": 1000,
                "replicates": 10,
                "yield_mean": yield_mean,
                "yield_sd": yield_sd,
                "internal_diversity_mean": diversity_mean,
                "internal_diversity_sd": diversity_sd,
                "scaffolds_mean": scaffold_mean,
                "scaffolds_sd": scaffold_sd,
                "repeats_mean": repeats_mean,
                "repeats_sd": repeats_sd,
                "oracle_burden_1_mean": ob1_mean,
                "oracle_burden_1_sd": ob1_sd,
                "oracle_burden_1_successes": ob1_success,
                "oracle_burden_10_mean": ob10_mean,
                "oracle_burden_10_sd": ob10_sd,
                "oracle_burden_10_successes": ob10_success,
                "oracle_burden_100_mean": ob100_mean,
                "oracle_burden_100_sd": ob100_sd,
                "oracle_burden_100_successes": ob100_success,
            }
        )
    if len(records) != 18:
        raise ValueError(f"expected 18 architecture rows, found {len(records)}")
    return records


def hit_ratio_panel(path: Path) -> list[dict[str, Any]]:
    ws = load_workbook(path, read_only=True, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    targets = tuple(str(value) for value in rows[0][1:])
    if targets != ("parp1", "fa7", "5ht1b", "braf", "jak2"):
        raise ValueError(f"unexpected targets: {targets}")
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        method = str(row[0])
        for target, raw in zip(targets, row[1:], strict=True):
            values = ast.literal_eval(str(raw))
            if not isinstance(values, list) or len(values) != 10:
                raise ValueError(f"expected ten hit-ratio values for {method}/{target}")
            for seed, value in enumerate(values):
                records.append(
                    {
                        "study": "saturn_2026",
                        "evidence_tier": "adjacent_endpoint_method_comparison",
                        "panel": "five_target_hit_ratio",
                        "method": method,
                        "target": target,
                        "seed": seed,
                        "oracle_budget": 1000,
                        "hit_ratio_percent": float(value),
                    }
                )
    if len(records) != 200:
        raise ValueError(f"expected 200 hit-ratio records, found {len(records)}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    architecture_path = args.source_dir / "source_data_extended1.xlsx"
    hit_ratio_path = args.source_dir / "source_data_table1.xlsx"
    architecture = architecture_panel(architecture_path)
    hit_ratios = hit_ratio_panel(hit_ratio_path)
    target_method_means: dict[str, dict[str, float]] = {}
    for target in sorted({row["target"] for row in hit_ratios}):
        target_method_means[target] = {}
        for method in sorted({row["method"] for row in hit_ratios}):
            values = [
                row["hit_ratio_percent"]
                for row in hit_ratios
                if row["target"] == target and row["method"] == method
            ]
            target_method_means[target][method] = mean(values)

    payload = {
        "schema_version": "anarres.molecular.saturn_bridge.v1",
        "claim_boundary": (
            "The architecture panel is a direct component intervention and the "
            "five-target panel is an endpoint method comparison. Neither is a "
            "prospective environment-selection result or a source of pre-training "
            "profile coordinates."
        ),
        "source": {
            "article": "Sample-efficient generative molecular design using memory manipulation",
            "doi": "10.1038/s42256-026-01200-4",
            "pmcid": "PMC13658037",
            "license": "CC BY 4.0",
            "files": {
                architecture_path.name: sha256(architecture_path),
                hit_ratio_path.name: sha256(hit_ratio_path),
            },
        },
        "support": {
            "architecture_conditions": len(architecture),
            "architecture_replicates_per_condition": 10,
            "hit_ratio_methods": 4,
            "hit_ratio_targets": 5,
            "hit_ratio_replicates_per_method_target": 10,
            "hit_ratio_records": len(hit_ratios),
        },
        "hit_ratio_method_means_by_target": target_method_means,
        "architecture_records": architecture,
        "hit_ratio_records": hit_ratios,
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
