#!/usr/bin/env python3
"""Validate the local Leanstral inference contract for the Vero probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class InferenceContractError(ValueError):
    """Raised when the inference contract is incomplete or inconsistent."""


def validate(contract: dict[str, Any], *, protocol_path: Path, controller_lock_path: Path) -> None:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    controller = json.loads(controller_lock_path.read_text(encoding="utf-8"))
    starting_policy = protocol["starting_policy"]

    if contract["model"] != {
        "id": starting_policy["model_id"],
        "revision": starting_policy["model_revision"],
        "local_artifact_digest": starting_policy["local_artifact_digest"],
    }:
        raise InferenceContractError("model identity disagrees with the probe protocol")
    endpoint = contract["endpoint"]
    controller_endpoint = urlparse(controller["api_base"])
    if controller_endpoint.port is None:
        raise InferenceContractError("controller endpoint has no explicit port")
    if endpoint != {
        "host": "127.0.0.1",
        "port": controller_endpoint.port,
        "api_base": controller["api_base"],
        "external_network_exposure": False,
    }:
        raise InferenceContractError("inference endpoint is not frozen to loopback")
    if contract["runtime"]["name"] != "vllm":
        raise InferenceContractError("unsupported inference runtime")
    if contract["runtime"]["minimum_version"] != "0.24.0":
        raise InferenceContractError("vLLM minimum version disagrees with the model card")
    expected_launch = {
        "max_model_len": 200000,
        "tensor_parallel_size": 4,
        "attention_backend": "FLASH_ATTN_MLA",
        "tool_call_parser": "mistral",
        "enable_auto_tool_choice": True,
        "reasoning_parser": "mistral",
        "served_model_name": starting_policy["model_id"],
        "model_source_offline_after_resolution": True,
    }
    if contract["required_launch_configuration"] != expected_launch:
        raise InferenceContractError("required launch configuration is not frozen")

    if contract["status"] == "deployment_pending":
        pending = [
            contract["model"]["local_artifact_digest"],
            contract["runtime"]["exact_version"],
            contract["runtime"]["installation_digest"],
            *contract["deployment_configuration"].values(),
            *contract["qualification"].values(),
        ]
        if any(value is not None for value in pending):
            raise InferenceContractError("pending contract contains deployment results")
    elif contract["status"] == "qualified":
        required = [
            contract["model"]["local_artifact_digest"],
            contract["runtime"]["exact_version"],
            contract["runtime"]["installation_digest"],
            *contract["deployment_configuration"].values(),
            *contract["qualification"].values(),
        ]
        if any(value is None for value in required):
            raise InferenceContractError("qualified contract lacks deployment evidence")
    else:
        raise InferenceContractError("unknown inference-contract status")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    args = parser.parse_args()
    validate(
        json.loads(args.contract.read_text(encoding="utf-8")),
        protocol_path=args.protocol,
        controller_lock_path=args.controller_lock,
    )
    print("validated frozen, pre-deployment Leanstral inference contract")


if __name__ == "__main__":
    main()
