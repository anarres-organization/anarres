"""Qualification for the pinned Business Bench construction source."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

EXPECTED_REVISION = "0d09882b59a16f190feac09abc9331a733a6f96b"
EXPECTED_DESK_TASKS = 187
EXPECTED_BOOKKEEPING_TASKS = 36
EXPECTED_PROCESS_TASKS = 9
EXPECTED_WORKFLOWS = {
    "freight-accrual-revision",
    "month-end-close",
    "payment-run",
    "payment-run-need-to-know",
}
REQUIRED_RUNTIME_FILES = (
    "bench/process_grade.py",
    "bench/process_run.py",
    "bench/validate_process.py",
    "harnesses/contract.md",
)
REQUIRED_RUNTIME_DIRECTORIES = (
    "erp/bberp",
    "harnesses",
    "tasks/process",
)
REQUIRED_RUNTIME_PATHS = REQUIRED_RUNTIME_FILES + REQUIRED_RUNTIME_DIRECTORIES
REQUIRED_PROCESS_ASSETS = (
    "gen.py",
    "oracle.py",
    "policies.yaml",
    "projections.sql",
    "task.yaml",
)


class BusinessBenchSourceError(ValueError):
    """Raised when a Business Bench checkout does not match the frozen source."""


def checkout_revision(root: Path) -> str:
    """Return the exact Git revision of a local checkout."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise BusinessBenchSourceError(
            "native source is not a readable Business Bench Git checkout"
        ) from error
    return completed.stdout.strip()


def checkout_has_tracked_changes(root: Path) -> bool:
    """Return whether tracked source files differ from the pinned commit."""

    try:
        completed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise BusinessBenchSourceError(
            "native source is not a readable Business Bench Git checkout"
        ) from error
    if completed.returncode not in (0, 1):
        detail = completed.stderr.strip()
        raise BusinessBenchSourceError(
            "cannot verify the Business Bench tracked source state"
            + (f": {detail}" if detail else "")
        )
    return completed.returncode == 1


def _task_payload(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise BusinessBenchSourceError(f"cannot read task specification: {path}") from error
    if not isinstance(payload, dict):
        raise BusinessBenchSourceError(f"task specification is not a YAML object: {path}")
    return payload


def inventory(root: Path) -> dict[str, Any]:
    """Inventory task families and executable process-track components."""

    desk_specs = sorted((root / "tasks" / "desk").glob("*/task.yaml"))
    process_specs = sorted((root / "tasks" / "process").glob("*/task.yaml"))
    bookkeeping = sum(_task_payload(path).get("category") == "bookkeeping" for path in desk_specs)
    process_ids = {path.parent.name for path in process_specs}
    required_paths = {
        **{relative: (root / relative).is_file() for relative in REQUIRED_RUNTIME_FILES},
        **{relative: (root / relative).is_dir() for relative in REQUIRED_RUNTIME_DIRECTORIES},
    }
    missing_task_assets = sorted(
        str(path.relative_to(root))
        for process_id in process_ids
        for asset in REQUIRED_PROCESS_ASSETS
        if not (path := root / "tasks" / "process" / process_id / asset).is_file()
    )
    return {
        "desk_task_families": len(desk_specs),
        "bookkeeping_desk_task_families": bookkeeping,
        "process_task_families": len(process_specs),
        "qualified_workflows_present": sorted(EXPECTED_WORKFLOWS & process_ids),
        "qualified_workflows_missing": sorted(EXPECTED_WORKFLOWS - process_ids),
        "required_runtime_paths": required_paths,
        "missing_process_task_assets": missing_task_assets,
    }


def qualify_checkout(root: Path) -> dict[str, Any]:
    """Validate the exact outcome-blind construction checkout."""

    source = root.resolve()
    if not source.is_dir():
        raise BusinessBenchSourceError(f"native source is not a directory: {source}")
    revision = checkout_revision(source)
    if revision != EXPECTED_REVISION:
        raise BusinessBenchSourceError(
            f"Business Bench checkout is not at the pinned revision: {revision}"
        )
    if checkout_has_tracked_changes(source):
        raise BusinessBenchSourceError(
            "Business Bench tracked source files differ from the pinned revision"
        )
    result = inventory(source)
    if result["desk_task_families"] != EXPECTED_DESK_TASKS:
        raise BusinessBenchSourceError("unexpected desk-task inventory")
    if result["bookkeeping_desk_task_families"] != EXPECTED_BOOKKEEPING_TASKS:
        raise BusinessBenchSourceError("unexpected bookkeeping inventory")
    if result["process_task_families"] != EXPECTED_PROCESS_TASKS:
        raise BusinessBenchSourceError("unexpected process-task inventory")
    if result["qualified_workflows_missing"]:
        raise BusinessBenchSourceError(
            "qualified process workflows are missing: "
            + ", ".join(result["qualified_workflows_missing"])
        )
    missing_runtime = [
        path for path, present in result["required_runtime_paths"].items() if not present
    ]
    if missing_runtime:
        raise BusinessBenchSourceError(
            "Business Bench process runtime is incomplete: " + ", ".join(missing_runtime)
        )
    if result["missing_process_task_assets"]:
        raise BusinessBenchSourceError(
            "Business Bench process task assets are incomplete: "
            + ", ".join(result["missing_process_task_assets"])
        )
    return {"revision": revision, **result}
