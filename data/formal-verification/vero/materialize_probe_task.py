#!/usr/bin/env python3
"""Materialize one frozen Vero development task for the Leanstral probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

MODES = {"proof", "codeproof"}
FORBIDDEN_NAMES = {
    ".agents",
    ".claude",
    ".codex",
    ".env",
    ".git",
    ".mcp.json",
    ".vibe",
    "AGENTS.md",
    "auth.json",
    "manifest.json",
    "upstream_source",
}


class MaterializationError(ValueError):
    """Raised when a task cannot be materialized under the frozen contract."""


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    result = hashlib.sha256()
    for directory, names, filenames in os.walk(root, followlinks=False):
        names.sort()
        filenames.sort()
        current = Path(directory)
        for name in [*names, *filenames]:
            path = current / name
            relative = path.relative_to(root).as_posix().encode("utf-8")
            result.update(len(relative).to_bytes(8, "big"))
            result.update(relative)
            if path.is_symlink():
                result.update(b"L")
                target = os.readlink(path).encode("utf-8")
                result.update(len(target).to_bytes(8, "big"))
                result.update(target)
            elif path.is_dir():
                result.update(b"D")
            elif path.is_file():
                result.update(b"F")
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        result.update(chunk)
            else:
                result.update(b"O")
    return result.hexdigest()


def validate_visible_tree(root: Path) -> dict[str, int]:
    if not (root / "INSTRUCTION.md").is_file():
        raise MaterializationError("materialized task lacks INSTRUCTION.md")
    files = 0
    symlinks = 0
    resolved_root = root.resolve()
    for path in root.rglob("*"):
        if path.name in FORBIDDEN_NAMES or path.name.startswith(".env."):
            raise MaterializationError(f"forbidden model-visible path: {path.name}")
        if path.is_symlink():
            symlinks += 1
            try:
                target = path.resolve(strict=True)
            except FileNotFoundError as error:
                raise MaterializationError(f"broken model-visible symlink: {path}") from error
            if not target.is_relative_to(resolved_root):
                raise MaterializationError(f"model-visible symlink escapes the task: {path}")
        elif path.is_file():
            files += 1
    for sidecar in root.glob("*/Proof_mode*"):
        if sidecar.exists():
            raise MaterializationError(f"reference proof sidecar remains visible: {sidecar}")
    return {"files": files, "symlinks": symlinks}


def verify_source(source: Path, pin: dict[str, Any]) -> None:
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != pin["commit"]:
        raise MaterializationError("Vero checkout disagrees with the source pin")


def selected_repository(
    panel: dict[str, Any], split: dict[str, Any], benchmark_id: str
) -> dict[str, Any]:
    selected = next(
        (record for record in panel["repositories"] if record["benchmark_id"] == benchmark_id),
        None,
    )
    if selected is None:
        raise MaterializationError("benchmark is outside the development lifecycle panel")
    frozen = next(
        (record for record in split["repositories"] if record["benchmark_id"] == benchmark_id),
        None,
    )
    if frozen is None or frozen["split"] != "development":
        raise MaterializationError("benchmark is outside the frozen development split")
    for field in ("directory", "source_language", "specifications"):
        if selected[field] != frozen[field]:
            raise MaterializationError(f"panel and split disagree on {field}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve(strict=True)
    if args.output.exists():
        raise MaterializationError("--output must not exist")
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    split = json.loads(args.split.read_text(encoding="utf-8"))
    panel = json.loads(args.panel.read_text(encoding="utf-8"))
    verify_source(source, pin)
    if split["source_revision"] != pin["commit"] or panel["source_id"] != pin["source_id"]:
        raise MaterializationError("source, split, and panel identities disagree")
    selected = selected_repository(panel, split, args.benchmark_id)
    benchmark = source / "benchmarks" / selected["directory"]
    if not benchmark.is_dir():
        raise MaterializationError("selected benchmark directory is missing")

    from vero.generation.sandbox import create_sandbox

    create_sandbox(
        benchmark,
        args.output,
        mode=args.mode,
        strip_manifest=True,
        previous_feedback=None,
        iteration_index=0,
        iteration_total=1,
        seed_artifact=None,
        chunk_minutes=None,
        source_context="lean",
    )
    counts = validate_visible_tree(args.output)
    receipt = {
        "schema_version": "anarres.formal-verification-task-materialization.v1",
        "source_id": pin["source_id"],
        "benchmark_id": args.benchmark_id,
        "source_language": selected["source_language"],
        "mode": args.mode,
        "specifications": selected["specifications"],
        "source_context": "lean",
        "split_sha256": file_digest(args.split),
        "panel_sha256": file_digest(args.panel),
        "task_tree_sha256": tree_digest(args.output),
        "instruction_sha256": file_digest(args.output / "INSTRUCTION.md"),
        **counts,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"materialized {args.benchmark_id} {args.mode} task")


if __name__ == "__main__":
    main()
