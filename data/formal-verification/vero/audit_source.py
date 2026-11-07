#!/usr/bin/env python3
"""Audit a pinned Vero checkout without running a model or Lean build."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

SHA1 = re.compile(r"^[0-9a-f]{40}$")


class AuditError(ValueError):
    """Raised when the pinned Vero source contract is violated."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(source: Path, expression: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", expression],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_artifacts(source: Path, pin: dict[str, Any]) -> list[dict[str, Any]]:
    required = {
        "path",
        "uri",
        "bytes",
        "sha256",
        "media_type",
        "license",
        "producing_run_or_upstream_release",
    }
    verified = []
    for artifact in pin["artifacts"]:
        missing = required - set(artifact)
        if missing:
            raise AuditError(f"pinned artifact is missing metadata: {sorted(missing)}")
        path = source / artifact["path"]
        if not path.is_file():
            raise AuditError(f"missing pinned artifact: {artifact['path']}")
        size = path.stat().st_size
        digest = file_sha256(path)
        if size != artifact["bytes"] or digest != artifact["sha256"]:
            raise AuditError(f"artifact identity mismatch: {artifact['path']}")
        verified.append({**artifact, "bytes": size, "sha256": digest})
    return verified


def require_file(root: Path, relative: str, label: str) -> None:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise AuditError(f"{label} escapes its benchmark root: {relative}")
    if not (root / path).is_file():
        raise AuditError(f"{label} does not exist: {relative}")


def audit_manifest(path: Path, pin: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {"benchmark_id", "lean_version", "modes_supported", "source", "files", "packages"}
    missing = required - set(manifest)
    if missing:
        raise AuditError(f"{path} is missing fields: {sorted(missing)}")
    if manifest["lean_version"] != pin["lean_version"]:
        raise AuditError(f"{path} has an unexpected Lean version")
    if sorted(manifest["modes_supported"]) != sorted(pin["modes_supported"]):
        raise AuditError(f"{path} has unexpected evaluation modes")
    source = manifest["source"]
    if not source.get("repo_url") or not SHA1.fullmatch(source.get("commit_hash", "")):
        raise AuditError(f"{path} lacks an immutable upstream source revision")

    root = path.parent
    for name, relative in manifest["files"].items():
        require_file(root, relative, f"{path.name} files.{name}")

    modules = 0
    api_ids = set()
    spec_ids = set()
    for package in manifest["packages"]:
        package_name = package.get("name")
        if not package_name:
            raise AuditError(f"{path} contains a package without a name")
        for module in package.get("modules", []):
            modules += 1
            module_name = module.get("name")
            if not module_name:
                raise AuditError(f"{path} contains a module without a name")
            if module.get("impl") is not None:
                require_file(root, module["impl"], f"{path.name} implementation")
            if module.get("spec") is not None:
                require_file(root, module["spec"], f"{path.name} specification")
            for api in module.get("apis", []):
                name = api["name"] if isinstance(api, dict) else api
                identity = (package_name, module_name, name)
                if identity in api_ids:
                    raise AuditError(f"{path} contains duplicate API identity {identity}")
                api_ids.add(identity)
            for spec in module.get("specs", []):
                name = spec["name"] if isinstance(spec, dict) else spec
                identity = (package_name, module_name, name)
                if identity in spec_ids:
                    raise AuditError(f"{path} contains duplicate spec identity {identity}")
                spec_ids.add(identity)

    trusted_axioms = manifest.get("trusted_axioms", [])
    if len(trusted_axioms) != len(set(trusted_axioms)):
        raise AuditError(f"{path} contains duplicate trusted axioms")
    return {
        "benchmark_id": manifest["benchmark_id"],
        "source_language": source.get("language"),
        "source_repository": source["repo_url"],
        "modules": modules,
        "apis": len(api_ids),
        "specs": len(spec_ids),
        "trusted_axioms": len(trusted_axioms),
    }


def audit(source: Path, pin: dict[str, Any]) -> dict[str, Any]:
    if not (source / ".git").exists():
        raise AuditError("the pinned source must be a Git checkout")
    revision = git_value(source, "HEAD")
    tree = git_value(source, "HEAD:benchmarks")
    if revision != pin["commit"]:
        raise AuditError(f"Git revision mismatch: {revision}")
    if tree != pin["benchmark_tree_git_oid"]:
        raise AuditError(f"benchmark tree mismatch: {tree}")
    verified = verify_artifacts(source, pin)

    manifests = sorted((source / "benchmarks").glob("*/manifest.json"))
    records = [audit_manifest(path, pin) for path in manifests]
    benchmark_ids = [record["benchmark_id"] for record in records]
    if len(benchmark_ids) != len(set(benchmark_ids)):
        raise AuditError("benchmark_id values are not unique")

    exceptions = pin["license_exceptions"]
    for benchmark, _license in exceptions.items():
        root = source / "benchmarks" / benchmark
        if not root.is_dir() or not any(root.glob("LICEN*")) and not any(root.glob("COPYING*")):
            raise AuditError(f"license exception lacks a license file: {benchmark}")

    counts = {
        "benchmarks": len(records),
        "modules": sum(record["modules"] for record in records),
        "apis": sum(record["apis"] for record in records),
        "specs": sum(record["specs"] for record in records),
        "trusted_axiom_benchmarks": sum(record["trusted_axioms"] > 0 for record in records),
        "trusted_axioms": sum(record["trusted_axioms"] for record in records),
        "source_languages": dict(
            sorted(Counter(record["source_language"] for record in records).items())
        ),
    }
    if counts != pin["expected_counts"]:
        raise AuditError(f"source counts differ from the pin: {counts}")

    pin_digest = hashlib.sha256(
        json.dumps(pin, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": "anarres.formal-verification-source-audit.v1",
        "source_id": pin["source_id"],
        "git_revision": revision,
        "benchmark_tree_git_oid": tree,
        "source_pin_sha256": pin_digest,
        "counts": counts,
        "verified_artifacts": verified,
        "checks": {
            "artifact_identity": "pass",
            "git_revision": "pass",
            "benchmark_tree": "pass",
            "manifest_schema": "pass",
            "path_containment": "pass",
            "source_revision": "pass",
            "license_exception_files": "pass",
        },
        "qualification_state": "source_qualified_runtime_pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    report = audit(args.source, pin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"qualified {report['counts']['benchmarks']} Vero benchmarks with "
        f"{report['counts']['specs']} specifications"
    )


if __name__ == "__main__":
    main()
