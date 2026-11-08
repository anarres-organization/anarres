#!/usr/bin/env python3
"""Qualify the exact Vero container, controller, and agent-socket boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from materialize_probe_task import tree_digest
from run_probe_attempt import build_vibe_home, isolated_environment, stop_server, wait_for_socket


class QualificationError(RuntimeError):
    """Raised when containment qualification cannot complete."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QualificationError(f"expected an object in {path.name}")
    return value


def rpc(socket_path: Path, method: str, params: dict[str, Any], request_id: int) -> dict[str, Any]:
    request = (
        json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(30)
        connection.connect(str(socket_path))
        connection.sendall(request)
        retained = bytearray()
        while not retained.endswith(b"\n"):
            chunk = connection.recv(64 * 1024)
            if not chunk:
                break
            retained.extend(chunk)
    response = json.loads(retained)
    if not isinstance(response, dict):
        raise QualificationError("agent-socket response is not an object")
    return response


def execute(
    socket_path: Path, command: str, request_id: int, timeout: float = 30
) -> dict[str, Any]:
    response = rpc(
        socket_path,
        "sandbox/execute",
        {"command": command, "cwd": "/workspace", "timeout": timeout},
        request_id,
    )
    if "error" in response:
        raise QualificationError(response["error"]["message"])
    return response["result"]


def result(test_id: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"id": test_id, "passed": passed, "evidence": evidence}


def inspect_container(docker: str, container_name: str) -> dict[str, Any]:
    completed = subprocess.run(
        [docker, "inspect", container_name],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise QualificationError("could not inspect qualification container")
    return json.loads(completed.stdout)[0]


def host_inference_ready(api_base: str) -> bool:
    try:
        with urlopen(f"{api_base}/models", timeout=10) as response:  # noqa: S310
            return response.status == 200
    except OSError:
        return False


def verify_vibe_source(source: Path, expected_revision: str, vibe: Path) -> str:
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    if revision != expected_revision:
        raise QualificationError("Vibe checkout disagrees with the controller lock")
    if not vibe.resolve(strict=True).is_relative_to(source.resolve(strict=True)):
        raise QualificationError("Vibe executable must be installed inside the pinned checkout")
    return revision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--reset-workspace", type=Path, required=True)
    parser.add_argument("--materialization-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--model-artifact-digest", required=True)
    parser.add_argument("--inference-contract", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    parser.add_argument("--containment", type=Path, required=True)
    parser.add_argument("--vibe", type=Path, required=True)
    parser.add_argument("--vibe-source", type=Path, required=True)
    parser.add_argument("--sandbox-server", type=Path, required=True)
    parser.add_argument("--docker", default="docker")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output.absolute()
    if output.exists():
        raise QualificationError("--output must not exist")
    output.mkdir(mode=0o700, parents=True)
    work_parent = args.work_root.resolve(strict=True)
    workspace = args.workspace.resolve(strict=True)
    reset_workspace = args.reset_workspace.resolve(strict=True)
    if workspace == reset_workspace:
        raise QualificationError("qualification requires two independent task materializations")

    containment = read_json(args.containment)
    controller = read_json(args.controller_lock)
    inference = read_json(args.inference_contract)
    runtime = read_json(args.runtime_lock)
    materialization = read_json(args.materialization_receipt)
    expected_tests = [record["id"] for record in containment["required_tests"]]
    if containment["qualified"] or containment["status"] != "frozen_unqualified":
        raise QualificationError("qualification requires the frozen, unqualified contract")
    if (
        runtime["dockerfile_sha256"]
        != hashlib.sha256(
            (args.runtime_lock.parent / runtime["dockerfile"]).read_bytes()
        ).hexdigest()
    ):
        raise QualificationError("runtime Dockerfile disagrees with its lock")
    if inference["status"] != "deployment_pending":
        raise QualificationError("qualification must begin from the pending inference contract")
    if inference["model"]["local_artifact_digest"] is not None:
        raise QualificationError("pending inference contract already contains a model digest")

    pre_hash = tree_digest(workspace)
    reset_hash = tree_digest(reset_workspace)
    if pre_hash != materialization["task_tree_sha256"] or reset_hash != pre_hash:
        raise QualificationError("qualification tasks do not match the materialization receipt")
    vibe = args.vibe.resolve(strict=True)
    vibe_revision = verify_vibe_source(
        args.vibe_source,
        controller["agent_scaffold_revision"],
        vibe,
    )
    inference_digest = digest(args.inference_contract)
    results: list[dict[str, Any]] = []
    started_at = utc_now()
    server_receipt_path = output / "sandbox-receipt.json"

    with tempfile.TemporaryDirectory(prefix="anarres-vero-qualification-", dir=work_parent) as temp:
        work = Path(temp)
        socket_path = work / "socket" / "agent.sock"
        container_name_file = work / "container-name"
        server_stdout = (output / "sandbox.stdout").open("wb")
        server_stderr = (output / "sandbox.stderr").open("wb")
        server_environment = dict(os.environ)
        server_environment["ANARRES_HOST_CREDENTIAL_SENTINEL"] = "must-not-enter-container"
        server_command = [
            sys.executable,
            str(args.sandbox_server.resolve(strict=True)),
            "--socket",
            str(socket_path),
            "--image",
            args.image,
            "--workspace",
            str(workspace),
            "--receipt",
            str(server_receipt_path),
            "--container-name-file",
            str(container_name_file),
            "--attempt-id",
            "containment-qualification",
            "--task-id",
            f"qualification:{materialization['benchmark_id']}:{materialization['mode']}",
            "--model-artifact-digest",
            args.model_artifact_digest,
            "--inference-config-digest",
            inference_digest,
            "--docker",
            args.docker,
        ]
        server = subprocess.Popen(
            server_command,
            env=server_environment,
            stdout=server_stdout,
            stderr=server_stderr,
        )
        try:
            wait_for_socket(socket_path, server)
            initialized = rpc(
                socket_path,
                "agent/initialize",
                {"protocolVersion": 2, "vibeVersion": "3.1.0"},
                1,
            )
            if initialized.get("result", {}).get("workspace") != "/workspace":
                raise QualificationError("agent socket exposed the wrong workspace")
            if not container_name_file.is_file():
                raise QualificationError("sandbox server did not publish its container identity")
            container_name = container_name_file.read_text(encoding="utf-8").strip()
            inspected = inspect_container(args.docker, container_name)
            host_config = inspected["HostConfig"]
            mounts = inspected["Mounts"]
            mount_summary = [
                {"type": mount["Type"], "destination": mount["Destination"], "rw": mount["RW"]}
                for mount in mounts
            ]
            workspace_passed = (
                host_config["NetworkMode"] == "none"
                and host_config["ReadonlyRootfs"] is True
                and "ALL" in (host_config.get("CapDrop") or [])
                and "no-new-privileges" in (host_config.get("SecurityOpt") or [])
                and mount_summary == [{"type": "bind", "destination": "/workspace", "rw": True}]
                and set((host_config.get("Tmpfs") or {}).keys()) == {"/tmp", "/cache"}
            )
            results.append(
                result(
                    "workspace_allowlist",
                    workspace_passed,
                    {"mounts": mount_summary, "read_only_root": host_config["ReadonlyRootfs"]},
                )
            )

            with tempfile.TemporaryDirectory(dir=workspace.parent) as outside:
                sentinel = Path(outside) / "host-only-sentinel"
                sentinel.write_text("host-only", encoding="utf-8")
                link = workspace / "host-escape"
                link.symlink_to(sentinel)
                try:
                    read_response = rpc(
                        socket_path,
                        "sandbox/readFile",
                        {"path": "/workspace/host-escape", "maxBytes": 1024},
                        2,
                    )
                    parent = execute(
                        socket_path,
                        f"test ! -e /workspace/../{sentinel.name}",
                        3,
                    )
                    escape_passed = (
                        read_response.get("result", {}).get("contentBase64") is None
                        and parent["exitCode"] == 0
                    )
                finally:
                    link.unlink(missing_ok=True)
            results.append(
                result("path_and_symlink_escape", escape_passed, {"escape_blocked": True})
            )

            environment = execute(socket_path, "env", 4)
            environment_text = environment["stdout"]
            forbidden_environment = (
                "ANARRES_HOST_CREDENTIAL_SENTINEL",
                "SSH_AUTH_SOCK=",
                "AWS_ACCESS_KEY_ID=",
                "HF_TOKEN=",
                "HUGGING_FACE_HUB_TOKEN=",
                "_KEY=",
                "TOKEN=",
                "PASSWORD=",
                "SECRET=",
                "CREDENTIAL=",
            )
            credential_passed = environment["exitCode"] == 0 and not any(
                marker in environment_text for marker in forbidden_environment
            )
            results.append(
                result(
                    "credential_and_environment_visibility",
                    credential_passed,
                    {
                        "host_sentinel_absent": "ANARRES_HOST_CREDENTIAL_SENTINEL"
                        not in environment_text
                    },
                )
            )

            network_program = (
                "import json,socket; out={}; "
                "targets={'dns':('example.com',443),'public':('1.1.1.1',443),"
                "'metadata':('169.254.169.254',80)}; "
                "\nfor k,v in targets.items():\n"
                "  try:\n    s=socket.create_connection(v,timeout=1); s.close(); out[k]=True\n"
                "  except OSError: out[k]=False\n"
                "print(json.dumps(out,sort_keys=True))"
            )
            network = execute(socket_path, f"python3 -c {shlex.quote(network_program)}", 5, 10)
            network_outcomes = json.loads(network["stdout"])
            results.append(
                result(
                    "external_network_egress",
                    not any(network_outcomes.values()),
                    network_outcomes,
                )
            )

            api_base = inference["endpoint"]["api_base"]
            host_ready = host_inference_ready(api_base)
            inference_endpoint = urlparse(api_base)
            if inference_endpoint.port is None:
                raise QualificationError("inference endpoint has no explicit port")
            local_program = (
                "import socket,sys; "
                "s=socket.socket(); s.settimeout(1); "
                f"\ntry:\n s.connect(('127.0.0.1',{inference_endpoint.port})); sys.exit(1)\n"
                "except OSError:\n sys.exit(0)"
            )
            local = execute(socket_path, f"python3 -c {shlex.quote(local_program)}", 6, 5)
            results.append(
                result(
                    "local_inference_separation",
                    host_ready and local["exitCode"] == 0,
                    {
                        "controller_endpoint_ready": host_ready,
                        "sandbox_endpoint_blocked": local["exitCode"] == 0,
                    },
                )
            )

            timeout_response = rpc(
                socket_path,
                "sandbox/execute",
                {"command": "sleep 5", "cwd": "/workspace", "timeout": 0.2},
                7,
            )
            file_limit = execute(socket_path, "ulimit -f", 8)
            resource_passed = (
                timeout_response.get("error", {}).get("code") == -32001
                and int(file_limit["stdout"].strip()) == 2097152
                and host_config["PidsLimit"] == 512
                and host_config["Memory"] == 32 * 1024**3
                and host_config["NanoCpus"] == 8_000_000_000
            )
            results.append(
                result(
                    "resource_limits",
                    resource_passed,
                    {
                        "timeout_enforced": timeout_response.get("error", {}).get("code") == -32001,
                        "pids": host_config["PidsLimit"],
                        "memory_bytes": host_config["Memory"],
                        "cpus": host_config["NanoCpus"] / 1_000_000_000,
                    },
                )
            )

            reset_passed = (
                tree_digest(reset_workspace) == pre_hash and tree_digest(workspace) == pre_hash
            )
            results.append(
                result(
                    "fresh_task_reset",
                    reset_passed,
                    {"independent_materializations_match": reset_passed},
                )
            )

            controller_home = work / "controller-home"
            controller_home.mkdir(mode=0o700)
            environment_for_vibe = isolated_environment(controller_home, vibe)
            build_vibe_home(args.controller_lock.parent, controller, controller_home / "vibe-home")
            version = subprocess.run(
                [str(vibe), "--version"],
                env=environment_for_vibe,
                cwd=controller_home,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            version_text = (version.stdout or version.stderr).strip()
            vibe_output = output / "vibe-smoke"
            qualification_prompt = (
                args.controller_lock.parent / controller["qualification_prompt"]
            ).resolve(strict=True)
            command = [
                str(vibe),
                "--prompt-file",
                str(qualification_prompt),
                "--agent",
                "lean",
                "--model",
                controller["model_alias"],
                "--auto-approve",
                "--max-turns",
                "3",
                "--max-tokens",
                "4096",
                "--time-limit",
                "180",
                "--output",
                "json",
                "--output-dir",
                str(vibe_output),
                "--agent-socket",
                str(socket_path),
            ]
            for tool in controller["tool_allowlist"]:
                command.extend(["--enabled-tools", tool])
            with (
                (output / "vibe-smoke.stdout").open("wb") as stdout,
                (output / "vibe-smoke.stderr").open("wb") as stderr,
            ):
                vibe_result = subprocess.run(
                    command,
                    env=environment_for_vibe,
                    cwd=controller_home,
                    check=False,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=240,
                )
            export_path = vibe_output / "export.json"
            exported = read_json(export_path) if export_path.is_file() else {}
            effective = exported.get("config") or {}
            controller_passed = (
                version.returncode == 0
                and "3.1.0" in version_text
                and effective.get("enabled_tools") == controller["tool_allowlist"]
                and effective.get("bypass_tool_permissions") is True
                and not effective.get("mcp_servers")
                and not exported.get("warnings")
            )
            results.append(
                result(
                    "controller_configuration_isolation",
                    controller_passed,
                    {
                        "vibe_version": version_text,
                        "tool_allowlist_matched": effective.get("enabled_tools")
                        == controller["tool_allowlist"],
                        "warnings": len(exported.get("warnings") or []),
                    },
                )
            )
            export_passed = (
                vibe_result.returncode == 0
                and exported.get("outcome") == "finished"
                and isinstance(exported.get("usage"), dict)
                and isinstance(exported.get("steps"), int)
                and exported["steps"] >= 1
                and "stop_reason" in exported
                and "error" in exported
                and isinstance(exported.get("journal_dir"), str)
                and (vibe_output / exported["journal_dir"]).is_dir()
            )
            results.append(
                result(
                    "vibe_export_completeness",
                    export_passed,
                    {
                        "outcome": exported.get("outcome"),
                        "steps": exported.get("steps"),
                        "usage_recorded": isinstance(exported.get("usage"), dict),
                        "journal_recorded": isinstance(exported.get("journal_dir"), str),
                    },
                )
            )

            background = execute(
                socket_path,
                "sleep 300 >/tmp/anarres-background.log 2>&1 & echo $!",
                9,
            )
            background_started = (
                background["exitCode"] == 0 and background["stdout"].strip().isdigit()
            )
        finally:
            stop_server(server)
            server_stdout.close()
            server_stderr.close()

        removed = (
            subprocess.run(
                [args.docker, "inspect", container_name]
                if "container_name" in locals()
                else ["false"],
                check=False,
                capture_output=True,
                timeout=30,
            ).returncode
            != 0
        )
        results.append(
            result(
                "process_tree_cleanup",
                bool(locals().get("background_started")) and removed,
                {
                    "background_started": bool(locals().get("background_started")),
                    "container_removed": removed,
                },
            )
        )

    server_receipt = read_json(server_receipt_path)
    if server_receipt.get("infrastructure_errors"):
        raise QualificationError("sandbox server recorded an infrastructure error")
    methods = server_receipt.get("methods") or {}
    vibe_stdout = (output / "vibe-smoke.stdout").read_text(encoding="utf-8", errors="replace")
    vibe_tools_recorded = (
        methods.get("agent/initialize", 0) >= 2
        and methods.get("sandbox/execute", 0) >= 8
        and "4.29.1" in vibe_stdout
    )
    export_result = next(record for record in results if record["id"] == "vibe_export_completeness")
    export_result["passed"] = export_result["passed"] and vibe_tools_recorded
    export_result["evidence"]["tool_execution_recorded"] = vibe_tools_recorded
    observed_ids = [record["id"] for record in results]
    if sorted(observed_ids) != sorted(expected_tests) or len(observed_ids) != len(
        set(observed_ids)
    ):
        raise QualificationError(
            "qualification results do not cover the frozen test set exactly once"
        )
    qualified = all(record["passed"] for record in results)
    receipt = {
        "schema_version": "anarres.formal-verification-containment-qualification.v1",
        "contract_id": containment["contract_id"],
        "qualified": qualified,
        "started_at": started_at,
        "ended_at": utc_now(),
        "runtime_image": args.image,
        "runtime_image_id": server_receipt.get("image_id"),
        "container_runtime_version": server_receipt.get("container_runtime_version"),
        "model_artifact_digest": args.model_artifact_digest,
        "inference_contract_sha256": inference_digest,
        "controller_lock_sha256": digest(args.controller_lock),
        "vibe_source_revision": vibe_revision,
        "task_pre_sha256": pre_hash,
        "task_post_sha256": tree_digest(workspace),
        "sandbox_receipt_sha256": digest(server_receipt_path),
        "vibe_export_sha256": digest(output / "vibe-smoke" / "export.json")
        if (output / "vibe-smoke" / "export.json").is_file()
        else None,
        "tests": results,
    }
    (output / "qualification-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not qualified:
        raise QualificationError("one or more containment tests failed")


if __name__ == "__main__":
    main()
