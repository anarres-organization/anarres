#!/usr/bin/env python3
"""Normalize the released InVirtuoGen replay/no-replay PMO ablation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any

EXPECTED_TASKS = (
    "albuterol_similarity",
    "amlodipine_mpo",
    "celecoxib_rediscovery",
    "deco_hop",
    "drd2",
    "fexofenadine_mpo",
    "gsk3b",
    "isomers_c7h8n2o2",
    "isomers_c9h10n2o2pf2cl",
    "jnk3",
    "median1",
    "median2",
    "mestranol_similarity",
    "osimertinib_mpo",
    "perindopril_mpo",
    "qed",
    "ranolazine_mpo",
    "scaffold_hop",
    "sitagliptin_mpo",
    "thiothixene_rediscovery",
    "troglitazone_rediscovery",
    "valsartan_smarts",
    "zaleplon_mpo",
)
EXPECTED_COLUMNS = ("timestamp", "best_score", "auc_top10", "auc_top100", "predicted_auc", "seed")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_arm(root: Path, expected_runs: int, arm: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    observed_tasks = {path.name for path in root.iterdir() if path.is_dir()}
    if observed_tasks != set(EXPECTED_TASKS):
        raise ValueError(
            json.dumps(
                {
                    "arm": arm,
                    "missing_tasks": sorted(set(EXPECTED_TASKS) - observed_tasks),
                    "extra_tasks": sorted(observed_tasks - set(EXPECTED_TASKS)),
                }
            )
        )
    for task in EXPECTED_TASKS:
        path = root / task / f"results_{task}.csv"
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
                raise ValueError(f"unexpected columns in {path}: {reader.fieldnames}")
            rows = list(reader)
        if len(rows) != expected_runs:
            raise ValueError(f"expected {expected_runs} rows in {path}, found {len(rows)}")
        seeds: set[int] = set()
        for row in rows:
            seed_value = float(row["seed"])
            if not seed_value.is_integer():
                raise ValueError(f"non-integral seed in {path}: {row['seed']}")
            seed = int(seed_value)
            if seed in seeds:
                raise ValueError(f"duplicate seed {seed} in {path}")
            seeds.add(seed)
            numeric = {}
            for key in ("best_score", "auc_top10", "auc_top100", "predicted_auc"):
                value = float(row[key])
                if not math.isfinite(value):
                    raise ValueError(f"non-finite {key} in {path}")
                numeric[key] = value
            if abs(numeric["auc_top10"] - numeric["predicted_auc"]) > 1e-12:
                raise ValueError(f"predicted_auc mismatch in {path}")
            records.append(
                {
                    "study": "invirtuogen_replay_ablation_2026",
                    "evidence_tier": "direct_replay_intervention",
                    "task": task,
                    "arm": arm,
                    "seed": seed,
                    "oracle_budget": 10000,
                    **numeric,
                    "timestamp": row["timestamp"],
                    "source_file": str(path.relative_to(root.parent)),
                    "source_sha256": sha256(path),
                }
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    target_root = args.repository / "results" / "target_property"
    replay = read_arm(target_root / "no_prescreen_3_runs", 3, "experience_replay_300")
    no_replay = read_arm(
        target_root / "no_prescreen_no_experience_replay", 1, "no_experience_replay"
    )

    replay_seed0 = {(r["task"], r["seed"]): r for r in replay if r["seed"] == 0}
    baseline_seed0 = {(r["task"], r["seed"]): r for r in no_replay}
    if replay_seed0.keys() != baseline_seed0.keys():
        raise ValueError("seed-0 replay and no-replay panels are not exactly matched")
    differences = [
        replay_seed0[key]["auc_top10"] - baseline_seed0[key]["auc_top10"]
        for key in sorted(replay_seed0)
    ]
    wins = sum(delta > 0 for delta in differences)
    losses = sum(delta < 0 for delta in differences)
    ties = len(differences) - wins - losses

    payload = {
        "schema_version": "anarres.molecular.invirtuo_replay_bridge.v1",
        "claim_boundary": (
            "This is a direct experience-replay mechanism intervention under a "
            "fixed PMO contract. It is not an environment-selection test and its "
            "outcomes are not eligible as pre-training profile coordinates."
        ),
        "source": {
            "repository": "https://github.com/invirtuolabs/InVirtuoGen_results",
            "repository_commit": "b50bb3ae2bdcb9df581f0b219d79cf14b05d0fbb",
            "license": "MIT",
        },
        "contract": {
            "oracle_budget": 10000,
            "replay_size": 300,
            "comparison": "seed-0 experience replay versus seed-0 no replay",
            "primary_metric": "AUC Top-10",
        },
        "support": {
            "tasks": len(EXPECTED_TASKS),
            "replay_runs_per_task": 3,
            "no_replay_runs_per_task": 1,
            "records": len(replay) + len(no_replay),
            "matched_seed0_pairs": len(differences),
        },
        "matched_seed0_summary": {
            "replay_wins": wins,
            "no_replay_wins": losses,
            "ties": ties,
            "mean_auc_top10_difference": mean(differences),
            "median_auc_top10_difference": median(differences),
        },
        "records": replay + no_replay,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "output_sha256": sha256(args.output),
                "support": payload["support"],
                "matched_seed0_summary": payload["matched_seed0_summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
