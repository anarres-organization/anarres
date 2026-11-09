#!/usr/bin/env python3
"""Build matched budget-resolved selector panels from Bi and Elena (2026)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

SOURCE_ID = "bi_elena_2026_budget_crossover"
SELECTORS = {
    "Random": {
        "uses_structural_coverage": 0,
        "uses_learned_embedding": 0,
        "uses_response_disagreement": 0,
        "requires_full_data_reference": 0,
    },
    "FPS/DPP": {
        "uses_structural_coverage": 1,
        "uses_learned_embedding": 1,
        "uses_response_disagreement": 0,
        "requires_full_data_reference": 0,
    },
    "QUESTS-MSC": {
        "uses_structural_coverage": 1,
        "uses_learned_embedding": 0,
        "uses_response_disagreement": 0,
        "requires_full_data_reference": 0,
    },
    "Response witness": {
        "uses_structural_coverage": 0,
        "uses_learned_embedding": 0,
        "uses_response_disagreement": 1,
        "requires_full_data_reference": 1,
    },
    "Response repair": {
        "uses_structural_coverage": 1,
        "uses_learned_embedding": 1,
        "uses_response_disagreement": 1,
        "requires_full_data_reference": 1,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reconstruct(source_csv: Path) -> dict:
    by_panel: dict[str, list[dict]] = defaultdict(list)
    with source_csv.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            selector = row["selector"]
            if selector not in SELECTORS:
                raise ValueError(f"unknown selector: {selector}")
            budget = float(row["budget_fraction"])
            dataset = row["dataset"]
            endpoint = row["endpoint"]
            panel_id = f"{SOURCE_ID}:{dataset}:budget_{budget:g}:{endpoint}"
            by_panel[panel_id].append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "dataset": dataset,
                    "retained_budget_fraction": budget,
                    "endpoint": endpoint,
                    "selector": selector,
                    "pre_outcome_measurements": SELECTORS[selector]
                    | {
                        "retained_budget_fraction": budget,
                        "response_budget_interaction": budget
                        * SELECTORS[selector]["uses_response_disagreement"],
                    },
                    "outcome": {
                        "absolute_gap_from_full_data_pct": float(row["gap_pct"]),
                        "seed_aggregation": row["seed_aggregation"],
                    },
                }
            )

    if len(by_panel) != 24 or any(len(arms) != 5 for arms in by_panel.values()):
        raise ValueError("expected 24 panels with five selectors each")
    arms = []
    for panel_arms in by_panel.values():
        values = [arm["outcome"]["absolute_gap_from_full_data_pct"] for arm in panel_arms]
        best, worst = min(values), max(values)
        span = worst - best
        for arm in panel_arms:
            value = arm["outcome"]["absolute_gap_from_full_data_pct"]
            arm["derived"] = {
                "native_utility": -value,
                "panel_normalized_utility": 1.0 if span == 0 else (worst - value) / span,
                "panel_normalized_regret": 0.0 if span == 0 else (value - best) / span,
            }
            arms.append(arm)
    arms.sort(
        key=lambda arm: (
            arm["dataset"],
            arm["retained_budget_fraction"],
            arm["endpoint"],
            arm["selector"],
        )
    )
    return {
        "artifact": "bi_elena_2026_budget_crossover_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(by_panel),
        "arm_count": len(arms),
        "primary_outcome": "absolute percentage gap from the paired full-data force-error endpoint",
        "normalization": (
            "within dataset, retained-data budget, and force endpoint; lower absolute gap maps "
            "to higher utility"
        ),
        "source_artifact": {
            "concept_doi": "10.5281/zenodo.22263567",
            "record_id": 22263568,
            "release_version": "2.3.0",
            "archive_name": "DD_Zenodo_v2.3.0_2026-09-05.zip",
            "archive_md5": "0676e1f69c65db6eec57a82153c27072",
            "archive_sha256": "0adf688b6a92da7922b0e0e6b24a65e0a1fe3e842e890c9c5cb427e7a14eb880",
            "source_csv_relative_path": "data/si/figS6_budget_sensitivity.csv",
            "source_csv_sha256": sha256(source_csv),
        },
        "interpretation_boundary": [
            (
                "The response witness is a retrospective scientific comparator that requires a "
                "full-data reference model."
            ),
            (
                "Five-seed means are available for every arm; individual seeds are released only "
                "for selected contrasts."
            ),
            (
                "Four force endpoints share held-out structures and are repeated views of two "
                "dataset-level contexts."
            ),
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = reconstruct(args.source_csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
