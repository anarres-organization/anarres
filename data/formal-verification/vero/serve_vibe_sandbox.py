#!/usr/bin/env python3
"""Serve one Vibe attempt through an ephemeral, network-denied Docker sandbox."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

PROTOCOL_VERSION = 2
MAX_REQUEST_BYTES = 64 * 1024 * 1024
TIMEOUT_ERROR = -32001
METHOD_NOT_FOUND = -32601
INVALID_REQUEST = -32602
INTERNAL_ERROR = -32603


class SandboxError(RuntimeError):
    """Raised when the container runtime or request contract fails."""


class CommandTimedOut(TimeoutError):
    """Raised when an in-container command reaches its bounded timeout."""

    def __init__(self, seconds: float) -> None:
        super().__init__(f"sandbox command exceeded {seconds:g} seconds")
        self.seconds = seconds


@dataclass(frozen=True)
class SandboxConfig:
    docker: str
    image: str
    workspace: Path
    container_workspace: str
    user: str
    memory: str
    cpus: float
    pids: int
    maximum_command_seconds: float
    maximum_output_bytes: int
    maximum_file_bytes: int


@dataclass
class Receipt:
    attempt_id: str
    task_id: str
    started_at: str
    image_reference: str
    model_artifact_digest: str
    inference_config_digest: str
    workspace: str
    container_name: str
    resource_limits: dict[str, Any]
    workspace_pre_sha256: str
    container_id: str | None = None
    image_id: str | None = None
    container_runtime_version: str | None = None
    methods: dict[str, int] = field(default_factory=dict)
    command_timeouts: int = 0
    output_truncations: int = 0
    infrastructure_errors: list[str] = field(default_factory=list)
    ended_at: str | None = None
    workspace_post_sha256: str | None = None
    container_removed: bool = False

    def count(self, method: str) -> None:
        self.methods[method] = self.methods.get(method, 0) + 1


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def tree_digest(root: Path) -> str:
    """Hash one task tree without following links outside it."""
    result = hashlib.sha256()
    for directory, names, filenames in os.walk(root, followlinks=False):
        names.sort()
        filenames.sort()
        current = Path(directory)
        for name in [*names, *filenames]:
            path = current / name
            relative = path.relative_to(root).as_posix().encode("utf-8")
            result.update(len(relative).to_bytes(8, "big"))
            result.update(relative)
            if path.is_symlink():
                result.update(b"L")
                target = os.readlink(path).encode("utf-8")
                result.update(len(target).to_bytes(8, "big"))
                result.update(target)
            elif path.is_dir():
                result.update(b"D")
            elif path.is_file():
                result.update(b"F")
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        result.update(chunk)
            else:
                result.update(b"O")
    return result.hexdigest()


def validate_image_reference(image: str) -> None:
    digest = (
        image.split("@sha256:", 1)[-1] if "@sha256:" in image else image.removeprefix("sha256:")
    )
    if (
        ("@sha256:" not in image and not image.startswith("sha256:"))
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise SandboxError("--image must be an immutable digest reference")


def validate_digest(value: str, option: str) -> None:
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise SandboxError(f"{option} must be a SHA-256 digest")


def validate_resource_limits(args: argparse.Namespace) -> None:
    if args.cpus <= 0 or args.pids <= 0 or args.maximum_command_seconds <= 0:
        raise SandboxError("CPU, process, and command-time limits must be positive")
    if args.maximum_output_bytes < 1024 or args.maximum_file_bytes < 1024:
        raise SandboxError("output and file-size limits must be at least 1,024 bytes")


def validate_container_workspace(path: str) -> None:
    parsed = PurePosixPath(path)
    if not parsed.is_absolute() or ".." in parsed.parts or path == "/":
        raise SandboxError("--container-workspace must be a non-root absolute path")


def docker_run_command(config: SandboxConfig, name: str) -> list[str]:
    mount = f"type=bind,src={config.workspace},dst={config.container_workspace},rw"
    return [
        config.docker,
        "run",
        "--detach",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(config.pids),
        "--memory",
        config.memory,
        "--cpus",
        str(config.cpus),
        "--user",
        config.user,
        "--mount",
        mount,
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,mode=1777",
        "--tmpfs",
        "/cache:rw,nosuid,nodev,mode=1777",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "XDG_CACHE_HOME=/cache",
        "--workdir",
        config.container_workspace,
        "--entrypoint",
        "/bin/sh",
        config.image,
        "-lc",
        "mkdir -p /tmp/home /cache && while :; do sleep 3600; done",
    ]


class DockerSandbox:
    def __init__(self, config: SandboxConfig, receipt: Receipt) -> None:
        self.config = config
        self.receipt = receipt
        self.name = receipt.container_name
        self._metrics_lock = threading.Lock()

    def _run(
        self, arguments: list[str], *, timeout: float = 60
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                arguments,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise SandboxError(f"container runtime timed out: {arguments[1]}") from error

    def start(self) -> None:
        version = self._run(
            [
                self.config.docker,
                "version",
                "--format",
                "{{.Client.Version}}/{{.Server.Version}}",
            ]
        )
        if version.returncode != 0:
            raise SandboxError(f"container runtime unavailable: {version.stderr.strip()}")
        self.receipt.container_runtime_version = version.stdout.strip()
        result = self._run(docker_run_command(self.config, self.name), timeout=120)
        if result.returncode != 0:
            raise SandboxError(f"container start failed: {result.stderr.strip()}")
        self.receipt.container_id = result.stdout.strip()
        inspect = self._run([self.config.docker, "inspect", "--format", "{{.Image}}", self.name])
        if inspect.returncode != 0:
            raise SandboxError(f"container inspection failed: {inspect.stderr.strip()}")
        self.receipt.image_id = inspect.stdout.strip()
        preflight = self._run(
            [
                self.config.docker,
                "exec",
                "--user",
                self.config.user,
                self.name,
                "/bin/sh",
                "-lc",
                "command -v python3 >/dev/null && command -v timeout >/dev/null",
            ]
        )
        if preflight.returncode != 0:
            raise SandboxError("sandbox image must provide python3 and GNU timeout")

    def stop(self) -> None:
        result = self._run([self.config.docker, "rm", "--force", self.name])
        self.receipt.container_removed = result.returncode == 0
        if result.returncode != 0:
            self.receipt.infrastructure_errors.append(
                f"container cleanup failed: {result.stderr.strip()}"
            )

    def execute(self, command: str, cwd: str, requested_timeout: float | None) -> dict[str, Any]:
        if len(command.encode("utf-8")) > 1024 * 1024:
            raise SandboxError("sandbox command exceeds the one-megabyte request limit")
        seconds = min(
            self.config.maximum_command_seconds,
            self.config.maximum_command_seconds if requested_timeout is None else requested_timeout,
        )
        if seconds <= 0:
            raise SandboxError("sandbox command timeout must be positive")
        file_blocks = max(1, (self.config.maximum_file_bytes + 511) // 512)
        arguments = [
            self.config.docker,
            "exec",
            "--user",
            self.config.user,
            "--workdir",
            cwd,
            self.name,
            "/bin/sh",
            "-c",
            'ulimit -f "$1"; shift; exec "$@"',
            "anarres-limit",
            str(file_blocks),
            "timeout",
            "--kill-after=5s",
            f"{seconds:g}s",
            "/bin/sh",
            "-lc",
            command,
        ]
        returncode, stdout, stderr, stdout_cut, stderr_cut = self._run_bounded(
            arguments, timeout=seconds + 30
        )
        if returncode in {124, 137}:
            with self._metrics_lock:
                self.receipt.command_timeouts += 1
            raise CommandTimedOut(seconds)
        if stdout_cut or stderr_cut:
            with self._metrics_lock:
                self.receipt.output_truncations += 1
        return {"exitCode": returncode, "stdout": stdout, "stderr": stderr}

    def _run_bounded(
        self, arguments: list[str], *, timeout: float
    ) -> tuple[int, str, str, bool, bool]:
        process = subprocess.Popen(
            arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def drain(stream: Any) -> tuple[bytes, bool]:
            retained = bytearray()
            truncated = False
            while chunk := stream.read(64 * 1024):
                remaining = self.config.maximum_output_bytes - len(retained)
                if remaining > 0:
                    retained.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated = True
            return bytes(retained), truncated

        stdout_result: list[tuple[bytes, bool]] = []
        stderr_result: list[tuple[bytes, bool]] = []
        stdout_thread = threading.Thread(target=lambda: stdout_result.append(drain(process.stdout)))
        stderr_thread = threading.Thread(target=lambda: stderr_result.append(drain(process.stderr)))
        stdout_thread.start()
        stderr_thread.start()
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.wait()
            raise SandboxError("container command transport timed out") from error
        finally:
            stdout_thread.join()
            stderr_thread.join()
        stdout_raw, stdout_cut = stdout_result[0]
        stderr_raw, stderr_cut = stderr_result[0]
        return (
            returncode,
            decode_bounded(stdout_raw, stdout_cut, self.config.maximum_output_bytes),
            decode_bounded(stderr_raw, stderr_cut, self.config.maximum_output_bytes),
            stdout_cut,
            stderr_cut,
        )

    def read_file(self, path: str, max_bytes: int) -> dict[str, str | None]:
        limit = min(max(max_bytes, 0), self.config.maximum_output_bytes)
        program = (
            "import base64,os,sys; p=sys.argv[1]; n=int(sys.argv[2]); "
            "sys.exit(3) if not os.path.isfile(p) else "
            "sys.stdout.write(base64.b64encode(open(p,'rb').read(n)).decode('ascii'))"
        )
        result = self._run(
            [
                self.config.docker,
                "exec",
                "--user",
                self.config.user,
                self.name,
                "python3",
                "-c",
                program,
                path,
                str(limit),
            ]
        )
        if result.returncode == 3:
            return {"contentBase64": None}
        if result.returncode != 0:
            raise SandboxError(f"sandbox read failed: {result.stderr.strip()}")
        try:
            base64.b64decode(result.stdout, validate=True)
        except ValueError as error:
            raise SandboxError("sandbox read returned invalid base64") from error
        return {"contentBase64": result.stdout}


def decode_bounded(value: bytes, truncated: bool, maximum_bytes: int) -> str:
    if not truncated:
        return value.decode("utf-8", errors="replace")
    suffix = b"\n[output truncated by containment boundary]\n"
    retained = value[: max(0, maximum_bytes - len(suffix))]
    return (retained + suffix).decode("utf-8", errors="replace")


def response(request_id: Any, *, result: Any = None, error: dict[str, Any] | None = None) -> bytes:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        message["result"] = result
    else:
        message["error"] = error
    return json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"


async def dispatch(request: dict[str, Any], sandbox: DockerSandbox) -> dict[str, Any]:
    method = request.get("method")
    params = request.get("params")
    if not isinstance(method, str) or not isinstance(params, dict):
        raise SandboxError("request must contain a string method and object params")
    sandbox.receipt.count(method)
    if method == "agent/initialize":
        if params.get("protocolVersion") != PROTOCOL_VERSION:
            raise SandboxError("unsupported Vibe agent-socket protocol")
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "workspace": sandbox.config.container_workspace,
            "python": "/usr/bin/python3",
        }
    if method == "sandbox/execute":
        command, cwd, timeout = params.get("command"), params.get("cwd"), params.get("timeout")
        if not isinstance(command, str) or not isinstance(cwd, str):
            raise SandboxError("sandbox/execute requires string command and cwd")
        if timeout is not None and not isinstance(timeout, int | float):
            raise SandboxError("sandbox/execute timeout must be numeric or null")
        return await asyncio.to_thread(sandbox.execute, command, cwd, timeout)
    if method == "sandbox/readFile":
        path, max_bytes = params.get("path"), params.get("maxBytes")
        if not isinstance(path, str) or not isinstance(max_bytes, int):
            raise SandboxError("sandbox/readFile requires path and maxBytes")
        return await asyncio.to_thread(sandbox.read_file, path, max_bytes)
    raise LookupError(method)


async def handle(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, sandbox: DockerSandbox
) -> None:
    request_id: Any = None
    try:
        line = await reader.readline()
        if not line or len(line) > MAX_REQUEST_BYTES:
            raise SandboxError("empty or oversized agent-socket request")
        request = json.loads(line)
        if not isinstance(request, dict):
            raise SandboxError("agent-socket request must be an object")
        request_id = request.get("id")
        result = await dispatch(request, sandbox)
        reply = response(request_id, result=result)
    except CommandTimedOut as error:
        reply = response(
            request_id,
            error={
                "code": TIMEOUT_ERROR,
                "message": str(error),
                "data": {"timeoutSeconds": error.seconds},
            },
        )
    except LookupError as error:
        reply = response(
            request_id,
            error={"code": METHOD_NOT_FOUND, "message": f"unknown method: {error}"},
        )
    except (SandboxError, json.JSONDecodeError) as error:
        reply = response(request_id, error={"code": INVALID_REQUEST, "message": str(error)})
    except Exception as error:  # pragma: no cover - final containment boundary
        sandbox.receipt.infrastructure_errors.append(type(error).__name__)
        reply = response(
            request_id,
            error={"code": INTERNAL_ERROR, "message": "sandbox infrastructure failure"},
        )
    try:
        writer.write(reply)
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def serve(socket_path: Path, sandbox: DockerSandbox) -> None:
    socket_path.parent.mkdir(mode=0o700, parents=True, exist_ok=False)
    socket_path.parent.chmod(0o700)
    server = await asyncio.start_unix_server(
        lambda reader, writer: handle(reader, writer, sandbox),
        path=str(socket_path),
        limit=MAX_REQUEST_BYTES,
    )
    socket_path.chmod(0o600)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            loop.add_signal_handler(getattr(signal, name), stop.set)
    async with server:
        await stop.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--model-artifact-digest", required=True)
    parser.add_argument("--inference-config-digest", required=True)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--container-workspace", default="/workspace")
    parser.add_argument("--user", default=f"{os.getuid()}:{os.getgid()}")
    parser.add_argument("--memory", default="32g")
    parser.add_argument("--cpus", type=float, default=8.0)
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--maximum-command-seconds", type=float, default=1200)
    parser.add_argument("--maximum-output-bytes", type=int, default=16 * 1024 * 1024)
    parser.add_argument("--maximum-file-bytes", type=int, default=1024 * 1024 * 1024)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_image_reference(args.image)
    validate_digest(args.model_artifact_digest, "--model-artifact-digest")
    validate_digest(args.inference_config_digest, "--inference-config-digest")
    validate_resource_limits(args)
    validate_container_workspace(args.container_workspace)
    workspace = args.workspace.resolve(strict=True)
    if not workspace.is_dir():
        raise SandboxError("--workspace must be a directory")
    docker = shutil.which(args.docker)
    if docker is None:
        raise SandboxError("Docker CLI not found")
    if args.socket.exists() or args.socket.parent.exists():
        raise SandboxError("--socket must be inside a new private directory")
    config = SandboxConfig(
        docker=docker,
        image=args.image,
        workspace=workspace,
        container_workspace=args.container_workspace,
        user=args.user,
        memory=args.memory,
        cpus=args.cpus,
        pids=args.pids,
        maximum_command_seconds=args.maximum_command_seconds,
        maximum_output_bytes=args.maximum_output_bytes,
        maximum_file_bytes=args.maximum_file_bytes,
    )
    name = f"anarres-vero-{secrets.token_hex(6)}"
    receipt = Receipt(
        attempt_id=args.attempt_id,
        task_id=args.task_id,
        started_at=utc_now(),
        image_reference=args.image,
        model_artifact_digest=args.model_artifact_digest,
        inference_config_digest=args.inference_config_digest,
        workspace=str(workspace),
        container_name=name,
        resource_limits={
            "memory": args.memory,
            "cpus": args.cpus,
            "pids": args.pids,
            "maximum_command_seconds": args.maximum_command_seconds,
            "maximum_output_bytes": args.maximum_output_bytes,
            "maximum_file_bytes": args.maximum_file_bytes,
        },
        workspace_pre_sha256=tree_digest(workspace),
    )
    sandbox = DockerSandbox(config, receipt)
    try:
        sandbox.start()
        asyncio.run(serve(args.socket, sandbox))
    except Exception as error:
        receipt.infrastructure_errors.append(f"{type(error).__name__}: {error}")
        raise
    finally:
        if receipt.container_id is not None:
            sandbox.stop()
        receipt.ended_at = utc_now()
        receipt.workspace_post_sha256 = tree_digest(workspace)
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt.__dict__, indent=2) + "\n", encoding="utf-8")
        if args.socket.parent.exists():
            shutil.rmtree(args.socket.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
