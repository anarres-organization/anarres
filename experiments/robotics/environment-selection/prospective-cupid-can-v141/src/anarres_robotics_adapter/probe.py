"""Portable preflight checks for the released Can measurement contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


class ProbePreflightError(ValueError):
    """Raised when local probe inputs differ from the released contract."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "anarres.robotics-cupid-can-v141-probe-contract.v1":
        raise ProbePreflightError("unsupported robotics probe contract")
    if contract.get("execution", {}).get("policy_probe_capability_released") is not False:
        raise ProbePreflightError("unreleased probe contract cannot advertise policy-probe")
    return contract


def git_revision(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def checkpoint_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*.pth") if path.is_file())


def _check(check_id: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "observed": observed,
        "expected": expected,
    }


def inspect_preflight(
    *,
    contract_path: Path,
    dataset: Path | None,
    checkpoints: Path | None,
    runtime: Path | None,
    python: str | None,
    backend: str,
) -> dict[str, Any]:
    """Inspect local artifacts without running rollouts or opening outcomes."""

    contract = read_contract(contract_path)
    checks: list[dict[str, Any]] = []
    source = contract["source"]
    subject = contract["subject"]
    runtime_contract = contract["runtime"]

    observed_dataset = file_sha256(dataset) if dataset is not None and dataset.is_file() else None
    checks.append(
        _check(
            "source-dataset",
            observed_dataset == source["sha256"],
            observed_dataset,
            source["sha256"],
        )
    )

    expected_checkpoints = {item["sha256"]: item["seed"] for item in subject["checkpoints"]}
    observed_checkpoints: dict[str, str] = {}
    if checkpoints is not None:
        for path in checkpoint_paths(checkpoints):
            digest = file_sha256(path)
            if digest in expected_checkpoints:
                observed_checkpoints[digest] = path.name
    checks.append(
        _check(
            "scoring-checkpoint-ensemble",
            set(observed_checkpoints) == set(expected_checkpoints),
            sorted(observed_checkpoints),
            sorted(expected_checkpoints),
        )
    )

    for name, revision in runtime_contract["checkouts"].items():
        checkout = None if runtime is None else runtime / name
        if name == "CUPID" and runtime is not None and not checkout.exists():
            checkout = runtime / "cupid"
        if name == "PyTorch3D" and runtime is not None and not checkout.exists():
            checkout = runtime / "pytorch3d"
        observed = git_revision(checkout) if checkout is not None and checkout.is_dir() else None
        checks.append(_check(f"checkout-{name.lower()}", observed == revision, observed, revision))

    for relative, digest in runtime_contract["entrypoints"].items():
        path = None if runtime is None else runtime / relative
        observed = file_sha256(path) if path is not None and path.is_file() else None
        checks.append(_check(f"entrypoint-{relative}", observed == digest, observed, digest))

    package_versions: dict[str, str | None] = {}
    expected_python = runtime_contract.get("python")
    python_path = Path(python) if python else None
    if expected_python is not None and (python_path is None or not python_path.is_file()):
        checks.append(_check("python", False, None, expected_python))
    elif python_path is not None and python_path.is_file():
        script = """
import importlib.metadata as metadata
import json
import sys

versions = {}
for name in json.loads(sys.argv[1]):
    try:
        versions[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        versions[name] = None
print(json.dumps({
    "python": ".".join(map(str, sys.version_info[:3])),
    "packages": versions,
}))
"""
        result = subprocess.run(
            [str(python_path), "-c", script, json.dumps(sorted(runtime_contract["packages"]))],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            checks.append(_check("python", False, result.stderr.strip(), expected_python))
        else:
            observed_runtime = json.loads(result.stdout)
            if expected_python is not None:
                checks.append(
                    _check(
                        "python",
                        observed_runtime["python"] == expected_python,
                        observed_runtime["python"],
                        expected_python,
                    )
                )
            package_versions = observed_runtime["packages"]
    for name, version in runtime_contract["packages"].items():
        observed = package_versions.get(name)
        checks.append(_check(f"package-{name}", observed == version, observed, version))

    checks.append(
        _check(
            "backend",
            backend in contract["execution"]["supported_backends"],
            backend,
            contract["execution"]["supported_backends"],
        )
    )
    failures = [item["check_id"] for item in checks if item["status"] == "fail"]
    release_blockers = contract["execution"]["release_blockers"]
    return {
        "schema_version": "anarres.robotics-probe-preflight.v1",
        "study_id": contract["study_id"],
        "measurement_contract": contract["measurement_contract"],
        "contract_sha256": f"sha256:{file_sha256(contract_path)}",
        "subject": {"kind": subject["kind"], "id": subject["id"], "revision": subject["revision"]},
        "mode": "dry_run",
        "backend": backend,
        "ready": not failures and not release_blockers,
        "artifacts_conform": not failures,
        "checks": checks,
        "missing_or_mismatched": failures,
        "release_blockers": release_blockers,
        "execution_started": False,
        "candidate_outcomes_opened": False,
    }
