#!/usr/bin/env python3
"""Qualify the exact local Leanstral vLLM deployment without mutating its contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
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
        "artifacts": records,
    }


def inspect_vllm_installation(python: Path) -> dict[str, Any]:
    program = r"""
import base64, csv, hashlib, importlib.metadata, json
from pathlib import Path
d = importlib.metadata.distribution("vllm")
record = next((p for p in d.files or () if str(p).endswith(".dist-info/RECORD")), None)
if record is None:
    raise SystemExit("vLLM installation has no RECORD")
record_path = Path(d.locate_file(record))
verified = 0
unhashed = 0
with record_path.open(newline="", encoding="utf-8") as handle:
    for name, declared, size in csv.reader(handle):
        if not declared:
            unhashed += 1
            continue
        algorithm, encoded = declared.split("=", 1)
        if algorithm != "sha256":
            raise SystemExit(f"unsupported package hash: {algorithm}")
        path = Path(d.locate_file(name))
        observed = base64.urlsafe_b64encode(
            hashlib.sha256(path.read_bytes()).digest()
        ).decode().rstrip("=")
        if observed != encoded:
            raise SystemExit(f"vLLM package file changed: {name}")
        if size and path.stat().st_size != int(size):
            raise SystemExit(f"vLLM package size changed: {name}")
        verified += 1
print(json.dumps({
    "exact_version": d.version,
    "record_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
    "verified_files": verified,
    "unhashed_record_entries": unhashed,
}, sort_keys=True))
"""
    completed = subprocess.run(
        [str(python), "-c", program],
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


def validate_live_command(
    command: list[str], contract: dict[str, Any], model_root: Path
) -> dict[str, Any]:
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
    if Path(model_argument(command)).resolve(strict=True) != model_root:
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
    parser.add_argument("--vllm-python", type=Path, required=True)
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
    command = (process_root / "cmdline").read_bytes().split(b"\0")
    command = [item.decode() for item in command if item]
    process_environment = {
        item.partition(b"=")[0].decode(): item.partition(b"=")[2].decode()
        for item in (process_root / "environ").read_bytes().split(b"\0")
        if b"=" in item
    }
    if (
        process_environment.get("HF_HUB_OFFLINE") != "1"
        or process_environment.get("TRANSFORMERS_OFFLINE") != "1"
    ):
        raise DeploymentQualificationError("live server is not frozen to offline model access")
    server_python = (process_root / "exe").resolve(strict=True)
    vllm_python = args.vllm_python.resolve(strict=True)
    server_identity = os.stat(server_python)
    qualification_identity = os.stat(vllm_python)
    if (server_identity.st_dev, server_identity.st_ino) != (
        qualification_identity.st_dev,
        qualification_identity.st_ino,
    ):
        raise DeploymentQualificationError("qualification Python differs from the server runtime")
    model_root = args.model_root.resolve(strict=True)
    deployment = validate_live_command(command, contract, model_root)
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
    installation = inspect_vllm_installation(vllm_python)
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
        "runtime": installation,
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
