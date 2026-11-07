#!/usr/bin/env python3
"""Qualify Vero's pinned Lean runtime and bounded grader controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

EXPECTED_TESTS = 93
LEAN_VERSION = re.compile(
    r"Lean (?:\(version )?(?P<version>\d+\.\d+\.\d+),.*commit (?P<commit>[0-9a-f]+)"
)
PYTEST_SUMMARY = re.compile(r"(?P<passed>\d+) passed in (?P<seconds>[0-9.]+)s")
TEST_PATHS = (
    "tests/evaluation",
    "tests/generation/test_render.py",
    "tests/generation/test_extractor.py",
    "tests/generation/test_sandbox.py",
    "tests/generation/test_proof_materialize.py",
)


class AuditError(ValueError):
    """Raised when the runtime does not satisfy the pinned contract."""


def run(
    arguments: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith((".lake/", "build/")):
            continue
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def parse_lean_version(output: str, expected: str) -> dict[str, str]:
    match = LEAN_VERSION.search(output)
    if not match:
        raise AuditError("could not parse Lean toolchain identity")
    if match.group("version") != expected:
        raise AuditError(f"Lean version mismatch: {match.group('version')}")
    return match.groupdict()


def parse_pytest_output(output: str) -> dict[str, Any]:
    match = PYTEST_SUMMARY.search(output)
    if not match:
        raise AuditError("bounded grader tests did not emit a passing summary")
    passed = int(match.group("passed"))
    if passed != EXPECTED_TESTS:
        raise AuditError(f"expected {EXPECTED_TESTS} bounded grader tests, observed {passed}")
    if " skipped" in output or " failed" in output or " error" in output.lower():
        raise AuditError("bounded grader tests did not complete without skips or failures")
    return {"passed": passed, "reported_seconds": float(match.group("seconds"))}


def verify_revision(source: Path, expected: str) -> str:
    revision = run(["git", "rev-parse", "HEAD"], cwd=source).stdout.strip()
    if revision != expected:
        raise AuditError(f"source revision mismatch: {revision}")
    diff = subprocess.run(["git", "diff", "--quiet"], cwd=source)
    if diff.returncode != 0:
        raise AuditError("tracked files in the Vero checkout differ from the pinned revision")
    return revision


def build_reference_once(source: Path, lake: str, expected_lean: str) -> dict[str, Any]:
    reference = source / "reference" / "BankLedger"
    if not reference.is_dir():
        raise AuditError("missing Vero BankLedger reference project")
    with tempfile.TemporaryDirectory(prefix="anarres-vero-reference-") as directory:
        project = Path(directory) / "BankLedger"
        shutil.copytree(reference, project)
        source_digest = tree_digest(project)
        toolchain = run([lake, "env", "lean", "--version"], cwd=project)
        identity = parse_lean_version(toolchain.stdout + toolchain.stderr, expected_lean)
        started = time.monotonic()
        result = run([lake, "build"], cwd=project)
        elapsed = time.monotonic() - started
        output = result.stdout + result.stderr
        return {
            "source_sha256": source_digest,
            "lean": identity,
            "elapsed_seconds": round(elapsed, 3),
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        }


def run_grader_controls(source: Path, python: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    result = run([python, "-m", "pytest", "-q", *TEST_PATHS], cwd=source, env=env)
    elapsed = time.monotonic() - started
    output = result.stdout + result.stderr
    summary = parse_pytest_output(output)
    summary.update(
        {
            "elapsed_seconds": round(elapsed, 3),
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        }
    )
    return summary


def audit(
    source: Path,
    pin: dict[str, Any],
    *,
    lake: str,
    python: str,
    repetitions: int,
) -> dict[str, Any]:
    if repetitions < 2:
        raise AuditError("clean-reset qualification requires at least two repetitions")
    revision = verify_revision(source, pin["commit"])
    builds = [build_reference_once(source, lake, pin["lean_version"]) for _ in range(repetitions)]
    source_digests = {build["source_sha256"] for build in builds}
    lean_identities = {json.dumps(build["lean"], sort_keys=True) for build in builds}
    if len(source_digests) != 1 or len(lean_identities) != 1:
        raise AuditError("clean reference builds disagree on source or toolchain identity")

    grader = run_grader_controls(source, python)
    return {
        "schema_version": "anarres.formal-verification-runtime-audit.v1",
        "source_id": pin["source_id"],
        "source_revision": revision,
        "reference_builds": builds,
        "grader_controls": grader,
        "checks": {
            "pinned_lean_toolchain": "pass",
            "reference_build": "pass",
            "clean_reset_agreement": "pass",
            "native_unsat_and_joint_evaluation": "pass",
            "sorry_and_axiom_rejection": "pass",
            "unsafe_and_overfilled_rejection": "pass",
            "frozen_file_and_extra_marker_removal": "pass",
        },
        "qualification_state": "runtime_and_grader_qualified_policy_measurement_pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lake", default="lake")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    report = audit(
        args.source.resolve(),
        pin,
        lake=args.lake,
        python=args.python,
        repetitions=args.repetitions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"qualified Vero runtime across {args.repetitions} clean reference builds")


if __name__ == "__main__":
    main()
