"""Freeze outcome-blind candidate orderings for cyber qualification.

The output is an ordering, not an admission decision. Static licensing,
contamination, containment, oracle, no-op, and reset gates are applied in order;
the first 24 eligible entries from each declared stratum form a 48-task subset.
No replacement is allowed after warm-start measurements begin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SALT = "anarres-cyber-qualification-v1"


def rank(family: str, task_id: str, salt: str = SALT) -> str:
    payload = f"{salt}\0{family}\0{task_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def ordered_rows(family: str, task_ids: list[str]) -> list[dict[str, str | int]]:
    rows = [
        {"task_id": task_id, "rank_sha256": rank(family, task_id)}
        for task_id in sorted(set(task_ids))
    ]
    rows.sort(key=lambda row: (str(row["rank_sha256"]), str(row["task_id"])))
    for position, row in enumerate(rows, start=1):
        row["position"] = position
    return rows


def cyber_candidates(mask_map_path: Path) -> dict[str, list[dict[str, str | int]]]:
    mapping = json.loads(mask_map_path.read_text())
    if not isinstance(mapping, dict):
        raise ValueError("CyberGym mask map must be an object")
    result: dict[str, list[dict[str, str | int]]] = {}
    for source in ("arvo", "oss-fuzz"):
        task_ids = [task_id for task_id in mapping if task_id.startswith(f"{source}:")]
        if len(task_ids) < 24:
            raise ValueError(f"CyberGym stratum {source} has fewer than 24 tasks")
        result[source] = ordered_rows("cybergym", task_ids)
    return result


def secbench_candidates(projects_path: Path) -> dict[str, list[dict[str, str | int]]]:
    result: dict[str, list[dict[str, str | int]]] = {}
    for source in ("v8", "sm"):
        root = projects_path / source
        task_ids = [
            f"{source}:{path.name}"
            for path in root.iterdir()
            if path.is_dir() and (path / "meta.json").is_file()
        ]
        if len(task_ids) < 24:
            raise ValueError(f"SEC-Bench Pro stratum {source} has fewer than 24 tasks")
        result[source] = ordered_rows("sec_bench_pro", task_ids)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cybergym-mask-map", type=Path, required=True)
    parser.add_argument("--secbench-projects", type=Path, required=True)
    parser.add_argument("--cybergym-revision", required=True)
    parser.add_argument("--secbench-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    artifact = {
        "schema_version": "anarres.cyber-development-candidate-order.v1",
        "salt": SALT,
        "outcome_blind": True,
        "admission_rule": (
            "within each declared stratum, take the first 24 candidates that pass "
            "all pre-measurement gates; do not replace after measurement begins"
        ),
        "sources": {
            "cybergym": {
                "revision": arguments.cybergym_revision,
                "strata": cyber_candidates(arguments.cybergym_mask_map),
            },
            "sec_bench_pro": {
                "revision": arguments.secbench_revision,
                "strata": secbench_candidates(arguments.secbench_projects),
            },
        },
    }
    arguments.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
