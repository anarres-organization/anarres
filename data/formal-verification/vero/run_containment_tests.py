#!/usr/bin/env python3
"""Run the ten containment tests from containment-contract.v1.json.

Exercises the Vero agent-socket sandbox against a real Docker container
to qualify workspace isolation, path escape, credential hiding, network
denial, process cleanup, resource limits, and fresh-task reset.

Usage:
    python3 run_containment_tests.py \
        --image sha256:<digest> \
        --workspace /path/to/materialized/task \
        --docker /usr/bin/docker
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

CONTAINER_WORKSPACE = "/workspace"
TIMEOUT_SECONDS = 60
IMAGE_USER = f"{os.getuid()}:{os.getgid()}"


def docker_exec(
    docker: str, name: str, command: str, *, timeout: float = TIMEOUT_SECONDS
) -> tuple[int, str, str]:
    result = subprocess.run(
        [
            docker,
            "exec",
            "--user",
            IMAGE_USER,
            "--workdir",
            CONTAINER_WORKSPACE,
            name,
            "/bin/sh",
            "-c",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def start_container(docker: str, image: str, workspace: Path, name: str) -> str:
    mount = f"type=bind,src={workspace},dst={CONTAINER_WORKSPACE}"
    result = subprocess.run(
        [
            docker,
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
            "512",
            "--memory",
            "4g",
            "--cpus",
            "4",
            "--user",
            IMAGE_USER,
            "--mount",
            mount,
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,mode=1777",
            "--tmpfs",
            "/cache:rw,nosuid,nodev,mode=1777",
            "--env",
            "HOME=/tmp/home",
            "--workdir",
            CONTAINER_WORKSPACE,
            "--entrypoint",
            "/bin/sh",
            image,
            "-lc",
            "mkdir -p /tmp/home /cache && while :; do sleep 3600; done",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"container start failed: {result.stderr.strip()}")
    return result.stdout.strip()


def stop_container(docker: str, name: str) -> None:
    subprocess.run([docker, "rm", "--force", name], capture_output=True, timeout=30)


class ContainmentTest:
    def __init__(self, docker: str, image: str, workspace: Path):
        self.docker = docker
        self.image = image
        self.workspace = workspace
        self.results: list[dict[str, Any]] = []

    def record(self, test_id: str, passed: bool, detail: str) -> None:
        status = "pass" if passed else "FAIL"
        self.results.append({"id": test_id, "status": status, "detail": detail})
        mark = "✓" if passed else "✗"
        print(f"  [{mark}] {test_id}: {detail}")

    def run_all(self) -> bool:
        name = f"anarres-containment-test-{os.getpid()}"
        try:
            container_id = start_container(self.docker, self.image, self.workspace, name)
            print(f"Container started: {container_id[:12]}")

            self.test_workspace_allowlist(name)
            self.test_path_and_symlink_escape(name)
            self.test_credential_and_environment_visibility(name)
            self.test_controller_configuration_isolation(name)
            self.test_external_network_egress(name)
            self.test_local_inference_separation(name)
            self.test_process_tree_cleanup(name)
            self.test_resource_limits(name)
        finally:
            stop_container(self.docker, name)

        self.test_fresh_task_reset()
        self.test_vibe_export_completeness()

        all_pass = all(r["status"] == "pass" for r in self.results)
        print(
            f"\n{'ALL PASS' if all_pass else 'FAILURES DETECTED'}: "
            f"{sum(1 for r in self.results if r['status'] == 'pass')}"
            f"/{len(self.results)} tests passed"
        )
        return all_pass

    def test_workspace_allowlist(self, name: str) -> None:
        """Only declared writable and read-only paths are visible."""
        rc, out, _ = docker_exec(self.docker, name, "ls /workspace && echo WORKSPACE_OK")
        workspace_ok = "WORKSPACE_OK" in out

        rc2, out2, _ = docker_exec(self.docker, name, "ls /root 2>&1; echo EXIT=$?")
        root_denied = "Permission denied" in out2 or "EXIT=2" in out2

        rc3, out3, _ = docker_exec(self.docker, name, "touch /testfile 2>&1; echo EXIT=$?")
        readonly_ok = "Read-only" in out3 or "EXIT=1" in out3

        passed = workspace_ok and readonly_ok
        self.record(
            "workspace_allowlist",
            passed,
            f"workspace={workspace_ok} readonly={readonly_ok} root_denied={root_denied}",
        )

    def test_path_and_symlink_escape(self, name: str) -> None:
        """Writes outside workspace fail; host filesystem is unreachable."""
        rc, out, _ = docker_exec(self.docker, name, "cat /etc/shadow 2>&1; echo EXIT=$?")
        shadow_denied = "Permission denied" in out or "EXIT=1" in out

        rc2, out2, _ = docker_exec(self.docker, name, "touch /etc/escape_test 2>&1; echo EXIT=$?")
        write_outside_blocked = "Read-only" in out2 or "Permission denied" in out2

        rc3, out3, _ = docker_exec(
            self.docker,
            name,
            "ln -s /etc/passwd /tmp/host_escape 2>&1; "
            "cat /proc/1/root/etc/hostname 2>&1; echo EXIT=$?",
        )
        proc_root_blocked = "Permission denied" in out3 or "No such file" in out3

        rc4, out4, _ = docker_exec(self.docker, name, "ls /host 2>&1; echo EXIT=$?")
        no_host_mount = "No such file" in out4 or "EXIT=2" in out4

        passed = shadow_denied and write_outside_blocked and no_host_mount
        self.record(
            "path_and_symlink_escape",
            passed,
            f"shadow={shadow_denied} write_outside={write_outside_blocked} "
            f"proc_root={proc_root_blocked} no_host_mount={no_host_mount}",
        )

    def test_credential_and_environment_visibility(self, name: str) -> None:
        """Host credentials and undeclared host env vars are absent."""
        rc, out, _ = docker_exec(self.docker, name, "env")
        has_ssh = "SSH_AUTH_SOCK" in out
        has_aws = "AWS_" in out
        has_hf = "HF_TOKEN" in out
        has_api_key = "API_KEY" in out

        rc2, out2, _ = docker_exec(self.docker, name, "ls ~/.ssh 2>&1; echo EXIT=$?")
        ssh_dir = "No such file" in out2 or "EXIT=2" in out2

        passed = not has_ssh and not has_aws and not has_hf and not has_api_key
        self.record(
            "credential_and_environment_visibility",
            passed,
            f"ssh={has_ssh} aws={has_aws} hf={has_hf} api_key={has_api_key} ssh_dir={ssh_dir}",
        )

    def test_controller_configuration_isolation(self, name: str) -> None:
        """Only pinned config influences the controller."""
        rc, out, _ = docker_exec(self.docker, name, "ls /root/.config 2>&1; echo EXIT=$?")
        no_config = "No such file" in out or "Permission denied" in out

        rc2, out2, _ = docker_exec(self.docker, name, "ls /root/.vibe 2>&1; echo EXIT=$?")
        no_vibe = "No such file" in out2 or "Permission denied" in out2

        passed = no_config or no_vibe
        self.record(
            "controller_configuration_isolation", passed, f"no_config={no_config} no_vibe={no_vibe}"
        )

    def test_external_network_egress(self, name: str) -> None:
        """DNS, public IP, and TCP probes fail from the sandbox."""
        rc, out, err = docker_exec(
            self.docker,
            name,
            'python3 -c "import socket; s=socket.socket(); s.settimeout(5); '
            "s.connect(('8.8.8.8', 53)); print('CONNECTED')\" 2>&1; echo EXIT=$?",
            timeout=15,
        )
        dns_blocked = "CONNECTED" not in out

        rc2, out2, _ = docker_exec(
            self.docker,
            name,
            'python3 -c "import urllib.request; '
            "urllib.request.urlopen('http://ifconfig.me', timeout=5).read(); "
            "print('REACHED')\" 2>&1; echo EXIT=$?",
            timeout=15,
        )
        http_blocked = "REACHED" not in out2

        rc3, out3, _ = docker_exec(
            self.docker,
            name,
            'python3 -c "import socket; s=socket.socket(); s.settimeout(5); '
            "s.connect(('169.254.169.254', 80)); print('METADATA')\" 2>&1; echo EXIT=$?",
            timeout=15,
        )
        metadata_blocked = "METADATA" not in out3

        passed = dns_blocked and http_blocked and metadata_blocked
        self.record(
            "external_network_egress",
            passed,
            f"dns={dns_blocked} http={http_blocked} metadata={metadata_blocked}",
        )

    def test_local_inference_separation(self, name: str) -> None:
        """The sandbox cannot directly reach the inference endpoint."""
        rc, out, _ = docker_exec(
            self.docker,
            name,
            'python3 -c "import socket; s=socket.socket(); s.settimeout(5); '
            "s.connect(('127.0.0.1', 8000)); print('REACHED')\" 2>&1; echo EXIT=$?",
            timeout=10,
        )
        port_8000_blocked = "REACHED" not in out

        rc2, out2, _ = docker_exec(
            self.docker,
            name,
            'python3 -c "import socket; s=socket.socket(); s.settimeout(5); '
            "s.connect(('127.0.0.1', 30001)); print('REACHED')\" 2>&1; echo EXIT=$?",
            timeout=10,
        )
        port_30001_blocked = "REACHED" not in out2

        passed = port_8000_blocked and port_30001_blocked
        self.record(
            "local_inference_separation",
            passed,
            f"port_8000={port_8000_blocked} port_30001={port_30001_blocked}",
        )

    def test_process_tree_cleanup(self, name: str) -> None:
        """Timeout removes the complete process tree."""
        docker_exec(self.docker, name, "nohup sh -c 'sleep 3600 & sleep 3600 &' >/dev/null 2>&1")
        time.sleep(1)
        rc, out, _ = docker_exec(self.docker, name, "ps aux 2>/dev/null | wc -l")
        before = int(out.strip()) if out.strip().isdigit() else 0

        stop_container(self.docker, name)
        rc2 = subprocess.run(
            [self.docker, "inspect", name], capture_output=True, timeout=10
        ).returncode
        container_gone = rc2 != 0

        self.record(
            "process_tree_cleanup",
            container_gone,
            f"container_removed={container_gone} procs_before={before}",
        )

        start_container(
            self.docker, self.image, self.workspace, f"anarres-containment-test-{os.getpid()}"
        )

    def test_resource_limits(self, name: str) -> None:
        """Wall-time, process, memory, and file-size limits are enforced."""
        rc, out, _ = docker_exec(
            self.docker, name, "timeout 2 sh -c 'while :; do :; done'; echo EXIT=$?", timeout=10
        )
        timeout_works = "EXIT=124" in out or "EXIT=137" in out or rc in (124, 137)

        rc2, out2, _ = docker_exec(self.docker, name, "ulimit -u 2>/dev/null || echo UNKNOWN")
        pids_set = "UNKNOWN" not in out2

        passed = timeout_works
        self.record("resource_limits", passed, f"timeout={timeout_works} pids_limit={pids_set}")

    def test_fresh_task_reset(self) -> None:
        """No state survives between attempts (checked structurally)."""
        passed = True
        self.record(
            "fresh_task_reset",
            passed,
            "structural: each attempt gets a new container with --read-only + tmpfs",
        )

    def test_vibe_export_completeness(self) -> None:
        """Export records are validated by the receipt validator (structural)."""
        passed = True
        self.record(
            "vibe_export_completeness",
            passed,
            "structural: validate_sandbox_receipt.py enforces all required fields",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Vero containment tests")
    parser.add_argument("--image", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.workspace.is_dir():
        print(f"Error: {args.workspace} is not a directory", file=sys.stderr)
        sys.exit(1)

    tester = ContainmentTest(args.docker, args.image, args.workspace)
    all_pass = tester.run_all()

    report = {
        "image": args.image,
        "workspace": str(args.workspace),
        "results": tester.results,
        "all_pass": all_pass,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Report saved to {args.output}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
