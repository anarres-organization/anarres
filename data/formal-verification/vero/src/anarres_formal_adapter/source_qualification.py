"""Qualification for the exact public Vero source checkout."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from importlib.resources import files
from pathlib import Path
from typing import Any

SHA1 = re.compile(r"^[0-9a-f]{40}$")


class SourceQualificationError(ValueError):
    """Raised when a Vero checkout violates its released source pin."""


def load_source_pin() -> dict[str, Any]:
    resource = files("anarres_formal_adapter").joinpath("source-pin.json")
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SourceQualificationError("bundled Vero source pin is not a JSON object")
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(source: Path, expression: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source), "rev-parse", expression],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SourceQualificationError(
            f"cannot inspect Vero Git identity for {expression}"
        ) from error
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
            raise SourceQualificationError(
                f"pinned artifact is missing metadata: {sorted(missing)}"
            )
        path = source / artifact["path"]
        if not path.is_file():
            raise SourceQualificationError(f"missing pinned artifact: {artifact['path']}")
        size = path.stat().st_size
        digest = file_sha256(path)
        if size != artifact["bytes"] or digest != artifact["sha256"]:
            raise SourceQualificationError(f"artifact identity mismatch: {artifact['path']}")
        verified.append({**artifact, "bytes": size, "sha256": digest})
    return verified


def require_file(root: Path, relative: str, label: str) -> None:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise SourceQualificationError(f"{label} escapes its benchmark root: {relative}")
    if not (root / path).is_file():
        raise SourceQualificationError(f"{label} does not exist: {relative}")


def audit_manifest(path: Path, pin: dict[str, Any]) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceQualificationError(f"cannot read benchmark manifest: {path}") from error
    required = {
        "benchmark_id",
        "lean_version",
        "modes_supported",
        "source",
        "files",
        "packages",
    }
    missing = required - set(manifest)
    if missing:
        raise SourceQualificationError(f"{path} is missing fields: {sorted(missing)}")
    if manifest["lean_version"] != pin["lean_version"]:
        raise SourceQualificationError(f"{path} has an unexpected Lean version")
    if sorted(manifest["modes_supported"]) != sorted(pin["modes_supported"]):
        raise SourceQualificationError(f"{path} has unexpected evaluation modes")
    source = manifest["source"]
    if not source.get("repo_url") or not SHA1.fullmatch(source.get("commit_hash", "")):
        raise SourceQualificationError(f"{path} lacks an immutable upstream source revision")

    root = path.parent
    for name, relative in manifest["files"].items():
        require_file(root, relative, f"{path.name} files.{name}")

    modules = 0
    api_ids: set[tuple[str, str, str]] = set()
    spec_ids: set[tuple[str, str, str]] = set()
    for package in manifest["packages"]:
        package_name = package.get("name")
        if not package_name:
            raise SourceQualificationError(f"{path} contains a package without a name")
        for module in package.get("modules", []):
            modules += 1
            module_name = module.get("name")
            if not module_name:
                raise SourceQualificationError(f"{path} contains a module without a name")
            if module.get("impl") is not None:
                require_file(root, module["impl"], f"{path.name} implementation")
            if module.get("spec") is not None:
                require_file(root, module["spec"], f"{path.name} specification")
            for api in module.get("apis", []):
                name = api["name"] if isinstance(api, dict) else api
                identity = (package_name, module_name, name)
                if identity in api_ids:
                    raise SourceQualificationError(
                        f"{path} contains duplicate API identity {identity}"
                    )
                api_ids.add(identity)
            for specification in module.get("specs", []):
                name = specification["name"] if isinstance(specification, dict) else specification
                identity = (package_name, module_name, name)
                if identity in spec_ids:
                    raise SourceQualificationError(
                        f"{path} contains duplicate spec identity {identity}"
                    )
                spec_ids.add(identity)

    trusted_axioms = manifest.get("trusted_axioms", [])
    if len(trusted_axioms) != len(set(trusted_axioms)):
        raise SourceQualificationError(f"{path} contains duplicate trusted axioms")
    return {
        "benchmark_id": manifest["benchmark_id"],
        "source_language": source.get("language"),
        "source_repository": source["repo_url"],
        "modules": modules,
        "apis": len(api_ids),
        "specs": len(spec_ids),
        "trusted_axioms": len(trusted_axioms),
    }


def qualify(source: Path) -> dict[str, Any]:
    """Audit the exact released Vero revision without running Lean or a policy."""

    pin = load_source_pin()
    if not (source / ".git").exists():
        raise SourceQualificationError("the pinned Vero source must be a Git checkout")
    revision = git_value(source, "HEAD")
    tree = git_value(source, "HEAD:benchmarks")
    if revision != pin["commit"]:
        raise SourceQualificationError(f"Git revision mismatch: {revision}")
    if tree != pin["benchmark_tree_git_oid"]:
        raise SourceQualificationError(f"benchmark tree mismatch: {tree}")
    verified = verify_artifacts(source, pin)

    manifests = sorted((source / "benchmarks").glob("*/manifest.json"))
    records = [audit_manifest(path, pin) for path in manifests]
    benchmark_ids = [record["benchmark_id"] for record in records]
    if len(benchmark_ids) != len(set(benchmark_ids)):
        raise SourceQualificationError("benchmark_id values are not unique")

    for benchmark in pin["license_exceptions"]:
        root = source / "benchmarks" / benchmark
        if not root.is_dir() or (not any(root.glob("LICEN*")) and not any(root.glob("COPYING*"))):
            raise SourceQualificationError(f"license exception lacks a license file: {benchmark}")

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
        raise SourceQualificationError(f"source counts differ from the pin: {counts}")

    pin_digest = hashlib.sha256(
        json.dumps(pin, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "source_id": pin["source_id"],
        "git_revision": revision,
        "benchmark_tree_git_oid": tree,
        "source_pin_sha256": pin_digest,
        "counts": counts,
        "verified_artifacts": len(verified),
        "lean_version": pin["lean_version"],
        "modes": pin["modes_supported"],
    }
