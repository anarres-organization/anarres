#!/usr/bin/env python3
"""Build Vero's outcome-blind, repository-disjoint study split."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

SALT = "anarres-vero-repository-split-v1"
SPLITS = ("development", "qualification", "prospective")
QUOTAS = {
    "coq": {"development": 2, "qualification": 1, "prospective": 1},
    "dafny": {"development": 3, "qualification": 1, "prospective": 1},
    "python": {"development": 16, "qualification": 7, "prospective": 7},
    "verus": {"development": 2, "qualification": 1, "prospective": 1},
}


class SplitError(ValueError):
    """Raised when the source cannot produce the frozen split contract."""


def stable_key(*parts: str) -> str:
    return hashlib.sha256(":".join((SALT, *parts)).encode()).hexdigest()


def manifest_record(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    modules = [module for package in manifest["packages"] for module in package.get("modules", [])]
    return {
        "benchmark_id": manifest["benchmark_id"],
        "directory": path.parent.name,
        "source_language": manifest["source"]["language"],
        "source_repository": manifest["source"]["repo_url"],
        "source_revision": manifest["source"]["commit_hash"],
        "modules": len(modules),
        "apis": sum(len(module.get("apis", [])) for module in modules),
        "specifications": sum(len(module.get("specs", [])) for module in modules),
        "trusted_axioms": len(manifest.get("trusted_axioms", [])),
    }


def assign_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observed = Counter(record["source_language"] for record in records)
    expected = {language: sum(quota.values()) for language, quota in QUOTAS.items()}
    if dict(sorted(observed.items())) != expected:
        raise SplitError(f"source-language inventory differs from the split contract: {observed}")

    assigned: list[dict[str, Any]] = []
    for language, quotas in sorted(QUOTAS.items()):
        group = [record for record in records if record["source_language"] == language]
        total_specs = sum(record["specifications"] for record in group)
        targets = {split: total_specs * count / len(group) for split, count in quotas.items()}
        counts: Counter[str] = Counter()
        specs: Counter[str] = Counter()
        ordered = sorted(
            group,
            key=lambda record: (
                -record["specifications"],
                stable_key(record["benchmark_id"]),
            ),
        )
        for record in ordered:
            eligible = [split for split in SPLITS if counts[split] < quotas[split]]
            split = min(
                eligible,
                key=lambda candidate: (
                    (specs[candidate] + record["specifications"]) / targets[candidate],
                    counts[candidate] / quotas[candidate],
                    stable_key(record["benchmark_id"], candidate),
                ),
            )
            counts[split] += 1
            specs[split] += record["specifications"]
            assigned.append({**record, "split": split})

    identities = [record["benchmark_id"] for record in assigned]
    if len(identities) != len(set(identities)):
        raise SplitError("a repository appears more than once in the split")
    return sorted(assigned, key=lambda record: (record["split"], record["benchmark_id"]))


def build(source: Path, pin: dict[str, Any]) -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != pin["commit"]:
        raise SplitError(f"source revision mismatch: {revision}")
    records = [
        manifest_record(path) for path in sorted((source / "benchmarks").glob("*/manifest.json"))
    ]
    assigned = assign_records(records)
    summary = {
        split: {
            "repositories": sum(record["split"] == split for record in assigned),
            "modules": sum(record["modules"] for record in assigned if record["split"] == split),
            "apis": sum(record["apis"] for record in assigned if record["split"] == split),
            "specifications": sum(
                record["specifications"] for record in assigned if record["split"] == split
            ),
            "source_languages": dict(
                sorted(
                    Counter(
                        record["source_language"] for record in assigned if record["split"] == split
                    ).items()
                )
            ),
        }
        for split in SPLITS
    }
    return {
        "schema_version": "anarres.formal-verification-repository-split.v1",
        "source_id": pin["source_id"],
        "source_revision": revision,
        "selection_status": "frozen_before_policy_measurement",
        "selection_inputs": [
            "source_language",
            "specification_count",
            "benchmark_id_hash",
        ],
        "salt": SALT,
        "summary": summary,
        "repositories": assigned,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    report = build(args.source.resolve(), pin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("froze repository-disjoint Vero split before policy measurement")


if __name__ == "__main__":
    main()
