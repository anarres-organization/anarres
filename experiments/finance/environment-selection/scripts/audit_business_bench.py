#!/usr/bin/env python3
"""Audit a pinned Business Bench checkout without reading outcome directories."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

EXPECTED_REVISION = "0d09882b59a16f190feac09abc9331a733a6f96b"
EXPECTED_WORKFLOWS = {
    "freight-accrual-revision",
    "month-end-close",
    "payment-run",
    "payment-run-need-to-know",
}


def revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def inventory(root: Path) -> dict:
    desk_specs = sorted((root / "tasks" / "desk").glob("*/task.yaml"))
    process_specs = sorted((root / "tasks" / "process").glob("*/task.yaml"))
    bookkeeping = 0
    for path in desk_specs:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        bookkeeping += payload.get("category") == "bookkeeping"
    process_ids = {path.parent.name for path in process_specs}
    return {
        "desk_task_families": len(desk_specs),
        "bookkeeping_desk_task_families": bookkeeping,
        "process_task_families": len(process_specs),
        "qualified_workflows_present": sorted(EXPECTED_WORKFLOWS & process_ids),
        "qualified_workflows_missing": sorted(EXPECTED_WORKFLOWS - process_ids),
    }


def validate(root: Path) -> dict:
    if revision(root) != EXPECTED_REVISION:
        raise ValueError("Business Bench checkout is not at the pinned revision")
    result = inventory(root)
    if result["desk_task_families"] != 187:
        raise ValueError("unexpected desk-task inventory")
    if result["bookkeeping_desk_task_families"] != 36:
        raise ValueError("unexpected bookkeeping inventory")
    if result["process_task_families"] != 9:
        raise ValueError("unexpected process-task inventory")
    if result["qualified_workflows_missing"]:
        raise ValueError("a qualified workflow is missing")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    args = parser.parse_args()
    result = validate(args.checkout.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
