"""Validate Anarres JSON schemas and the public golden-path fixture."""

from __future__ import annotations

import json
from pathlib import Path

from anarres.environments.cli import build_manifest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    schema_paths = sorted((ROOT / "schemas").rglob("*.schema.json"))
    for schema_path in schema_paths:
        Draft202012Validator.check_schema(load(schema_path))

    probe = load(ROOT / "examples/environment-processing/probe.json")
    probe_schema = load(ROOT / "schemas/environments/probe-input.v1.schema.json")
    Draft202012Validator(probe_schema).validate(probe)

    manifest = build_manifest(probe)
    manifest_schema = load(ROOT / "schemas/environments/environment-manifest.v1.schema.json")
    Draft202012Validator(manifest_schema).validate(manifest)

    print(f"validated {len(schema_paths)} schemas and the environment-processing fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
