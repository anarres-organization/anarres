#!/usr/bin/env python3
"""Build an outcome-blind, parent-capped OMat24 measurement pool."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from audit_candidate_overlap import parse_atomic_number_spec, parse_reduced_formula, sha256

SALT = "anarres-mlip-measurement-pool-v1"


def source_family(source: str) -> str:
    if source.startswith("rattled-") and source.endswith("-subsampled"):
        return source.removesuffix("-subsampled")
    return source


def record_score(source: str, sid: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{SALT}|{source}|{sid}".encode()).digest(), "big")


def target_compositions(overlap_artifact: dict) -> set[tuple[tuple[str, int], ...]]:
    compositions = set()
    for target in overlap_artifact["targets"].values():
        formula = target["descriptor"].split("|", maxsplit=1)[0]
        compositions.add(parse_reduced_formula(formula))
    return compositions


def scan_source(arguments: tuple) -> dict:
    database_path, excluded_compositions, supported_numbers, capacity = arguments
    from ase.data import atomic_numbers
    from ase_db_backends.aselmdb import LMDBDatabase

    database = LMDBDatabase(str(database_path))
    source = database_path.parent.name
    family = source_family(source)
    heap = []
    excluded_target = 0
    excluded_support = 0
    for row_id in range(1, len(database) + 1):
        row = database.get(row_id)
        data = row.data
        composition = parse_reduced_formula(data["composition_reduced"])
        if composition in excluded_compositions:
            excluded_target += 1
            continue
        if any(atomic_numbers[element] not in supported_numbers for element, _ in composition):
            excluded_support += 1
            continue
        score = record_score(source, data["sid"])
        record = {
            "source": source,
            "source_family": family,
            "row_id": row_id,
            "sid": data["sid"],
            "parent_id": data["parent_id"],
            "composition_reduced": data["composition_reduced"],
            "prototype_label": data.get("prototype_label", ""),
            "parent_prototype_label": data.get("parent_prototype_label", ""),
            "natoms": int(row.natoms),
            "hash_score": f"{score:064x}",
        }
        item = (-score, data["sid"], row_id, record)
        if len(heap) < capacity:
            heapq.heappush(heap, item)
        elif score < -heap[0][0]:
            heapq.heapreplace(heap, item)
    return {
        "source": source,
        "source_family": family,
        "records": len(database),
        "excluded_target_composition": excluded_target,
        "excluded_unsupported_element": excluded_support,
        "candidates": [item[3] for item in heap],
    }


def build(
    overlap_path: Path,
    omat_train_root: Path,
    records_per_family: int,
    parent_cap: int,
    oversample_factor: int,
    supported_numbers: set[int],
    workers: int,
) -> tuple[dict, list[dict]]:
    overlap = json.loads(overlap_path.read_text(encoding="utf-8"))
    excluded_compositions = target_compositions(overlap)
    capacity = records_per_family * oversample_factor
    database_paths = sorted(omat_train_root.glob("*/train.aselmdb"))
    arguments = [
        (path, excluded_compositions, supported_numbers, capacity) for path in database_paths
    ]
    with ProcessPoolExecutor(max_workers=min(workers, len(arguments))) as executor:
        scans = list(executor.map(scan_source, arguments))

    by_family = defaultdict(list)
    for scan in scans:
        by_family[scan["source_family"]].extend(scan["candidates"])

    selected = []
    family_summaries = {}
    for family in sorted(by_family):
        rows = sorted(by_family[family], key=lambda row: row["hash_score"])
        parent_counts = Counter()
        family_selected = []
        for row in rows:
            if parent_counts[row["parent_id"]] >= parent_cap:
                continue
            parent_counts[row["parent_id"]] += 1
            family_selected.append(row)
            if len(family_selected) == records_per_family:
                break
        if len(family_selected) != records_per_family:
            raise RuntimeError(
                f"{family} produced {len(family_selected)} records; expected {records_per_family}"
            )
        selected.extend(family_selected)
        family_summaries[family] = {
            "records": len(family_selected),
            "atoms": sum(row["natoms"] for row in family_selected),
            "parents": len({row["parent_id"] for row in family_selected}),
            "source_records": dict(
                sorted(Counter(row["source"] for row in family_selected).items())
            ),
        }

    selected.sort(key=lambda row: (row["source_family"], row["hash_score"]))
    source_summaries = {
        scan["source"]: {
            "records": scan["records"],
            "excluded_target_composition": scan["excluded_target_composition"],
            "excluded_unsupported_element": scan["excluded_unsupported_element"],
        }
        for scan in sorted(scans, key=lambda row: row["source"])
    }
    summary = {
        "artifact": "anarres_mlip_measurement_pool_v1",
        "status": "complete",
        "selection": {
            "salt": SALT,
            "records_per_source_family": records_per_family,
            "maximum_records_per_parent": parent_cap,
            "oversample_factor": oversample_factor,
            "source_families": sorted(by_family),
            "uses_training_labels": False,
            "uses_target_outcomes": False,
        },
        "inputs": {
            "overlap_audit_sha256": sha256(overlap_path),
            "supported_atomic_numbers": sorted(supported_numbers),
        },
        "pool": {
            "records": len(selected),
            "atoms": sum(row["natoms"] for row in selected),
            "parents": len({row["parent_id"] for row in selected}),
            "source_families": family_summaries,
        },
        "source_audit": source_summaries,
    }
    return summary, selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlap-audit", type=Path, required=True)
    parser.add_argument("--omat-train-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--records-per-family", type=int, default=10_000)
    parser.add_argument("--parent-cap", type=int, default=4)
    parser.add_argument("--oversample-factor", type=int, default=4)
    parser.add_argument("--supported-atomic-numbers", default="1-83,89-94")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    summary, selected = build(
        args.overlap_audit,
        args.omat_train_root,
        args.records_per_family,
        args.parent_cap,
        args.oversample_factor,
        parse_atomic_number_spec(args.supported_atomic_numbers),
        args.workers,
    )
    digest = hashlib.sha256()
    with args.manifest.open("w", encoding="utf-8") as handle:
        for row in selected:
            line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            handle.write(line)
            digest.update(line.encode())
    summary["pool"]["manifest_sha256"] = digest.hexdigest()
    summary["pool"]["manifest_bytes"] = args.manifest.stat().st_size
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
