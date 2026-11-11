"""Static and local-runtime qualification for a pinned Vero checkout."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


class RuntimeQualificationError(ValueError):
    """Raised when a Vero execution contract is unsafe or inconsistent."""


SHA256 = re.compile(r"^[0-9a-f]{64}$")
LEAN_VERSION = re.compile(r"\bversion\s+(\d+\.\d+\.\d+)\b", re.IGNORECASE)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeQualificationError(f"{label} must be an object")
    return value


def require_exact_keys(value: dict[str, Any], keys: set[str], label: str) -> None:
    missing = keys - set(value)
    extra = set(value) - keys
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {sorted(missing)}")
        if extra:
            details.append(f"unexpected {sorted(extra)}")
        raise RuntimeQualificationError(f"{label} has " + " and ".join(details))


def require_positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeQualificationError(f"{label} must be a positive integer")
    return value


def require_string_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise RuntimeQualificationError(f"{label} must be a nonempty string list")
    if len(value) != len(set(value)):
        raise RuntimeQualificationError(f"{label} contains duplicates")
    return value


def require_container_path(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.startswith("/"):
        raise RuntimeQualificationError(f"{label} must be an absolute container path")
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise RuntimeQualificationError(f"{label} contains parent traversal")
    if str(path) in {"/", "/root", "/home", "/workspace"}:
        raise RuntimeQualificationError(f"{label} is too broad")
    return path


def is_within(path: PurePosixPath, roots: list[PurePosixPath]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def run_identity(executable: Path, label: str) -> dict[str, str]:
    if not executable.is_file():
        raise RuntimeQualificationError(f"{label} executable does not exist: {executable}")
    if not os.access(executable, os.X_OK):
        raise RuntimeQualificationError(f"{label} executable is not executable: {executable}")
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeQualificationError(f"cannot identify {label} executable") from error
    output = (completed.stdout + "\n" + completed.stderr).strip()
    if not output:
        raise RuntimeQualificationError(f"{label} version command returned no identity")
    return {
        "name": executable.name,
        "sha256": f"sha256:{file_sha256(executable)}",
        "version_output": output,
    }


def qualify(
    *,
    contract_path: Path,
    source: Path,
    source_report: dict[str, Any],
    source_revision: str,
    lean_executable: Path,
    lake_executable: Path,
) -> dict[str, Any]:
    """Validate a Vero runtime contract without contacting a model."""

    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeQualificationError(f"cannot read runtime contract: {contract_path}") from error
    require_exact_keys(
        require_mapping(contract, "runtime contract"),
        {
            "schema_version",
            "contract_id",
            "source",
            "mode",
            "toolchain",
            "sandbox",
            "limits",
            "verifier",
            "network",
            "cleanup",
            "filesystem",
            "resources",
        },
        "runtime contract",
    )
    if contract["schema_version"] != "anarres.formal-verification-runtime-contract.v1":
        raise RuntimeQualificationError("unsupported formal-verification runtime schema")
    if not isinstance(contract["contract_id"], str) or not contract["contract_id"]:
        raise RuntimeQualificationError("contract_id must be nonempty")

    source_contract = require_mapping(contract["source"], "source")
    require_exact_keys(
        source_contract,
        {"source_id", "revision", "source_pin_sha256", "package_lock"},
        "source",
    )
    expected_pin = f"sha256:{source_report['source_pin_sha256']}"
    if (
        source_contract["source_id"] != source_report["source_id"]
        or source_contract["revision"] != source_revision
        or source_contract["source_pin_sha256"] != expected_pin
    ):
        raise RuntimeQualificationError("runtime source identity differs from source qualification")
    package_lock = require_mapping(source_contract["package_lock"], "source.package_lock")
    require_exact_keys(package_lock, {"path", "sha256"}, "source.package_lock")
    relative_lock = Path(package_lock["path"])
    if relative_lock.is_absolute() or ".." in relative_lock.parts:
        raise RuntimeQualificationError("package-lock path escapes the Vero checkout")
    lock_path = source / relative_lock
    if not lock_path.is_file():
        raise RuntimeQualificationError("declared package lock is missing")
    lock_digest = file_sha256(lock_path)
    if package_lock["sha256"] != f"sha256:{lock_digest}":
        raise RuntimeQualificationError("package-lock identity mismatch")

    mode = contract["mode"]
    if mode not in source_report["modes"]:
        raise RuntimeQualificationError(f"unsupported Vero mode: {mode}")

    toolchain = require_mapping(contract["toolchain"], "toolchain")
    require_exact_keys(toolchain, {"lean_version", "lean_toolchain", "lake_required"}, "toolchain")
    if toolchain["lean_version"] != source_report["lean_version"]:
        raise RuntimeQualificationError("Lean version differs from the qualified source")
    if toolchain["lean_toolchain"] != f"leanprover/lean4:v{source_report['lean_version']}":
        raise RuntimeQualificationError("Lean toolchain identity is inconsistent")
    if toolchain["lake_required"] is not True:
        raise RuntimeQualificationError("the Vero runtime must require Lake")
    lean_identity = run_identity(lean_executable, "Lean")
    lean_match = LEAN_VERSION.search(lean_identity["version_output"])
    if lean_match is None or lean_match.group(1) != source_report["lean_version"]:
        raise RuntimeQualificationError("local Lean executable has the wrong version")
    lake_identity = run_identity(lake_executable, "Lake")
    if "lake" not in lake_identity["version_output"].lower():
        raise RuntimeQualificationError("local Lake executable returned an unexpected identity")

    sandbox = require_mapping(contract["sandbox"], "sandbox")
    require_exact_keys(
        sandbox,
        {"task_visibility", "tool_allowlist", "forbidden_inputs"},
        "sandbox",
    )
    if sandbox["task_visibility"] != "task-only":
        raise RuntimeQualificationError("sandbox visibility must be task-only")
    tools = require_string_list(sandbox["tool_allowlist"], "sandbox.tool_allowlist")
    if set(tools) != {"sandbox/execute", "sandbox/readFile"}:
        raise RuntimeQualificationError(
            "sandbox tool allowlist differs from the qualified interface"
        )
    forbidden = require_string_list(sandbox["forbidden_inputs"], "sandbox.forbidden_inputs")
    required_forbidden = {
        "reference-solutions",
        "source-benchmark-tree",
        "qualification-tasks",
        "prospective-tasks",
        "host-home",
        "host-credentials",
        "other-attempt-workspaces",
    }
    if not required_forbidden.issubset(forbidden):
        raise RuntimeQualificationError("sandbox forbidden-input set is incomplete")

    limits = require_mapping(contract["limits"], "limits")
    required_limits = {"wall_seconds", "turns", "response_tokens", "cumulative_tokens"}
    require_exact_keys(limits, required_limits, "limits")
    normalized_limits = {
        name: require_positive_integer(limits[name], f"limits.{name}")
        for name in sorted(required_limits)
    }
    if normalized_limits["response_tokens"] > normalized_limits["cumulative_tokens"]:
        raise RuntimeQualificationError("response-token ceiling exceeds cumulative-token ceiling")

    verifier = require_mapping(contract["verifier"], "verifier")
    require_exact_keys(verifier, {"command", "identity", "strict_success"}, "verifier")
    verifier_command = require_string_list(verifier["command"], "verifier.command")
    if "{task}" not in verifier_command:
        raise RuntimeQualificationError("verifier command must contain the {task} placeholder")
    if verifier_command[0] != lake_executable.name:
        raise RuntimeQualificationError("verifier command does not use the qualified Lake binary")
    if verifier["identity"] != "vero-strict-lean-v1":
        raise RuntimeQualificationError("verifier identity differs from the Vero strict grader")
    if verifier["strict_success"] != "exit-zero-and-all-specifications-verified":
        raise RuntimeQualificationError("strict-success semantics differ from the Vero contract")

    network = require_mapping(contract["network"], "network")
    require_exact_keys(network, {"task_external_egress", "controller_allowlist"}, "network")
    if network["task_external_egress"] is not False:
        raise RuntimeQualificationError("task sandbox must disable external network egress")
    controller_allowlist = require_string_list(
        network["controller_allowlist"], "network.controller_allowlist"
    )
    if any(
        not endpoint.startswith(("http://127.0.0.1:", "http://localhost:"))
        for endpoint in controller_allowlist
    ):
        raise RuntimeQualificationError(
            "controller network allowlist must contain only local endpoints"
        )

    cleanup = require_mapping(contract["cleanup"], "cleanup")
    require_exact_keys(cleanup, {"process_tree", "workspace", "verify_after_attempt"}, "cleanup")
    if cleanup != {
        "process_tree": "terminate",
        "workspace": "destroy",
        "verify_after_attempt": True,
    }:
        raise RuntimeQualificationError("cleanup behavior is not strict enough")

    filesystem = require_mapping(contract["filesystem"], "filesystem")
    require_exact_keys(
        filesystem,
        {"task_root", "read_only_paths", "writable_paths", "output_path"},
        "filesystem",
    )
    task_root = require_container_path(filesystem["task_root"], "filesystem.task_root")
    read_only = [
        require_container_path(path, "filesystem.read_only_paths")
        for path in require_string_list(filesystem["read_only_paths"], "filesystem.read_only_paths")
    ]
    writable = [
        require_container_path(path, "filesystem.writable_paths")
        for path in require_string_list(filesystem["writable_paths"], "filesystem.writable_paths")
    ]
    output_path = require_container_path(filesystem["output_path"], "filesystem.output_path")
    if any(
        left == right or left in right.parents or right in left.parents
        for left in read_only
        for right in writable
    ):
        raise RuntimeQualificationError("read-only and writable path sets overlap")
    if not is_within(task_root, writable):
        raise RuntimeQualificationError("task root must be inside a declared writable path")
    if not is_within(output_path, writable):
        raise RuntimeQualificationError("output path must be inside a declared writable path")

    resources = require_mapping(contract["resources"], "resources")
    required_resources = {"processes", "memory_bytes", "file_bytes"}
    require_exact_keys(resources, required_resources, "resources")
    normalized_resources = {
        name: require_positive_integer(resources[name], f"resources.{name}")
        for name in sorted(required_resources)
    }

    checks = [
        "source-bound",
        "package-lock-bound",
        "lean-identity",
        "lake-identity",
        "mode-supported",
        "task-only-visibility",
        "tool-allowlist",
        "execution-ceilings",
        "strict-verifier",
        "network-policy",
        "cleanup-policy",
        "filesystem-policy",
        "resource-limits",
    ]
    report: dict[str, Any] = {
        "schema_version": "anarres.formal-verification-runtime-report.v1",
        "status": "qualified",
        "contract_id": contract["contract_id"],
        "contract_sha256": f"sha256:{file_sha256(contract_path)}",
        "source_id": source_report["source_id"],
        "source_revision": source_revision,
        "source_pin_sha256": expected_pin,
        "package_lock": {
            "path": package_lock["path"],
            "sha256": f"sha256:{lock_digest}",
        },
        "mode": mode,
        "toolchain": {
            "lean_version": source_report["lean_version"],
            "lean_toolchain": toolchain["lean_toolchain"],
            "lean_executable": lean_identity,
            "lake_executable": lake_identity,
        },
        "sandbox": sandbox,
        "limits": normalized_limits,
        "verifier": verifier,
        "network": network,
        "cleanup": cleanup,
        "filesystem": filesystem,
        "resources": normalized_resources,
        "checks": [{"check_id": check, "status": "pass"} for check in checks],
        "model_execution_started": False,
        "task_opened": False,
        "policy_probe_available": False,
    }
    report["report_id"] = f"sha256:{canonical_sha256(report)}"
    return report
