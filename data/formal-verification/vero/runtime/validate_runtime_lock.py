#!/usr/bin/env python3
"""Validate the pinned Vero task-runtime inputs and build state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class RuntimeLockError(ValueError):
    """Raised when the Vero runtime lock is incomplete or inconsistent."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(
    lock: dict[str, Any],
    *,
    lock_path: Path,
    panel_path: Path,
    source_pin_path: Path,
) -> None:
    runtime_dir = lock_path.parent
    dockerfile = runtime_dir / lock["dockerfile"]
    if digest(dockerfile) != lock["dockerfile_sha256"]:
        raise RuntimeLockError("Dockerfile hash disagrees with the runtime lock")
    if digest(panel_path) != lock["development_panel_sha256"]:
        raise RuntimeLockError("development-panel hash disagrees with the runtime lock")

    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    source_pin = json.loads(source_pin_path.read_text(encoding="utf-8"))
    if (
        panel["source_id"] != lock["vero_source_id"]
        or source_pin["source_id"] != lock["vero_source_id"]
    ):
        raise RuntimeLockError("Vero source identity disagrees with the runtime lock")
    if lock["lean_toolchain"] != f"leanprover/lean4:v{source_pin['lean_version']}":
        raise RuntimeLockError("Lean toolchain disagrees with the qualified Vero runtime")

    if not lock["base_image"]["manifest_digest"].startswith("sha256:"):
        raise RuntimeLockError("base image must be pinned by digest")
    if len(lock["elan"]["sha256"]) != 64:
        raise RuntimeLockError("elan asset SHA-256 is malformed")
    if not lock["required_binaries"]:
        raise RuntimeLockError("runtime declares no required binaries")

    built = lock["built_image_digest"]
    receipt = lock["qualification_receipt"]
    if lock["status"] == "build_and_qualification_pending":
        if built is not None or receipt is not None:
            raise RuntimeLockError("pending runtime cannot contain qualified build artifacts")
    elif lock["status"] == "qualified":
        if not isinstance(built, str) or not built.startswith("sha256:") or receipt is None:
            raise RuntimeLockError("qualified runtime lacks its image digest or receipt")
    else:
        raise RuntimeLockError("unknown runtime-lock status")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--source-pin", type=Path, required=True)
    args = parser.parse_args()
    validate(
        json.loads(args.lock.read_text(encoding="utf-8")),
        lock_path=args.lock,
        panel_path=args.panel,
        source_pin_path=args.source_pin,
    )
    print("validated pinned, pre-build Vero task-runtime lock")


if __name__ == "__main__":
    main()
