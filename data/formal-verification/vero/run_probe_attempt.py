#!/usr/bin/env python3
"""Run one frozen Vero policy-probe attempt after every gate is qualified."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from materialize_probe_task import tree_digest


class AttemptLaunchError(RuntimeError):
    """Raised when an attempt cannot start under the frozen contract."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AttemptLaunchError(f"expected an object in {path.name}")
    return value


def require_sha256(value: str, label: str) -> None:
    normalized = value.removeprefix("sha256:")
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise AttemptLaunchError(f"{label} is not a SHA-256 digest")


def validate_ready(
    *,
    protocol: dict[str, Any],
    containment: dict[str, Any],
    runtime: dict[str, Any],
    controller: dict[str, Any],
    inference: dict[str, Any],
    materialization: dict[str, Any],
    task: Path,
    image: str,
) -> None:
    if not protocol["execution_authorized"] or protocol["status"] != "frozen_ready":
        raise AttemptLaunchError("probe protocol is not authorized for execution")
    if not containment["qualified"] or containment["status"] != "qualified":
        raise AttemptLaunchError("containment contract has not qualified")
    if runtime["status"] != "qualified" or runtime["built_image_digest"] != image:
        raise AttemptLaunchError("runtime image is not the qualified image")
    if controller["status"] != "frozen":
        raise AttemptLaunchError("controller deployment has not been frozen")
    if inference["status"] != "qualified":
        raise AttemptLaunchError("inference deployment has not qualified")

    starting_policy = protocol["starting_policy"]
    model_digest = inference["model"]["local_artifact_digest"]
    if model_digest is None or model_digest != starting_policy["local_artifact_digest"]:
        raise AttemptLaunchError("local model artifact is not frozen in the protocol")
    require_sha256(model_digest, "local model artifact")
    require_sha256(image.split("@")[-1], "runtime image")

    if materialization["source_id"] != protocol["source"]["vero_id"]:
        raise AttemptLaunchError("task source disagrees with the protocol")
    if materialization["mode"] not in protocol["probe_design"]["modes"]:
        raise AttemptLaunchError("task mode is outside the probe design")
    if tree_digest(task) != materialization["task_tree_sha256"]:
        raise AttemptLaunchError("task tree has changed since materialization")


def build_vibe_home(controller_root: Path, lock: dict[str, Any], destination: Path) -> None:
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    config_source = controller_root / lock["config"]
    agent_source = controller_root / lock["agent"]
    if (
        digest(config_source) != lock["config_sha256"]
        or digest(agent_source) != lock["agent_sha256"]
    ):
        raise AttemptLaunchError("controller files disagree with their lock")
    shutil.copy2(config_source, destination / "config.toml")
    agents = destination / "agents"
    agents.mkdir(mode=0o700)
    shutil.copy2(agent_source, agents / "lean.toml")
    (destination / "config.toml").chmod(0o600)
    (agents / "lean.toml").chmod(0o600)


def isolated_environment(work_root: Path, vibe: Path) -> dict[str, str]:
    home = work_root / "home"
    vibe_home = work_root / "vibe-home"
    cache = work_root / "cache"
    temporary = work_root / "tmp"
    for path in (home, cache, temporary):
        path.mkdir(mode=0o700, exist_ok=False)
    path_entries = [str(vibe.parent), "/usr/local/bin", "/usr/bin", "/bin"]
    return {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "NO_PROXY": "127.0.0.1,localhost",
        "PATH": ":".join(dict.fromkeys(path_entries)),
        "TMPDIR": str(temporary),
        "VIBE_HOME": str(vibe_home),
        "VIBE_STRICT_CONFIG": "1",
        "XDG_CACHE_HOME": str(cache),
        "no_proxy": "127.0.0.1,localhost",
    }


def build_vibe_command(
    *,
    vibe: Path,
    prompt: Path,
    socket: Path,
    output: Path,
    lock: dict[str, Any],
) -> list[str]:
    limits = lock["limits"]
    command = [
        str(vibe),
        "--prompt-file",
        str(prompt),
        "--agent",
        "lean",
        "--model",
        lock["model_alias"],
        "--auto-approve",
        "--max-turns",
        str(limits["maximum_turns"]),
        "--max-tokens",
        str(limits["maximum_cumulative_model_tokens"]),
        "--time-limit",
        str(limits["wall_time_seconds"]),
        "--output",
        lock["output_format"],
        "--output-dir",
        str(output),
        "--agent-socket",
        str(socket),
    ]
    for tool in lock["tool_allowlist"]:
        command.extend(["--enabled-tools", tool])
    return command


def wait_for_socket(socket: Path, server: subprocess.Popen[bytes], seconds: float = 30) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if socket.is_socket():
            return
        if server.poll() is not None:
            raise AttemptLaunchError("sandbox server exited before opening its socket")
        time.sleep(0.1)
    raise AttemptLaunchError("sandbox server did not open its socket")


def stop_server(server: subprocess.Popen[bytes]) -> None:
    if server.poll() is not None:
        return
    server.send_signal(signal.SIGTERM)
    try:
        server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=10)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--materialization-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--vibe", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--containment", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--controller-lock", type=Path, required=True)
    parser.add_argument("--inference-contract", type=Path, required=True)
    parser.add_argument("--sandbox-server", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [
        args.task,
        args.materialization_receipt,
        args.vibe,
        args.protocol,
        args.containment,
        args.runtime_lock,
        args.controller_lock,
        args.inference_contract,
        args.sandbox_server,
    ]
    for path in paths:
        if not path.exists():
            raise AttemptLaunchError(f"required path does not exist: {path}")
    output = args.output.absolute()
    if output.exists():
        raise AttemptLaunchError("--output must not exist")
    work_parent = args.work_root.resolve(strict=True)

    protocol = read_json(args.protocol)
    containment = read_json(args.containment)
    runtime = read_json(args.runtime_lock)
    controller = read_json(args.controller_lock)
    inference = read_json(args.inference_contract)
    materialization = read_json(args.materialization_receipt)
    task = args.task.resolve(strict=True)
    validate_ready(
        protocol=protocol,
        containment=containment,
        runtime=runtime,
        controller=controller,
        inference=inference,
        materialization=materialization,
        task=task,
        image=args.image,
    )

    prompt = (args.protocol.parent / protocol["starting_policy"]["user_prompt"]).resolve(
        strict=True
    )
    if digest(prompt) != protocol["starting_policy"]["user_prompt_sha256"]:
        raise AttemptLaunchError("agent prompt disagrees with the protocol")
    inference_digest = digest(args.inference_contract)
    model_digest = inference["model"]["local_artifact_digest"]

    output.mkdir(mode=0o700, parents=True)
    receipt_path = output / "attempt-receipt.json"
    started = utc_now()
    launcher_receipt: dict[str, Any] = {
        "schema_version": "anarres.formal-verification-attempt.v1",
        "attempt_id": args.attempt_id,
        "task_id": f"{materialization['benchmark_id']}:{materialization['mode']}",
        "started_at": started,
        "protocol_sha256": digest(args.protocol),
        "containment_sha256": digest(args.containment),
        "runtime_lock_sha256": digest(args.runtime_lock),
        "controller_lock_sha256": digest(args.controller_lock),
        "inference_contract_sha256": inference_digest,
        "materialization_receipt_sha256": digest(args.materialization_receipt),
        "task_pre_sha256": tree_digest(task),
        "environment_keys": controller["environment_allowlist"],
        "tool_allowlist": controller["tool_allowlist"],
        "vibe_version": None,
        "vibe_exit_code": None,
        "sandbox_exit_code": None,
        "outcome": None,
        "launcher_error": None,
        "ended_at": None,
        "task_post_sha256": None,
    }

    try:
        with tempfile.TemporaryDirectory(prefix="anarres-vero-", dir=work_parent) as temporary:
            work = Path(temporary)
            vibe = args.vibe.resolve(strict=True)
            environment = isolated_environment(work, vibe)
            if sorted(environment) != sorted(controller["environment_allowlist"]):
                raise AttemptLaunchError("launcher environment disagrees with the controller lock")
            build_vibe_home(args.controller_lock.parent, controller, work / "vibe-home")
            version = subprocess.run(
                [str(vibe), "--version"],
                env=environment,
                cwd=work,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            version_text = (version.stdout or version.stderr).strip()
            if version.returncode != 0 or "3.1.0" not in version_text:
                raise AttemptLaunchError("Vibe v3.1.0 is not installed at --vibe")
            launcher_receipt["vibe_version"] = version_text

            socket = work / "socket" / "agent.sock"
            sandbox_receipt = output / "sandbox-receipt.json"
            server_stdout = (output / "sandbox.stdout").open("wb")
            server_stderr = (output / "sandbox.stderr").open("wb")
            server_command = [
                sys.executable,
                str(args.sandbox_server.resolve(strict=True)),
                "--socket",
                str(socket),
                "--image",
                args.image,
                "--workspace",
                str(task),
                "--receipt",
                str(sandbox_receipt),
                "--attempt-id",
                args.attempt_id,
                "--task-id",
                launcher_receipt["task_id"],
                "--model-artifact-digest",
                model_digest,
                "--inference-config-digest",
                inference_digest,
                "--docker",
                args.docker,
            ]
            server = subprocess.Popen(server_command, stdout=server_stdout, stderr=server_stderr)
            try:
                wait_for_socket(socket, server)
                vibe_output = output / "vibe-output"
                vibe_command = build_vibe_command(
                    vibe=vibe,
                    prompt=prompt,
                    socket=socket,
                    output=vibe_output,
                    lock=controller,
                )
                with (
                    (output / "vibe.stdout").open("wb") as stdout,
                    (output / "vibe.stderr").open("wb") as stderr,
                ):
                    result = subprocess.run(
                        vibe_command,
                        env=environment,
                        cwd=work,
                        check=False,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=controller["limits"]["wall_time_seconds"] + 90,
                    )
                launcher_receipt["vibe_exit_code"] = result.returncode
            finally:
                stop_server(server)
                server_stdout.close()
                server_stderr.close()
                launcher_receipt["sandbox_exit_code"] = server.returncode

        export_path = output / "vibe-output" / "export.json"
        if export_path.is_file():
            exported = read_json(export_path)
            launcher_receipt["outcome"] = exported.get("outcome")
            launcher_receipt["vibe_export_sha256"] = digest(export_path)
    except Exception as error:
        launcher_receipt["launcher_error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        launcher_receipt["ended_at"] = utc_now()
        launcher_receipt["task_post_sha256"] = tree_digest(task)
        receipt_path.write_text(
            json.dumps(launcher_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if launcher_receipt["vibe_exit_code"] not in {0, 3}:
        raise AttemptLaunchError("attempt ended with an infrastructure or configuration failure")


if __name__ == "__main__":
    main()
