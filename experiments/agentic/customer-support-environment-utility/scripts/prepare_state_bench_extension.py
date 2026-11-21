#!/usr/bin/env python3
"""Install the versioned Anarres learning extension into a qualified STATE-Bench checkout."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "execution/state_bench_extension"
EXTENSION_FILES = ("anarres_learning_operator.py", "anarres_memory_agent.py")

AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(checkout: Path) -> dict:
    source = audit_checkout(checkout)
    destination = checkout / "agents"
    destination.mkdir(exist_ok=True)
    files = {}
    for name in EXTENSION_FILES:
        source_path = SOURCE_DIR / name
        destination_path = destination / name
        if destination_path.exists() and sha256(destination_path) != sha256(source_path):
            raise ValueError(f"refusing to replace a different extension file: {destination_path}")
        if not destination_path.exists():
            shutil.copyfile(source_path, destination_path)
        files[f"agents/{name}"] = sha256(destination_path)
    return {
        "schema_version": 1,
        "status": "STATE_BENCH_EXTENSION_READY__NO_MODEL_CALLS_MADE",
        "source_revision": source["revision"],
        "extension_files": files,
        "agent_class": "AnarresEpisodicMemoryAgent",
        "learning_artifact_env": "ANARRES_STATE_LEARNINGS_PATH",
        "model_calls_made": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    result = prepare(arguments.checkout.resolve())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
