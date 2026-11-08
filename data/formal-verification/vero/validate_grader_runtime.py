#!/usr/bin/env python3
"""Verify the qualified Lean grader before a model attempt begins."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


class GraderRuntimeError(RuntimeError):
    """Raised when the qualified grader cannot run from the materialized task."""


def version(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    rendered = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise GraderRuntimeError(
            f"{' '.join(command)} failed with exit code {result.returncode}: {rendered}"
        )
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise GraderRuntimeError("--output already exists")

    lean = version(["lean", "--version"])
    lake = version(["lake", "--version"])
    if "Lean (version 4.29.1" not in lean:
        raise GraderRuntimeError("grader does not provide the pinned Lean 4.29.1 toolchain")
    if "Lake version 5.0.0" not in lake:
        raise GraderRuntimeError("grader does not provide the Lake version paired with Lean 4.29.1")

    receipt = {
        "schema_version": "anarres.formal-verification-grader-runtime.v1",
        "status": "qualified_before_model_attempt",
        "checked_at": datetime.now(UTC).isoformat(),
        "working_directory": str(Path.cwd()),
        "lean_version": lean,
        "lake_version": lake,
    }
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
