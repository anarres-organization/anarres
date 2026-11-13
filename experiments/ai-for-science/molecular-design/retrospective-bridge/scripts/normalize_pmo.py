#!/usr/bin/env python3
"""Normalize the official PMO result archive into auditable panel records.

This is an adjacent finite-budget molecular-optimization bridge.  PMO methods
are not treated as training environments, and no PMO outcome is promoted to a
pre-training Anarres coordinate.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

METHODS = (
    "dog_ae",
    "dog_gen",
    "dst",
    "gflownet",
    "gflownet_al",
    "gp_bo",
    "graph_ga",
    "graph_mcts",
    "jt_vae_bo",
    "mars",
    "mimosa",
    "mol_pal",
    "moldqn",
    "pasithea",
    "reinvent",
    "reinvent_selfies",
    "screening",
    "selfies_ga",
    "selfies_lstm_hc",
    "selfies_vae_bo",
    "smiles_ga",
    "smiles_lstm_hc",
    "smiles_vae_bo",
    "stoned",
    "synnet",
)

TASKS = (
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

BUDGETS = (1000, 2500, 5000, 7500, 10000)
EXPECTED_ARCHIVE_MD5 = "5a9a1d477cd23747aac9e033f1e39c92"
EXPECTED_FILE_COUNT = len(METHODS) * len(TASKS) * 5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_identity(path: Path) -> tuple[str, str, str]:
    stem = path.stem
    if not stem.startswith("results_"):
        raise ValueError(f"unexpected PMO filename: {path.name}")
    body = stem.removeprefix("results_")
    candidates: list[tuple[int, str, str, str]] = []
    for method in METHODS:
        prefix = f"{method}_"
        if not body.startswith(prefix):
            continue
        rest = body[len(prefix) :]
        for task in TASKS:
            task_prefix = f"{task}_"
            if rest.startswith(task_prefix):
                seed = rest[len(task_prefix) :]
                if seed.isdigit():
                    candidates.append((len(method) + len(task), method, task, seed))
    if len(candidates) != 1:
        raise ValueError(f"could not uniquely parse {path.name}: {candidates}")
    _, method, task, seed = candidates[0]
    return method, task, seed


def load_trace(path: Path) -> list[tuple[int, int, float, str]]:
    with path.open() as handle:
        raw: Any = yaml.load(handle, Loader=yaml.CSafeLoader)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"expected a nonempty mapping in {path}")
    trace: list[tuple[int, int, float, str]] = []
    for source_order, (smiles, value) in enumerate(raw.items()):
        if not isinstance(smiles, str) or not smiles:
            raise ValueError(f"invalid molecule identity in {path}")
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError(f"invalid PMO value for {smiles!r} in {path}")
        score, oracle_index = value
        if not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            raise ValueError(f"invalid score for {smiles!r} in {path}")
        if not isinstance(oracle_index, int) or oracle_index < 0:
            raise ValueError(f"invalid oracle index for {smiles!r} in {path}")
        # Batched optimizers can assign one oracle index to several molecules.
        # Python's source implementation uses a stable sort on the index, so
        # source order must be retained within each batch.
        trace.append((oracle_index, source_order, float(score), smiles))
    trace.sort(key=lambda row: row[0])
    return trace


def top_auc(
    trace: list[tuple[int, int, float, str]], budget: int, top_n: int = 10, frequency: int = 100
) -> float:
    """Reproduce PMO's trapezoidal AUC Top-N on a budget-truncated trace."""
    prefix = [row for row in trace if row[0] <= budget]
    if not prefix:
        return 0.0
    area = 0.0
    previous = 0.0
    called = 0
    for index in range(frequency, min(len(prefix), budget), frequency):
        current = mean(sorted((score for _, _, score, _ in prefix[:index]), reverse=True)[:top_n])
        area += frequency * (current + previous) / 2.0
        previous = current
        called = index
    final = mean(sorted((score for _, _, score, _ in prefix), reverse=True)[:top_n])
    area += (len(prefix) - called) * (final + previous) / 2.0
    if len(prefix) < budget:
        area += (budget - len(prefix)) * final
    return area / budget


def normalize_path(path: Path) -> tuple[str, str, str, list[dict[str, Any]]]:
    method, task, seed = parse_identity(path)
    trace = load_trace(path)
    file_hash = sha256(path)
    records: list[dict[str, Any]] = []
    for budget in BUDGETS:
        prefix = [row for row in trace if row[0] <= budget]
        records.append(
            {
                "study": "pmo_2022",
                "evidence_tier": "adjacent_budgeted_optimization",
                "task": task,
                "method": method,
                "run_label": seed,
                "oracle_budget": budget,
                "observed_unique_molecules": len(prefix),
                "auc_top10": top_auc(trace, budget),
                "endpoint_top10": (
                    mean(sorted((x[2] for x in prefix), reverse=True)[:10]) if prefix else 0.0
                ),
                "source_file": path.name,
                "source_sha256": file_hash,
            }
        )
    return method, task, seed, records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    archive_md5 = md5(args.archive)
    if archive_md5 != EXPECTED_ARCHIVE_MD5:
        raise SystemExit(f"archive MD5 mismatch: {archive_md5}")

    paths = sorted(args.results_dir.glob("results_*.yaml"))
    if len(paths) != EXPECTED_FILE_COUNT:
        raise SystemExit(f"expected {EXPECTED_FILE_COUNT} result files, found {len(paths)}")

    support: dict[tuple[str, str], list[str]] = {}
    records: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for method, task, seed, path_records in pool.map(normalize_path, paths, chunksize=4):
            support.setdefault((method, task), []).append(seed)
            records.extend(path_records)
    records.sort(
        key=lambda row: (row["method"], row["task"], int(row["run_label"]), row["oracle_budget"])
    )

    bad_support = {
        f"{method}/{task}": sorted(seeds)
        for (method, task), seeds in support.items()
        if len(seeds) != 5 or len(set(seeds)) != 5
    }
    expected_panels = {(method, task) for method in METHODS for task in TASKS}
    missing_panels = sorted(f"{m}/{t}" for m, t in expected_panels - set(support))
    extra_panels = sorted(f"{m}/{t}" for m, t in set(support) - expected_panels)
    if missing_panels or extra_panels:
        raise SystemExit(
            json.dumps(
                {
                    "missing_panels": missing_panels,
                    "extra_panels": extra_panels,
                },
                indent=2,
            )
        )

    payload = {
        "schema_version": "anarres.molecular.pmo_bridge.v1",
        "claim_boundary": (
            "PMO methods are adjacent finite-budget molecular optimizers, not "
            "training environments. Outcomes remain retrospective result records "
            "and are not eligible as pre-training profile coordinates."
        ),
        "source": {
            "title": "Results for practival molecular optimization (PMO) benchmark",
            "figshare_article_id": 20123453,
            "doi": "10.6084/m9.figshare.20123453.v1",
            "download_url": "https://ndownloader.figshare.com/files/35994221",
            "license": "MIT",
            "archive_name": args.archive.name,
            "archive_size_bytes": args.archive.stat().st_size,
            "archive_md5": archive_md5,
            "archive_sha256": sha256(args.archive),
        },
        "metric_contract": {
            "primary": "AUC Top-10",
            "frequency": 100,
            "budgets": list(BUDGETS),
            "implementation": "Exact Python reproduction of mol_opt/main/optimizer.py:top_auc",
        },
        "support": {
            "methods": len(METHODS),
            "tasks": len(TASKS),
            "nominal_runs_per_method_task": 5,
            "minimum_runs_per_method_task": min(map(len, support.values())),
            "maximum_runs_per_method_task": max(map(len, support.values())),
            "support_anomalies": bad_support,
            "source_files": len(paths),
            "normalized_records": len(records),
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
