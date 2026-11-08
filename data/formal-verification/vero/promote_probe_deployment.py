#!/usr/bin/env python3
"""Build a qualified Vero execution bundle from frozen contracts and receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from build_probe_queue import build_queue


class PromotionError(RuntimeError):
    """Raised when deployment evidence cannot authorize the frozen probe."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PromotionError(f"expected an object in {path.name}")
    return value


def sha256_reference(value: str, label: str) -> str:
    normalized = value.removeprefix("sha256:")
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise PromotionError(f"{label} is not a SHA-256 identity")
    return f"sha256:{normalized}"


def promote(
    *,
    protocol: dict[str, Any],
    queue: dict[str, Any],
    panel: dict[str, Any],
    containment: dict[str, Any],
    runtime: dict[str, Any],
    controller: dict[str, Any],
    inference: dict[str, Any],
    containment_receipt: dict[str, Any],
    inference_receipt: dict[str, Any],
    containment_receipt_sha256: str,
    inference_receipt_sha256: str,
    controller_sha256: str,
    pending_inference_sha256: str,
    panel_sha256: str,
    runtime_image: str,
) -> dict[str, dict[str, Any]]:
    if (
        protocol["status"]
        not in {
            "frozen_before_model_attempts",
            "frozen_after_excluded_deployment_pilot_before_claim_attempts",
        }
        or protocol["execution_authorized"]
    ):
        raise PromotionError("promotion requires the frozen, unauthorized probe")
    if queue["status"] != "frozen_before_model_attempts":
        raise PromotionError("promotion requires the frozen queue")
    if containment["status"] != "frozen_unqualified" or containment["qualified"]:
        raise PromotionError("promotion requires the unqualified containment contract")
    if runtime["status"] != "build_and_qualification_pending":
        raise PromotionError("promotion requires the pending runtime lock")
    if inference["status"] != "deployment_pending":
        raise PromotionError("promotion requires the pending inference contract")

    runtime_image = sha256_reference(runtime_image, "runtime image")
    model_digest = sha256_reference(
        inference_receipt["model"]["local_artifact_digest"], "model artifact"
    )
    expected_tests = {record["id"] for record in containment["required_tests"]}
    observed_tests = {
        record["id"] for record in containment_receipt["tests"] if record.get("passed") is True
    }
    if (
        containment_receipt.get("qualified") is not True
        or containment_receipt["contract_id"] != containment["contract_id"]
        or observed_tests != expected_tests
        or len(containment_receipt["tests"]) != len(expected_tests)
        or containment_receipt["controller_lock_sha256"] != controller_sha256
        or containment_receipt["inference_contract_sha256"] != pending_inference_sha256
        or containment_receipt["runtime_image"] != runtime_image
        or containment_receipt["runtime_image_id"] != runtime_image
        or containment_receipt["model_artifact_digest"] != model_digest
        or containment_receipt["vibe_source_revision"]
        != containment["interface"]["agent_scaffold_revision"]
        or containment_receipt["task_pre_sha256"] != containment_receipt["task_post_sha256"]
    ):
        raise PromotionError("containment receipt does not qualify the frozen deployment")

    inference_runtime = inference_receipt["runtime"]
    container = inference_runtime["container"]
    if (
        inference_receipt.get("qualified") is not True
        or inference_receipt["inference_id"] != inference["inference_id"]
        or inference_receipt["model"]["id"] != inference["model"]["id"]
        or inference_receipt["model"]["revision"] != inference["model"]["revision"]
        or inference_runtime["package_versions"] != inference["runtime"]["required_versions"]
        or container["image_digest"] != inference["runtime"]["image_digest"]
        or controller["api_base"] != inference["endpoint"]["api_base"]
        or inference_receipt["endpoint"]["api_base"] != inference["endpoint"]["api_base"]
        or inference_receipt["endpoint"]["chat_completion_smoke"] != "pass"
        or inference_receipt["endpoint"]["tool_call_parser_smoke"] != "pass"
    ):
        raise PromotionError("inference receipt does not qualify the frozen deployment")

    qualified_containment = json.loads(json.dumps(containment))
    qualified_containment["status"] = "qualified"
    qualified_containment["qualified"] = True
    for record in qualified_containment["required_tests"]:
        record["status"] = "pass"
    qualified_containment["qualification_receipt_sha256"] = f"sha256:{containment_receipt_sha256}"

    qualified_runtime = json.loads(json.dumps(runtime))
    qualified_runtime.update(
        {
            "status": "qualified",
            "built_image_reference": runtime_image,
            "built_image_id": runtime_image,
            "qualification_receipt": f"sha256:{containment_receipt_sha256}",
        }
    )

    qualified_inference = json.loads(json.dumps(inference))
    qualified_inference["status"] = "qualified"
    qualified_inference["model"]["local_artifact_digest"] = model_digest
    qualified_inference["runtime"]["exact_version"] = inference_runtime["exact_version"]
    installation = {key: value for key, value in inference_runtime.items() if key != "container"}
    qualified_inference["runtime"]["installation_digest"] = (
        f"sha256:{canonical_digest(installation)}"
    )
    qualified_inference["deployment_configuration"] = inference_receipt["deployment_configuration"]
    qualified_inference["qualification"] = {
        "runtime_receipt": f"sha256:{inference_receipt_sha256}",
        "readiness_receipt": f"sha256:{inference_receipt_sha256}",
    }

    qualified_protocol = json.loads(json.dumps(protocol))
    qualified_protocol["status"] = "frozen_ready"
    qualified_protocol["execution_authorized"] = True
    qualified_protocol["starting_policy"]["local_artifact_digest"] = model_digest
    interface = qualified_protocol["execution_interface"]
    interface["containment_contract_sha256"] = canonical_file_digest(qualified_containment)
    interface["runtime_dockerfile_sha256"] = qualified_runtime["dockerfile_sha256"]
    interface["controller_lock_sha256"] = controller_sha256
    interface["inference_contract_sha256"] = canonical_file_digest(qualified_inference)
    gates = qualified_protocol["admission_gates"]
    gates["satisfied_before_execution"] = gates["required_before_execution"]
    gates["required_before_execution"] = []
    qualified_protocol["deployment_qualification"] = {
        "containment_receipt_sha256": f"sha256:{containment_receipt_sha256}",
        "inference_receipt_sha256": f"sha256:{inference_receipt_sha256}",
    }

    protocol_sha256 = canonical_file_digest(qualified_protocol)
    qualified_queue = build_queue(
        qualified_protocol,
        panel,
        protocol_sha256=protocol_sha256,
        panel_sha256=panel_sha256,
    )
    if qualified_queue["attempts"] != queue["attempts"]:
        raise PromotionError("promotion changed frozen queue attempts")
    return {
        "containment": qualified_containment,
        "runtime": qualified_runtime,
        "inference": qualified_inference,
        "protocol": qualified_protocol,
        "queue": qualified_queue,
    }


def render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def canonical_file_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(render(value)).hexdigest()


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(render(value))
    path.chmod(0o600)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--containment", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    parser.add_argument("--inference-contract", type=Path, required=True)
    parser.add_argument("--containment-receipt", type=Path, required=True)
    parser.add_argument("--inference-receipt", type=Path, required=True)
    parser.add_argument("--runtime-image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise PromotionError("--output must not exist")
    source_paths = (
        args.protocol,
        args.queue,
        args.panel,
        args.containment,
        args.runtime_lock,
        args.controller_lock,
        args.inference_contract,
        args.containment_receipt,
        args.inference_receipt,
    )
    for path in source_paths:
        if not path.is_file():
            raise PromotionError(f"required file does not exist: {path}")
    promoted = promote(
        protocol=read_object(args.protocol),
        queue=read_object(args.queue),
        panel=read_object(args.panel),
        containment=read_object(args.containment),
        runtime=read_object(args.runtime_lock),
        controller=read_object(args.controller_lock),
        inference=read_object(args.inference_contract),
        containment_receipt=read_object(args.containment_receipt),
        inference_receipt=read_object(args.inference_receipt),
        containment_receipt_sha256=digest(args.containment_receipt),
        inference_receipt_sha256=digest(args.inference_receipt),
        controller_sha256=digest(args.controller_lock),
        pending_inference_sha256=digest(args.inference_contract),
        panel_sha256=digest(args.panel),
        runtime_image=args.runtime_image,
    )
    output_parent = args.output.parent.resolve(strict=True)
    temporary = Path(tempfile.mkdtemp(prefix="anarres-vero-promotion-", dir=output_parent))
    try:
        write(temporary / args.containment.name, promoted["containment"])
        write(temporary / "runtime" / args.runtime_lock.name, promoted["runtime"])
        write(temporary / "inference" / args.inference_contract.name, promoted["inference"])
        write(temporary / args.protocol.name, promoted["protocol"])
        write(temporary / args.queue.name, promoted["queue"])
        shutil.copy2(args.protocol.parent / "agent-prompt.txt", temporary / "agent-prompt.txt")
        shutil.copytree(
            args.controller_lock.parent,
            temporary / "controller",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copy2(args.runtime_lock.parent / "Dockerfile", temporary / "runtime" / "Dockerfile")
        promotion_receipt = {
            "schema_version": "anarres.formal-verification-deployment-promotion.v1",
            "promoted_at": datetime.now(UTC).isoformat(),
            "source_protocol_sha256": digest(args.protocol),
            "containment_receipt_sha256": digest(args.containment_receipt),
            "inference_receipt_sha256": digest(args.inference_receipt),
            "qualified_protocol_sha256": canonical_file_digest(promoted["protocol"]),
            "qualified_queue_sha256": canonical_file_digest(promoted["queue"]),
            "attempts": len(promoted["queue"]["attempts"]),
        }
        write(temporary / "promotion-receipt.json", promotion_receipt)
        os.replace(temporary, args.output)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    print(
        f"wrote qualified Vero execution bundle with {len(promoted['queue']['attempts'])} attempts"
    )


if __name__ == "__main__":
    main()
