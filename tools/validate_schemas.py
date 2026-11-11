"""Validate Anarres JSON schemas and the public golden-path fixture."""

from __future__ import annotations

import json
from pathlib import Path

from anarres.environments.cli import build_manifest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    schema_paths = sorted((ROOT / "schemas").rglob("*.schema.json"))
    schemas = [load(path) for path in schema_paths]
    registry = Registry()
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))

    probe = load(ROOT / "examples/environment-processing/probe.json")
    probe_schema = load(ROOT / "schemas/environments/probe-input.v1.schema.json")
    Draft202012Validator(probe_schema, registry=registry).validate(probe)

    probe_run = load(ROOT / "examples/environment-processing/probe-run/probe.json")
    probe_run_schema = load(ROOT / "schemas/environments/probe-run.v1.schema.json")
    Draft202012Validator(probe_run_schema, registry=registry).validate(probe_run)
    attempt_schema = load(ROOT / "schemas/environments/probe-attempt.v1.schema.json")
    attempts_path = ROOT / "examples/environment-processing/probe-run/attempts.jsonl"
    for line in attempts_path.read_text(encoding="utf-8").splitlines():
        Draft202012Validator(attempt_schema, registry=registry).validate(json.loads(line))

    manifest = build_manifest(probe)
    manifest_schema = load(ROOT / "schemas/environments/environment-manifest.v1.schema.json")
    Draft202012Validator(manifest_schema, registry=registry).validate(manifest)

    profile_input_schema = load(
        ROOT / "schemas/environments/environment-profile-input.v1.schema.json"
    )
    profile_schema = load(ROOT / "schemas/environments/environment-profile.v1.schema.json")
    profile_inputs = sorted((ROOT / "examples/environment-profiles").glob("*.profile-input.json"))
    for path in profile_inputs:
        profile_input = load(path)
        Draft202012Validator(profile_input_schema, registry=registry).validate(profile_input)
        checks = profile_input["qualification_checks"]
        profile = {
            **profile_input,
            "schema_version": "anarres.environment-profile.v1",
            "qualification_summary": {
                "passed": sum(check["status"] == "pass" for check in checks),
                "failed": sum(check["status"] == "fail" for check in checks),
                "unknown": sum(check["status"] == "unknown" for check in checks),
                "warnings": sum(
                    check["severity"] == "warning" and check["status"] != "pass" for check in checks
                ),
            },
            "ready": all(
                check["severity"] != "error" or check["status"] == "pass" for check in checks
            ),
            "input_digest": "sha256:" + "0" * 64,
            "profile_digest": "sha256:" + "0" * 64,
        }
        Draft202012Validator(profile_schema, registry=registry).validate(profile)

    adapter_descriptor = load(ROOT / "examples/adapters/demo.descriptor.json")
    adapter_schema = load(ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json")
    Draft202012Validator(adapter_schema, registry=registry).validate(adapter_descriptor)

    print(
        f"validated {len(schema_paths)} schemas, the environment-processing fixtures, "
        f"{len(profile_inputs)} cross-domain profile fixtures, and the adapter descriptor"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
