#!/usr/bin/env python3
"""Validate the frozen Vero development policy-probe contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class ProtocolError(ValueError):
    """Raised when the frozen probe contract is internally inconsistent."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(
    protocol: dict[str, Any],
    panel: dict[str, Any],
    split: dict[str, Any],
    *,
    panel_path: Path,
    split_path: Path,
    containment_path: Path,
    runtime_lock_path: Path,
    controller_lock_path: Path,
    inference_contract_path: Path,
) -> None:
    prompt_path = panel_path.parent / protocol["starting_policy"]["user_prompt"]
    if digest(prompt_path) != protocol["starting_policy"]["user_prompt_sha256"]:
        raise ProtocolError("the user-prompt hash disagrees with the protocol")
    source = protocol["source"]
    if digest(panel_path) != source["development_panel_sha256"]:
        raise ProtocolError("the development panel hash disagrees with the protocol")
    if digest(split_path) != source["repository_split_sha256"]:
        raise ProtocolError("the repository split hash disagrees with the protocol")
    if panel["source_id"] != source["vero_id"]:
        raise ProtocolError("the development panel and protocol identify different sources")

    by_id = {record["benchmark_id"]: record for record in split["repositories"]}
    selected = panel["repositories"]
    if protocol["probe_design"]["repositories"] != len(selected):
        raise ProtocolError("the protocol has an incorrect repository count")
    if len({record["source_language"] for record in selected}) != len(selected):
        raise ProtocolError("the development panel must contain one repository per language")
    for record in selected:
        frozen = by_id.get(record["benchmark_id"])
        if frozen is None or frozen["split"] != "development":
            raise ProtocolError("the policy probe contains a non-development repository")
        for field in ("directory", "source_language", "specifications"):
            if record[field] != frozen[field]:
                raise ProtocolError(f"panel and split disagree on {field}")

    design = protocol["probe_design"]
    expected = (
        len(selected) * len(design["modes"]) * design["independent_attempts_per_repository_mode"]
    )
    if design["total_attempts"] != expected:
        raise ProtocolError("the protocol has an incorrect total attempt count")
    if (
        protocol["execution_authorized"]
        and protocol["admission_gates"]["required_before_execution"]
    ):
        raise ProtocolError("execution cannot be authorized with unresolved pre-run gates")

    interface = protocol["execution_interface"]
    if interface["vibe_agent_socket_protocol_version"] != 2:
        raise ProtocolError("the probe must use the pinned Vibe agent-socket protocol")
    if interface["model_facing_tools_execute_on_controller_host"]:
        raise ProtocolError("model-facing tools cannot execute on the controller host")
    if set(interface["sandbox_methods"]) != {"sandbox/execute", "sandbox/readFile"}:
        raise ProtocolError("the probe has an unexpected model-facing sandbox interface")
    if containment_path.name != interface["containment_contract"]:
        raise ProtocolError("the containment contract name disagrees with the protocol")
    if digest(containment_path) != interface["containment_contract_sha256"]:
        raise ProtocolError("the containment contract hash disagrees with the protocol")
    if not runtime_lock_path.as_posix().endswith(interface["runtime_lock"]):
        raise ProtocolError("the runtime-lock path disagrees with the protocol")
    runtime_lock = json.loads(runtime_lock_path.read_text(encoding="utf-8"))
    if runtime_lock["dockerfile_sha256"] != interface["runtime_dockerfile_sha256"]:
        raise ProtocolError("the runtime Dockerfile hash disagrees with the protocol")
    if not controller_lock_path.as_posix().endswith(interface["controller_lock"]):
        raise ProtocolError("the controller-lock path disagrees with the protocol")
    if digest(controller_lock_path) != interface["controller_lock_sha256"]:
        raise ProtocolError("the controller-lock hash disagrees with the protocol")
    if not inference_contract_path.as_posix().endswith(interface["inference_contract"]):
        raise ProtocolError("the inference-contract path disagrees with the protocol")
    if digest(inference_contract_path) != interface["inference_contract_sha256"]:
        raise ProtocolError("the inference-contract hash disagrees with the protocol")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--containment", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    parser.add_argument("--inference-contract", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    validate(
        protocol,
        json.loads(args.panel.read_text(encoding="utf-8")),
        json.loads(args.split.read_text(encoding="utf-8")),
        panel_path=args.panel,
        split_path=args.split,
        containment_path=args.containment,
        runtime_lock_path=args.runtime_lock,
        controller_lock_path=args.controller_lock,
        inference_contract_path=args.inference_contract,
    )
    print("validated frozen Vero development policy-probe protocol")


if __name__ == "__main__":
    main()
