#!/usr/bin/env python3
"""Select development seeds through an outcome-blind Business Bench source gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

WORKFLOWS = [
    "freight-accrual-revision",
    "month-end-close",
    "payment-run",
    "payment-run-need-to-know",
]


def oracle_matrix_passes(summary_path: Path) -> bool:
    if not summary_path.is_file():
        return False
    rows = json.loads(summary_path.read_text(encoding="utf-8"))
    return (
        len(rows) == len(WORKFLOWS)
        and {row.get("task") for row in rows} == set(WORKFLOWS)
        and all(row.get("passed") is True and row.get("error") is None for row in rows)
    )


def select(
    root: Path,
    start_seed: int,
    count: int,
    max_candidates: int,
    label_prefix: str,
    output: Path,
) -> dict:
    runner = root / "bench" / "process_run.py"
    if not runner.is_file():
        raise ValueError("Business Bench process runner is missing")
    accepted = []
    attempts = []
    for seed in range(start_seed, start_seed + max_candidates):
        label = f"{label_prefix}-seed-{seed}"
        result_root = root / "results" / label
        if result_root.exists():
            raise ValueError(f"refusing to overwrite existing source-gate label: {label}")
        completed = subprocess.run(
            [
                sys.executable,
                str(runner),
                "--task",
                ",".join(WORKFLOWS),
                "--harness",
                "oracle",
                "--seed",
                str(seed),
                "--runs",
                "1",
                "--parallel",
                "1",
                "--label",
                label,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        passed = completed.returncode == 0 and oracle_matrix_passes(result_root / "summary.json")
        attempts.append(
            {
                "seed": seed,
                "accepted": passed,
                "return_code": completed.returncode,
                "label": label if result_root.exists() else None,
            }
        )
        if passed:
            accepted.append(seed)
        record = {
            "schema_version": 1,
            "rule": (
                f"first {count} integers from {start_seed} upward whose four generators "
                "and oracle references complete successfully"
            ),
            "workflows": WORKFLOWS,
            "selected_seeds": accepted,
            "attempts": attempts,
            "complete": len(accepted) == count,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if len(accepted) == count:
            return record
    raise RuntimeError(f"found only {len(accepted)} valid seeds among {max_candidates} candidates")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("business_bench_root", type=Path)
    parser.add_argument("--start-seed", type=int, default=71001)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=64)
    parser.add_argument("--label-prefix", default="anarres-finance-qualification-source-gate-v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    select(
        args.business_bench_root.resolve(),
        args.start_seed,
        args.count,
        args.max_candidates,
        args.label_prefix,
        args.output,
    )


if __name__ == "__main__":
    main()
