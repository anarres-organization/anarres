#!/usr/bin/env python3
"""Validate the frozen, pre-execution Vero containment contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    """Raised when the containment contract is incomplete or contradictory."""


EXPECTED_TESTS = {
    "workspace_allowlist",
    "path_and_symlink_escape",
    "credential_and_environment_visibility",
    "controller_configuration_isolation",
    "external_network_egress",
    "local_inference_separation",
    "process_tree_cleanup",
    "resource_limits",
    "fresh_task_reset",
    "vibe_export_completeness",
}


def validate(contract: dict[str, Any]) -> None:
    interface = contract["interface"]
    if interface["agent_socket_protocol_version"] != 2:
        raise ContractError("the contract must pin Vibe agent-socket protocol 2")
    if set(interface["sandbox_methods"]) != {"sandbox/execute", "sandbox/readFile"}:
        raise ContractError("the contract has an unexpected sandbox method set")

    boundaries = contract["execution_boundaries"]
    if boundaries["controller"]["model_facing_shell_or_file_access"]:
        raise ContractError("model-facing tools cannot execute on the controller")
    for field in (
        "user_global_configuration_loaded",
        "mcp_servers_enabled",
        "hooks_enabled",
        "project_plugins_enabled",
    ):
        if boundaries["controller"][field]:
            raise ContractError(f"controller setting must remain disabled: {field}")
    if boundaries["task_sandbox"]["external_network_egress"]:
        raise ContractError("the task sandbox cannot have external network egress")

    tests = contract["required_tests"]
    identifiers = [test["id"] for test in tests]
    if len(identifiers) != len(set(identifiers)):
        raise ContractError("containment test identifiers must be unique")
    if set(identifiers) != EXPECTED_TESTS:
        raise ContractError("the containment contract is missing a required test")
    if contract["qualified"] and any(test["status"] != "pass" for test in tests):
        raise ContractError("the contract cannot be qualified while a test is unresolved")
    if contract["status"] == "frozen_unqualified" and contract["qualified"]:
        raise ContractError("a frozen-unqualified contract cannot be marked qualified")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    validate(json.loads(args.contract.read_text(encoding="utf-8")))
    print("validated frozen, unqualified Vero containment contract")


if __name__ == "__main__":
    main()
