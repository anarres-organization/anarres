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
        "container_path": "/model",
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
    if contract["runtime"]["distribution"] != "official_container":
        raise InferenceContractError("inference runtime is not the official container")
    if contract["runtime"]["image"] != "vllm/vllm-openai":
        raise InferenceContractError("inference image is not the official vLLM image")
    if contract["runtime"]["image_digest"] != (
        "sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14"
    ):
        raise InferenceContractError("inference image digest is not frozen")
    if contract["runtime"]["source_revision"] != ("2cf0a6915ce544dc493a0990f2ea38d81601128a"):
        raise InferenceContractError("vLLM source revision is not frozen")
    if contract["runtime"]["required_versions"] != {
        "flashinfer-python": "0.6.16.post3",
        "huggingface-hub": "1.28.0",
        "mistral-common": "1.11.7",
        "safetensors": "0.8.0",
        "tokenizers": "0.22.2",
        "torch": "2.13.0+cu130",
        "transformers": "5.15.1",
        "vllm": "0.28.0",
    }:
        raise InferenceContractError("critical inference package versions are not frozen")
    expected_launch = {
        "max_model_len": 200000,
        "tensor_parallel_size": 2,
        "attention_backend": "FLASHINFER_MLA",
        "tool_call_parser": "mistral",
        "enable_auto_tool_choice": True,
        "reasoning_parser": "mistral",
        "served_model_name": starting_policy["model_id"],
        "tokenizer_mode": "mistral",
        "config_format": "mistral",
        "load_format": "safetensors",
        "seed": 42,
        "enforce_eager": True,
        "language_model_only": True,
        "kernel_config": {
            "enable_flashinfer_autotune": False,
            "enable_cutedsl_warmup": False,
            "enable_jit_warmup": False,
        },
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
