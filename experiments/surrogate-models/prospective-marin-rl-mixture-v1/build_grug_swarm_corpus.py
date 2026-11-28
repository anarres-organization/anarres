#!/usr/bin/env python3
"""Build a lineage-safe, multi-target corpus from the pinned Grug mixture swarm."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "GRUG_SWARM_SOURCE.json"
CELLS = HERE / "GRUG_SWARM_CELLS.json"
INPUTS = HERE / "GRUG_SWARM_INPUTS.jsonl.gz"
LABELS = HERE / "GRUG_SWARM_PROTECTED_LABELS.jsonl.gz"
MANIFEST = HERE / "GRUG_SWARM_CORPUS.json"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def gzip_bytes(value: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as stream:
        stream.write(value)
    return output.getvalue()


def require_pyarrow():
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise SystemExit(
            "pyarrow is required only to rebuild the pinned source extraction"
        ) from error
    return parquet


def check_source_files(source_dir: Path, source: dict[str, Any]) -> dict[str, Path]:
    paths = {name: source_dir / name for name in source["files"]}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise ValueError("missing pinned source files: " + ", ".join(missing))
    mismatched = [name for name, path in paths.items() if digest(path) != source["files"][name]]
    if mismatched:
        raise ValueError("source digest mismatch: " + ", ".join(mismatched))
    return paths


def lineage_key(phase0: list[float], phase1: list[float]) -> str:
    payload = canonical({"phase0": phase0, "phase1": phase1}).encode()
    return "mixture-" + digest_bytes(payload)[:24]


def record_key(observation_id: str) -> str:
    return "run-" + digest_bytes(observation_id.encode())[:24]


def build(source_dir: Path) -> dict[Path, bytes]:
    parquet = require_pyarrow()
    source = json.loads(SOURCE.read_text())
    paths = check_source_files(source_dir, source)

    buckets_rows = parquet.read_table(paths["buckets.parquet"]).to_pylist()
    swarm_rows = parquet.read_table(paths["swarm.parquet"]).to_pylist()
    observations = parquet.read_table(paths["observations.parquet"]).to_pylist()
    if len(buckets_rows) != 1 or len(swarm_rows) != 1:
        raise ValueError("expected one bucket contract and one swarm contract")
    bucket = buckets_rows[0]
    swarm = swarm_rows[0]
    shared = source["shared_contract"]
    for field in (
        "swarm_id",
        "training_recipe",
        "tokenizer",
        "evaluation_suite",
        "model_active_parameters",
        "model_total_parameters",
        "physical_training_tokens",
        "simulated_training_tokens",
    ):
        if swarm[field] != shared[field]:
            raise ValueError(f"swarm contract mismatch: {field}")
    if swarm["phase_budgets"] != shared["phase_budgets"]:
        raise ValueError("swarm phase budgets changed")

    cells = bucket["cells"]
    cell_ids = [row["cell"] for row in cells]
    if len(cell_ids) != 200 or len(set(cell_ids)) != 200:
        raise ValueError("expected 200 unique domain-by-quality cells")

    capability_targets = sorted(observations[0]["grouped_bpb"])
    training_evaluation_targets = sorted(observations[0]["training_eval_metrics"])
    if len(capability_targets) != 54:
        raise ValueError("expected 54 grouped evaluation targets")
    if len(training_evaluation_targets) != 108:
        raise ValueError("expected 108 held-out training-evaluation targets")

    input_rows = []
    label_rows = []
    lineage_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    for row in observations:
        if row["swarm_id"] != shared["swarm_id"] or "from10pct" not in row["run_name"]:
            raise ValueError("observation is outside the shared from-10-percent swarm")
        phase0 = [row["phase0_weights"][cell] for cell in cell_ids]
        phase1 = [row["phase1_weights"][cell] for cell in cell_ids]
        if not all(math.isfinite(value) for value in phase0 + phase1):
            raise ValueError("non-finite mixture weight")
        if abs(sum(phase0) - 1.0) > 1e-9 or abs(sum(phase1) - 1.0) > 1e-9:
            raise ValueError("mixture weights do not sum to one")
        if set(row["grouped_bpb"]) != set(capability_targets):
            raise ValueError("evaluation target set changed")
        if set(row["training_eval_metrics"]) != set(training_evaluation_targets):
            raise ValueError("training-evaluation target set changed")
        if not all(
            math.isfinite(value)
            for value in list(row["grouped_bpb"].values())
            + list(row["training_eval_metrics"].values())
        ):
            raise ValueError("non-finite evaluation target")

        lineage = lineage_key(phase0, phase1)
        key = record_key(row["observation_id"])
        lineage_counts[lineage] += 1
        group_counts[row["group"]] += 1
        input_rows.append(
            {
                "record_key": key,
                "lineage_key": lineage,
                "design_family": row["group"],
                "run_name": row["run_name"],
                "prediction_time": {
                    "phase0_cell_weights": phase0,
                    "phase1_cell_weights": phase1,
                    "phase_budgets": shared["phase_budgets"],
                    "model_active_parameters": shared["model_active_parameters"],
                    "model_total_parameters": shared["model_total_parameters"],
                    "physical_training_tokens": shared["physical_training_tokens"],
                },
            }
        )
        label_rows.append(
            {
                "record_key": key,
                "lineage_key": lineage,
                "outcomes": [
                    {
                        "family": "capability_log_probability",
                        "metric": "grouped_bpb/" + name,
                        "value": row["grouped_bpb"][name],
                        "lower_is_better": True,
                    }
                    for name in capability_targets
                ]
                + [
                    {
                        "family": "held_out_loss_or_bpb",
                        "metric": name,
                        "value": row["training_eval_metrics"][name],
                        "lower_is_better": True,
                    }
                    for name in training_evaluation_targets
                ],
            }
        )

    input_rows.sort(key=lambda row: row["record_key"])
    label_rows.sort(key=lambda row: row["record_key"])
    cells_document = {
        "artifact": "anarres_grug_swarm_cell_vocabulary_v1",
        "quality_order": bucket["quality_order"],
        "bucket_semantics": bucket["bucket_semantics"],
        "source_store_artifact": bucket["source_store_artifact"],
        "tokenizer": bucket["tokenizer"],
        "cells": cells,
    }
    cells_bytes = (json.dumps(cells_document, indent=2, sort_keys=True) + "\n").encode()
    inputs_raw = ("\n".join(canonical(row) for row in input_rows) + "\n").encode()
    labels_raw = ("\n".join(canonical(row) for row in label_rows) + "\n").encode()
    inputs_bytes = gzip_bytes(inputs_raw)
    labels_bytes = gzip_bytes(labels_raw)
    manifest = {
        "artifact": "anarres_grug_swarm_multi_target_corpus_v1",
        "status": "retrospective development corpus; not a prospective result",
        "source": {
            "path": SOURCE.name,
            "sha256": digest(SOURCE),
            "dataset": source["dataset"],
            "revision": source["revision"],
            "remote_path": source["path"],
            "files": source["files"],
        },
        "summary": {
            "trained_runs": len(input_rows),
            "candidate_lineages": len(lineage_counts),
            "replicated_lineages": sum(count > 1 for count in lineage_counts.values()),
            "design_families": dict(sorted(group_counts.items())),
            "mixture_cells_per_phase": len(cell_ids),
            "phases": 2,
            "protected_targets_per_run": (
                len(capability_targets) + len(training_evaluation_targets)
            ),
        },
        "artifacts": {
            "cell_vocabulary": {
                "path": CELLS.name,
                "sha256": digest_bytes(cells_bytes),
            },
            "inputs": {
                "path": INPUTS.name,
                "rows": len(input_rows),
                "compression": "gzip with mtime zero",
                "sha256": digest_bytes(inputs_bytes),
                "uncompressed_sha256": digest_bytes(inputs_raw),
            },
            "protected_labels": {
                "path": LABELS.name,
                "rows": len(label_rows),
                "compression": "gzip with mtime zero",
                "sha256": digest_bytes(labels_bytes),
                "uncompressed_sha256": digest_bytes(labels_raw),
            },
        },
        "evaluation_contract": {
            "independent_unit": "one trained continuation",
            "split_unit": "candidate lineage",
            "required_holdout": "entire candidate lineages and declared design families",
            "target_families": {
                "capability_log_probability": capability_targets,
                "held_out_loss_or_bpb": training_evaluation_targets,
            },
            "aggregation": "score every target separately before any declared aggregate",
            "replicates": "runs with identical two-phase weights remain in the same fold",
        },
        "boundaries": {
            "scope": "one model, one starting point, one budget, and one pretraining-mixture study",
            "selection": (
                "the swarm helped select the published mixture, so the corpus is "
                "development evidence"
            ),
            "transfer": "this corpus does not establish post-training or cross-scale transfer",
            "leakage": "outcomes are stored separately from prediction-time mixture inputs",
            "mochi": "no Mochi outcome is present",
        },
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    return {
        CELLS: cells_bytes,
        INPUTS: inputs_bytes,
        LABELS: labels_bytes,
        MANIFEST: manifest_bytes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build(args.source_dir)
    if args.check:
        stale = [
            path
            for path, content in expected.items()
            if not path.exists() or path.read_bytes() != content
        ]
        if stale:
            raise SystemExit("stale Grug swarm corpus: " + ", ".join(map(str, stale)))
        return
    for path, content in expected.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
