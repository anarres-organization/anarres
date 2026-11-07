#!/usr/bin/env python3
"""Audit the digest-pinned OSS Verify checker runtime without checking a proof."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

DIGEST = re.compile(r"@sha256:([0-9a-f]{64})$")


class AuditError(ValueError):
    """Raised when the checker runtime differs from the pinned contract."""


def expected_image_id(reference: str) -> str:
    match = DIGEST.search(reference)
    if not match:
        raise AuditError("checker image must be pinned by a SHA-256 digest")
    return f"sha256:{match.group(1)}"


def docker_json(arguments: list[str]) -> Any:
    result = subprocess.run(
        ["docker", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def audit(pin: dict[str, Any]) -> dict[str, Any]:
    image = pin["images"]["checker"]
    expected_id = expected_image_id(image)
    inspected = docker_json(["image", "inspect", image])[0]
    observed_id = inspected["Id"]
    if observed_id != expected_id:
        raise AuditError(f"checker image mismatch: {observed_id}")
    if image not in inspected.get("RepoDigests", []):
        raise AuditError("checker image does not expose the pinned repository digest")

    probe_code = """
import json
import platform
import shutil
import subprocess

rocq = subprocess.run(
    ["rocq", "--version"], check=True, capture_output=True, text=True
).stdout.strip()
packages = subprocess.run(
    [
        "opam",
        "list",
        "--installed",
        "--columns=name,version",
        "--separator==",
    ],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()
package_versions = {
    name.strip(): version.strip()
    for line in packages
    if "=" in line and not line.startswith("#")
    for name, version in [line.split("=", maxsplit=1)]
}
ipv4_routes = open("/proc/net/route", encoding="utf-8").read().splitlines()[1:]
ipv6_routes = open("/proc/net/ipv6_route", encoding="utf-8").read().splitlines()
print(json.dumps({
    "rocq": rocq,
    "python": platform.python_version(),
    "elf_snapshot": shutil.which("elf-snapshot"),
    "ipv4_routes": ipv4_routes,
    "ipv6_non_loopback_routes": [
        route for route in ipv6_routes if route.split()[-1] != "lo"
    ],
    "packages": {
        name: version
        for name, version in sorted(package_versions.items())
        if name.startswith("rocq-")
    },
}))
"""
    runtime = docker_json(
        [
            "run",
            "--rm",
            "--network",
            "none",
            image,
            "python3",
            "-c",
            probe_code,
        ]
    )
    package = pin["rocq"]["package"]
    version = pin["rocq"]["version"]
    if runtime["packages"].get(package) != version:
        raise AuditError(f"unexpected {package} version: {runtime['packages'].get(package)}")
    displayed_version = version.removesuffix(".0")
    if not runtime["rocq"].startswith(f"The Rocq Prover, version {displayed_version}"):
        raise AuditError(f"unexpected Rocq version: {runtime['rocq']}")
    if "rocq-linux-process-semantics-core" not in runtime["packages"]:
        raise AuditError("checker image lacks the LPS core package")
    if not runtime["elf_snapshot"]:
        raise AuditError("checker image lacks elf-snapshot")
    if runtime["ipv4_routes"] or runtime["ipv6_non_loopback_routes"]:
        raise AuditError("network-none runtime exposes a non-loopback route")

    return {
        "schema_version": "anarres.formal-verification-runtime-audit.v1",
        "source_id": pin["source_id"],
        "checker_image": image,
        "image_id": observed_id,
        "image_size_bytes": inspected["Size"],
        "runtime": runtime,
        "checks": {
            "digest_identity": "pass",
            "rocq_version": "pass",
            "lps_core_present": "pass",
            "elf_snapshot_present": "pass",
            "network_routes": "loopback_only",
        },
        "qualification_state": "checker_runtime_bootstrap_qualified_proof_replay_pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    report = audit(pin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"qualified checker runtime bootstrap for {report['checker_image']}")


if __name__ == "__main__":
    main()
