#!/usr/bin/env python3
"""Validate the frozen GPT-5.6 Sol development qualification contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class QualificationError(ValueError):
    """Raised when the qualification contract is inconsistent."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(contract: dict[str, Any], root: Path) -> None:
    if contract["execution_authorized"]:
        raise QualificationError("the preregistration cannot authorize its own execution")

    source = contract["source"]
    for name in ("source_pin", "repository_split", "development_panel"):
        path = root / source[name]
        if digest(path) != source[f"{name}_sha256"]:
            raise QualificationError(f"{name} hash disagrees with the contract")

    panel = json.loads((root / source["development_panel"]).read_text(encoding="utf-8"))
    repositories = panel["repositories"]
    if len(repositories) != 1 or repositories[0]["benchmark_id"] != "primepy":
        raise QualificationError("the qualification must use only the frozen PrimePy panel")
    if repositories[0]["specifications"] != 9:
        raise QualificationError("the frozen PrimePy specification count changed")

    policy = contract["starting_policy"]
    if (policy["model_id"], policy["agent_harness_version"], policy["reasoning_effort"]) != (
        "gpt-5.6-sol",
        "0.154.0",
        "xhigh",
    ):
        raise QualificationError("the selected policy identity changed")

    design = contract["qualification_design"]
    if design["benchmark_id"] != "primepy" or design["mode"] != "proof":
        raise QualificationError("the task identity or mode changed")
    if design["independent_attempts"] != 1 or design["maximum_wall_seconds"] != 5400:
        raise QualificationError("the attempt count or Vero wall budget changed")
    if design["scientific_retry_count"] != 0:
        raise QualificationError("scientific retries must remain disabled")
    if design["task_network_access"]:
        raise QualificationError("the task environment cannot have network access")
    if design["controller_network_scope"] != "model provider only":
        raise QualificationError("the controller network scope changed")
    if design["qualification_and_prospective_repositories_opened"]:
        raise QualificationError("protected repositories cannot be opened")

    gates = contract["required_before_execution"]
    if (
        not gates
        or policy["system_prompt_sha256"] is not None
        or policy["task_prompt_sha256"] is not None
    ):
        raise QualificationError("prompt hashes must be bound in a separate execution receipt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    validate(contract, args.contract.parent)
    print("validated frozen GPT-5.6 Sol development qualification")


if __name__ == "__main__":
    main()
