#!/usr/bin/env python3
"""Validate the task-only containment contract and one qualification receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_SCHEMA = "anarres.formal-verification-containment-contract.v3"
RECEIPT_SCHEMA = "anarres.formal-verification-task-boundary-receipt.v1"
REQUIRED_FLAGS = {
    "--network none",
    "--ipc none",
    "--read-only",
    "--cap-drop ALL",
    "--security-opt no-new-privileges",
}


REQUIRED_AGREEMENT = {
    "source_report_qualified",
    "runtime_report_qualified",
    "source_identity",
    "source_revision",
    "source_pin",
    "mode",
    "lean_version",
    "tool_allowlist",
    "task_only_visibility",
    "task_network",
    "controller_endpoint",
    "process_limit",
    "memory_limit",
    "file_limit",
    "wall_limit",
    "turn_limit",
    "response_token_limit",
    "cumulative_token_limit",
}
ROUTE_FILES = {
    "probe_sha256": "run_codex_sol_probe.py",
    "sandbox_server_sha256": "serve_vibe_sandbox.py",
    "containment_runner_sha256": "run_containment_tests.py",
    "materializer_sha256": "materialize_probe_task.py",
}


class BoundaryError(ValueError):
    """Raised when a contract or receipt cannot support a containment claim."""


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_immutable_image(reference: Any) -> bool:
    if not isinstance(reference, str):
        return False
    digest = reference.split("@sha256:", 1)[-1] if "@sha256:" in reference else reference
    digest = digest.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def validate_contract(contract: dict[str, Any]) -> list[str]:
    """Check the frozen contract and return its required test identifiers."""
    if contract.get("schema_version") != CONTRACT_SCHEMA:
        raise BoundaryError("unsupported task-boundary contract schema")
    if contract["status"] == "frozen_unqualified" and contract["qualified"]:
        raise BoundaryError("a frozen-unqualified contract cannot be marked qualified")
    interface = contract["interface"]
    if set(interface["sandbox_methods"]) != {"sandbox/execute", "sandbox/readFile"}:
        raise BoundaryError("the contract has an unexpected sandbox method set")
    controller = contract["execution_boundaries"]["controller"]
    for field in (
        "model_facing_shell_or_file_access",
        "host_credentials_forwarded_to_sandbox",
        "user_global_configuration_loaded",
        "mcp_servers_enabled",
        "hooks_enabled",
        "project_plugins_enabled",
    ):
        if controller[field]:
            raise BoundaryError(f"controller setting must remain disabled: {field}")
    sandbox = contract["execution_boundaries"]["task_sandbox"]
    if sandbox["external_network_egress"]:
        raise BoundaryError("the task sandbox cannot have external network egress")
    if sandbox["container_user"] != "unprivileged host user":
        raise BoundaryError("the task sandbox must not run as container root")
    if not REQUIRED_FLAGS.issubset(sandbox["docker_flags"]):
        raise BoundaryError("the task sandbox is missing a required isolation flag")
    identifiers = [test["id"] for test in contract["required_tests"]]
    if len(identifiers) != len(set(identifiers)):
        raise BoundaryError("containment test identifiers must be unique")
    if contract["qualified"] and any(
        test["status"] != "pass" for test in contract["required_tests"]
    ):
        raise BoundaryError("the contract cannot be qualified while a test is unresolved")
    return identifiers


def validate_receipt(
    receipt: dict[str, Any],
    contract: dict[str, Any],
    contract_sha256: str,
    bundle: Path | None = None,
) -> None:
    """Check that one receipt is internally consistent and covers the contract exactly."""
    required = validate_contract(contract)
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise BoundaryError("unsupported task-boundary receipt schema")
    if receipt.get("contract_id") != contract["contract_id"]:
        raise BoundaryError("receipt names a different containment contract")
    if receipt.get("contract_sha256") != f"sha256:{contract_sha256}":
        raise BoundaryError("receipt was produced against different contract bytes")
    body = {key: value for key, value in receipt.items() if key != "receipt_id"}
    if receipt.get("receipt_id") != f"sha256:{canonical_sha256(body)}":
        raise BoundaryError("receipt identifier does not match its content")
    if not is_immutable_image(receipt["runtime_image"]["reference"]):
        raise BoundaryError("runtime image is not identified by an immutable digest")

    tests = receipt["tests"]
    identifiers = [test["id"] for test in tests]
    if sorted(identifiers) != sorted(required) or len(set(identifiers)) != len(identifiers):
        raise BoundaryError("receipt does not cover the contract's required tests exactly once")
    for test in tests:
        if not isinstance(test.get("passed"), bool) or not isinstance(test.get("evidence"), dict):
            raise BoundaryError(f"test {test.get('id')} lacks a boolean outcome or evidence")
    all_passed = all(test["passed"] for test in tests)
    if receipt["all_tests_passed"] != all_passed:
        raise BoundaryError("receipt misstates its test outcomes")

    interface = contract["interface"]
    boundaries = contract["execution_boundaries"]
    route = receipt["route"]
    if route["harness_version"] != interface["agent_harness_version"]:
        raise BoundaryError("receipt exercised a different harness version")
    if receipt["controller"]["model_id"] != interface["model_id"]:
        raise BoundaryError("receipt names a different policy")
    if sorted(route["sandbox_methods"]) != sorted(interface["sandbox_methods"]):
        raise BoundaryError("receipt exercised a different sandbox method set")
    if route["resource_limits"] != boundaries["resource_limits"]:
        raise BoundaryError("receipt resource limits differ from the contract")
    declared = {k: v for k, v in boundaries["controller_limits"].items() if not k.endswith("_rule")}
    if route["controller_limits"] != declared:
        raise BoundaryError("receipt controller limits differ from the contract")

    reports = receipt["reports"]
    agreement = reports["agreement"]
    if reports["bound"] and (
        set(agreement) != REQUIRED_AGREEMENT
        or not reports["source_report_sha256"]
        or not reports["runtime_report_sha256"]
    ):
        raise BoundaryError("bound reports must carry hashes and every field-level agreement")
    emulated = receipt["runtime_image"]["platform"]["emulated"]
    expected_qualified = (
        all_passed and reports["bound"] and all(agreement.values()) and not emulated
    )
    if receipt["qualified"] != expected_qualified:
        raise BoundaryError("receipt qualification disagrees with its tests and report agreement")

    materializations = list(receipt["task"]["materializations"].values())
    if len(materializations) < 2 or any(
        record != materializations[0] for record in materializations
    ):
        raise BoundaryError("receipt lacks two identical independent materializations")
    if receipt["task"]["protected_repositories_opened"]:
        raise BoundaryError("containment qualification may not open protected repositories")
    if receipt["controller"]["policy_contacted"]:
        raise BoundaryError("containment qualification must not contact a policy")

    if bundle is not None:
        for name, expected in receipt["files"].items():
            path = bundle / name
            if not path.is_file():
                raise BoundaryError(f"receipt file is missing: {name}")
            if f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}" != expected:
                raise BoundaryError(f"receipt file hash disagrees: {name}")


def validate_route_files(receipt: dict[str, Any], study_root: Path) -> None:
    """Check that the receipt's route hashes match the code in this checkout."""
    for field, name in ROUTE_FILES.items():
        digest = hashlib.sha256((study_root / name).read_bytes()).hexdigest()
        if receipt["route"][field] != f"sha256:{digest}":
            raise BoundaryError(f"{name} differs from the route the receipt qualified")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "--route-root",
        type=Path,
        help="Vero adapter directory whose route files must match the receipt",
    )
    args = parser.parse_args()
    contract_bytes = args.contract.read_bytes()
    contract = json.loads(contract_bytes)
    if args.receipt is None:
        validate_contract(contract)
        print(f"validated containment contract {contract['contract_id']}")
        return
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    validate_receipt(
        receipt,
        contract,
        hashlib.sha256(contract_bytes).hexdigest(),
        bundle=args.receipt.parent,
    )
    if args.route_root is not None:
        validate_route_files(receipt, args.route_root)
    state = "qualified" if receipt["qualified"] else "not qualified"
    print(f"validated task-boundary receipt {receipt['receipt_id']} ({state})")


if __name__ == "__main__":
    main()
