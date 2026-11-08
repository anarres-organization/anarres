#!/usr/bin/env python3
"""Qualify the exact local Leanstral vLLM deployment without mutating its contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


class DeploymentQualificationError(RuntimeError):
    """Raised when the live inference deployment disagrees with the frozen contract."""


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DeploymentQualificationError(f"expected an object in {path.name}")
    return value


def flag_value(command: list[str], flag: str) -> str | None:
    for index, item in enumerate(command):
        if item == flag:
            if index + 1 >= len(command):
                raise DeploymentQualificationError(f"missing value after {flag}")
            return command[index + 1]
        if item.startswith(f"{flag}="):
            return item.split("=", 1)[1]
    return None


def require_flag(command: list[str], flag: str, expected: str) -> None:
    if flag_value(command, flag) != expected:
        raise DeploymentQualificationError(f"live process disagrees with {flag}")


def model_argument(command: list[str]) -> str:
    try:
        serve = command.index("serve")
    except ValueError as error:
        raise DeploymentQualificationError("live process is not a vLLM serve command") from error
    for item in command[serve + 1 :]:
        if not item.startswith("-"):
            return item
    raise DeploymentQualificationError("vLLM serve command has no model argument")


def artifact_manifest(root: Path) -> dict[str, Any]:
    records = []
    total_bytes = 0
    paths = (
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file() and candidate.relative_to(root).parts[0] != ".cache"
    )
    for path in sorted(paths):
        file_hash = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                file_hash.update(chunk)
                size += len(chunk)
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": file_hash.hexdigest(),
            }
        )
        total_bytes += size
    if not records:
        raise DeploymentQualificationError("local model artifact is empty")
    identity = hashlib.sha256()
    for record in records:
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        identity.update(len(encoded).to_bytes(8, "big"))
        identity.update(encoded)
    return {
        "schema_version": "anarres.model-artifact-manifest.v1",
        "root_sha256": identity.hexdigest(),
        "files": len(records),
        "bytes": total_bytes,
        "excluded_roots": [".cache"],
        "artifacts": records,
    }


def inspect_installation(command: list[str]) -> dict[str, Any]:
    program = r"""
import hashlib, importlib.metadata, json
from pathlib import Path
package_names = (
    "flashinfer-python",
    "huggingface-hub",
    "mistral-common",
    "safetensors",
    "tokenizers",
    "torch",
    "transformers",
    "vllm",
)

def inspect_distribution(package_name):
    distribution = importlib.metadata.distribution(package_name)
    metadata = next(
        (p for p in distribution.files or () if str(p).endswith(".dist-info/METADATA")),
        None,
    )
    record = next(
        (p for p in distribution.files or () if str(p).endswith(".dist-info/RECORD")),
        None,
    )
    if metadata is None or record is None:
        raise SystemExit(f"{package_name} installation lacks package metadata")
    metadata_path = Path(distribution.locate_file(metadata))
    record_path = Path(distribution.locate_file(record))
    return {
        "version": distribution.version,
        "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "record_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
        "declared_files": len(distribution.files or ()),
    }

package_metadata = {name: inspect_distribution(name) for name in package_names}
print(json.dumps({
    "exact_version": package_metadata["vllm"]["version"],
    "package_versions": {
        name: metadata["version"] for name, metadata in package_metadata.items()
    },
    "package_metadata": package_metadata,
}, sort_keys=True))
"""
    completed = subprocess.run(
        [*command, "-c", program],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise DeploymentQualificationError(
            f"could not verify vLLM installation: {completed.stderr.strip()}"
        )
    return json.loads(completed.stdout)


def docker_json(arguments: list[str]) -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["docker", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise DeploymentQualificationError(f"Docker inspection failed: {completed.stderr.strip()}")
    value = json.loads(completed.stdout)
    if not isinstance(value, list) or not value or not isinstance(value[0], dict):
        raise DeploymentQualificationError("Docker inspection returned an invalid record")
    return value


def validate_container_metadata(
    container: dict[str, Any],
    image: dict[str, Any],
    contract: dict[str, Any],
    server_pid: int,
    model_root: Path,
) -> tuple[list[str], dict[str, str], dict[str, Any]]:
    runtime = contract["runtime"]
    expected_reference = f"{runtime['image']}@{runtime['image_digest']}"
    if not container.get("State", {}).get("Running"):
        raise DeploymentQualificationError("inference container is not running")
    if container["State"].get("Pid") != server_pid:
        raise DeploymentQualificationError("server PID is not the container init process")
    if container.get("Image") != image.get("Id"):
        raise DeploymentQualificationError("container does not use the inspected image")
    if expected_reference not in image.get("RepoDigests", []):
        raise DeploymentQualificationError("container image digest disagrees with the contract")
    labels = image.get("Config", {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != runtime["source_revision"]:
        raise DeploymentQualificationError("container source revision disagrees")
    host_config = container.get("HostConfig", {})
    if host_config.get("NetworkMode") != "host":
        raise DeploymentQualificationError("inference container does not use host networking")
    if host_config.get("IpcMode") != "host":
        raise DeploymentQualificationError("inference container does not use host IPC")
    device_requests = host_config.get("DeviceRequests") or []
    device_ids = [
        device
        for request in device_requests
        if ["gpu"] in request.get("Capabilities", [])
        for device in request.get("DeviceIDs") or []
    ]
    expected_devices = contract["required_launch_configuration"]["tensor_parallel_size"]
    if len(device_ids) != expected_devices or len(set(device_ids)) != expected_devices:
        raise DeploymentQualificationError("container GPU assignment disagrees with TP size")
    expected_destination = contract["model"]["container_path"]
    model_mounts = [
        mount
        for mount in container.get("Mounts", [])
        if mount.get("Destination") == expected_destination
    ]
    if len(model_mounts) != 1:
        raise DeploymentQualificationError("container has no unique model mount")
    model_mount = model_mounts[0]
    if Path(model_mount.get("Source", "")).resolve(strict=True) != model_root:
        raise DeploymentQualificationError("container mounts a different model artifact")
    if model_mount.get("RW"):
        raise DeploymentQualificationError("container model mount is writable")
    command = [container.get("Path", ""), *container.get("Args", [])]
    if not command[0]:
        raise DeploymentQualificationError("container command is empty")
    environment = {}
    for item in container.get("Config", {}).get("Env") or []:
        name, separator, value = item.partition("=")
        if separator:
            environment[name] = value
    identity = {
        "image": runtime["image"],
        "image_digest": runtime["image_digest"],
        "image_id": image["Id"],
        "source_revision": labels["org.opencontainers.image.revision"],
        "device_ids": device_ids,
    }
    return command, environment, identity


def inspect_container_runtime(
    container_name: str,
    contract: dict[str, Any],
    server_pid: int,
    model_root: Path,
) -> tuple[list[str], dict[str, str], dict[str, Any]]:
    container = docker_json(["inspect", container_name])[0]
    image_reference = f"{contract['runtime']['image']}@{contract['runtime']['image_digest']}"
    image = docker_json(["image", "inspect", image_reference])[0]
    return validate_container_metadata(container, image, contract, server_pid, model_root)


def inspect_container_installation(container_name: str) -> dict[str, Any]:
    return inspect_installation(["docker", "exec", container_name, "python3"])


def request_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=120) as response:  # noqa: S310
            value = json.load(response)
    except OSError as error:
        raise DeploymentQualificationError(f"inference endpoint failed: {url}") from error
    if not isinstance(value, dict):
        raise DeploymentQualificationError("inference endpoint returned a non-object")
    return value


def validate_live_command(command: list[str], contract: dict[str, Any]) -> dict[str, Any]:
    required = contract["required_launch_configuration"]
    require_flag(command, "--host", contract["endpoint"]["host"])
    require_flag(command, "--port", str(contract["endpoint"]["port"]))
    require_flag(command, "--max-model-len", str(required["max_model_len"]))
    require_flag(command, "--tensor-parallel-size", str(required["tensor_parallel_size"]))
    require_flag(command, "--attention-backend", required["attention_backend"])
    require_flag(command, "--tool-call-parser", required["tool_call_parser"])
    require_flag(command, "--reasoning-parser", required["reasoning_parser"])
    require_flag(command, "--served-model-name", required["served_model_name"])
    require_flag(command, "--tokenizer-mode", required["tokenizer_mode"])
    require_flag(command, "--config-format", required["config_format"])
    require_flag(command, "--load-format", required["load_format"])
    require_flag(command, "--seed", str(required["seed"]))
    kernel_config = flag_value(command, "--kernel-config")
    if kernel_config is None or json.loads(kernel_config) != required["kernel_config"]:
        raise DeploymentQualificationError("live process has the wrong kernel configuration")
    if "--enable-auto-tool-choice" not in command:
        raise DeploymentQualificationError("live process lacks --enable-auto-tool-choice")
    if required["enforce_eager"] and "--enforce-eager" not in command:
        raise DeploymentQualificationError("live process lacks --enforce-eager")
    if required["language_model_only"] and "--language-model-only" not in command:
        raise DeploymentQualificationError("live process lacks --language-model-only")
    if model_argument(command) != contract["model"]["container_path"]:
        raise DeploymentQualificationError("live process serves a different local model artifact")
    gpu_memory = flag_value(command, "--gpu-memory-utilization")
    max_sequences = flag_value(command, "--max-num-seqs")
    dtype = flag_value(command, "--dtype")
    if gpu_memory is None or max_sequences is None or dtype is None:
        raise DeploymentQualificationError("live process omits a deployment-capacity flag")
    gpu_memory_value = float(gpu_memory)
    max_sequences_value = int(max_sequences)
    if not 0 < gpu_memory_value <= 1 or max_sequences_value <= 0:
        raise DeploymentQualificationError("live process has invalid capacity settings")
    observed = {
        "replicas": 1,
        "gpu_memory_utilization": gpu_memory_value,
        "max_num_seqs": max_sequences_value,
        "dtype": dtype,
    }
    return observed


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
    if match is None:
        raise DeploymentQualificationError(f"could not parse version: {value}")
    return tuple(int(part) for part in match.groups())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--resolved-revision", required=True)
    parser.add_argument("--maximum-concurrent-attempts", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise DeploymentQualificationError("--output must not exist")
    if args.maximum_concurrent_attempts <= 0:
        raise DeploymentQualificationError("maximum concurrency must be positive")
    contract = read_object(args.contract)
    protocol = read_object(args.protocol)
    controller = read_object(args.controller_lock)
    if contract["status"] != "deployment_pending":
        raise DeploymentQualificationError("qualification requires the pending contract")
    if args.resolved_revision != contract["model"]["revision"]:
        raise DeploymentQualificationError("resolved model revision disagrees with the contract")
    if contract["endpoint"]["api_base"] != controller["api_base"]:
        raise DeploymentQualificationError("controller and inference endpoints disagree")
    if contract["model"]["id"] != protocol["starting_policy"]["model_id"]:
        raise DeploymentQualificationError("protocol and inference model identities disagree")

    process_root = Path(f"/proc/{args.server_pid}")
    if not process_root.is_dir():
        raise DeploymentQualificationError("vLLM server PID is not running")
    model_root = args.model_root.resolve(strict=True)
    command, process_environment, container_identity = inspect_container_runtime(
        args.container, contract, args.server_pid, model_root
    )
    if (
        process_environment.get("HF_HUB_OFFLINE") != "1"
        or process_environment.get("TRANSFORMERS_OFFLINE") != "1"
    ):
        raise DeploymentQualificationError("live server is not frozen to offline model access")
    deployment = validate_live_command(command, contract)
    if args.maximum_concurrent_attempts > deployment["max_num_seqs"]:
        raise DeploymentQualificationError("attempt concurrency exceeds vLLM sequence capacity")
    deployment["maximum_concurrent_attempts_per_replica"] = args.maximum_concurrent_attempts

    output = args.output.absolute()
    output.mkdir(mode=0o700, parents=True)
    model_manifest = artifact_manifest(model_root)
    manifest_path = output / "model-artifact-manifest.json"
    manifest_path.write_text(
        json.dumps(model_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    installation = inspect_container_installation(args.container)
    if installation["package_versions"] != contract["runtime"]["required_versions"]:
        raise DeploymentQualificationError("critical inference package versions disagree")
    if version_tuple(installation["exact_version"]) < version_tuple(
        contract["runtime"]["minimum_version"]
    ):
        raise DeploymentQualificationError("vLLM version is below the frozen minimum")
    models = request_json(f"{contract['endpoint']['api_base']}/models")
    served_ids = [record.get("id") for record in models.get("data", [])]
    if contract["model"]["id"] not in served_ids:
        raise DeploymentQualificationError("endpoint does not expose the frozen model identity")
    smoke = request_json(
        f"{contract['endpoint']['api_base']}/chat/completions",
        {
            "model": contract["model"]["id"],
            "messages": [{"role": "user", "content": "Reply with the single word OK."}],
            "temperature": 0,
            "max_tokens": 16,
        },
    )
    if not smoke.get("choices") or not isinstance(smoke.get("usage"), dict):
        raise DeploymentQualificationError("chat-completion smoke lacks choices or usage")
    tool_smoke = request_json(
        f"{contract['endpoint']['api_base']}/chat/completions",
        {
            "model": contract["model"]["id"],
            "messages": [
                {
                    "role": "user",
                    "content": "Call read_file for /workspace/INSTRUCTION.md.",
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "Read one file",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "read_file"}},
            "temperature": 0,
            "max_tokens": 128,
        },
    )
    try:
        tool_call = tool_smoke["choices"][0]["message"]["tool_calls"][0]["function"]
        tool_arguments = json.loads(tool_call["arguments"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise DeploymentQualificationError(
            "tool-call parser smoke did not return a call"
        ) from error
    if tool_call["name"] != "read_file" or tool_arguments.get("path") != (
        "/workspace/INSTRUCTION.md"
    ):
        raise DeploymentQualificationError("tool-call parser smoke returned the wrong call")

    receipt = {
        "schema_version": "anarres.formal-verification-inference-qualification.v1",
        "inference_id": contract["inference_id"],
        "qualified": True,
        "qualified_at": datetime.now(UTC).isoformat(),
        "model": {
            "id": contract["model"]["id"],
            "revision": args.resolved_revision,
            "local_artifact_digest": f"sha256:{model_manifest['root_sha256']}",
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "files": model_manifest["files"],
            "bytes": model_manifest["bytes"],
        },
        "runtime": {**installation, "container": container_identity},
        "deployment_configuration": deployment,
        "endpoint": {
            "api_base": contract["endpoint"]["api_base"],
            "served_model_ids": served_ids,
            "chat_completion_smoke": "pass",
            "tool_call_parser_smoke": "pass",
        },
        "live_process": {
            "pid": args.server_pid,
            "command_sha256": hashlib.sha256(
                b"\0".join(item.encode() for item in command)
            ).hexdigest(),
        },
    }
    (output / "inference-qualification-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("qualified exact local Leanstral vLLM deployment")


if __name__ == "__main__":
    main()
