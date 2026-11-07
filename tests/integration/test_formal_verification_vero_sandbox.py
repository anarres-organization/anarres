from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "formal-verification" / "vero" / "serve_vibe_sandbox.py"
RECEIPT_SOURCE = ROOT / "data" / "formal-verification" / "vero" / "validate_sandbox_receipt.py"
SPEC = importlib.util.spec_from_file_location("vero_serve_vibe_sandbox", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {SOURCE}")
SANDBOX = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SANDBOX
SPEC.loader.exec_module(SANDBOX)
RECEIPT_SPEC = importlib.util.spec_from_file_location(
    "vero_validate_sandbox_receipt", RECEIPT_SOURCE
)
if RECEIPT_SPEC is None or RECEIPT_SPEC.loader is None:
    raise RuntimeError(f"could not load {RECEIPT_SOURCE}")
RECEIPT = importlib.util.module_from_spec(RECEIPT_SPEC)
sys.modules[RECEIPT_SPEC.name] = RECEIPT
RECEIPT_SPEC.loader.exec_module(RECEIPT)
PROTOCOL = json.loads(
    (ROOT / "data" / "formal-verification" / "vero" / "policy-probe-protocol.v1.json").read_text(
        encoding="utf-8"
    )
)


class VeroSandboxConfigurationTest(unittest.TestCase):
    def config(self, workspace: Path) -> SANDBOX.SandboxConfig:
        return SANDBOX.SandboxConfig(
            docker="/usr/bin/docker",
            image="example.test/vero@sha256:" + "a" * 64,
            workspace=workspace,
            container_workspace="/workspace",
            user="1000:1000",
            memory="32g",
            cpus=8,
            pids=512,
            maximum_command_seconds=1200,
            maximum_output_bytes=1024,
            maximum_file_bytes=1024 * 1024,
        )

    def test_runtime_command_enforces_primary_isolation_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command = SANDBOX.docker_run_command(self.config(Path(directory)), "attempt")
        joined = " ".join(command)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("no-new-privileges", command)
        self.assertIn("--pids-limit 512", joined)
        self.assertNotIn("/var/run/docker.sock", joined)

    def test_mutable_image_reference_is_rejected(self) -> None:
        with self.assertRaises(SANDBOX.SandboxError):
            SANDBOX.validate_image_reference("example.test/vero:latest")

    def test_malformed_image_digest_is_rejected(self) -> None:
        with self.assertRaises(SANDBOX.SandboxError):
            SANDBOX.validate_image_reference("example.test/vero@sha256:short")

    def test_container_workspace_cannot_be_root(self) -> None:
        with self.assertRaises(SANDBOX.SandboxError):
            SANDBOX.validate_container_workspace("/")

    def test_output_truncation_is_explicit_and_bounded(self) -> None:
        output = SANDBOX.decode_bounded(b"x" * 96, True, 96)
        self.assertLessEqual(len(output.encode("utf-8")), 96)
        self.assertIn("output truncated", output)


class VeroSandboxProtocolTest(unittest.TestCase):
    def test_initialize_exposes_only_the_container_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = VeroSandboxConfigurationTest().config(Path(directory))
            receipt = SANDBOX.Receipt(
                attempt_id="attempt-1",
                task_id="task-1",
                started_at="2026-11-07T00:00:00+00:00",
                image_reference=config.image,
                model_artifact_digest="sha256:" + "b" * 64,
                inference_config_digest="sha256:" + "c" * 64,
                workspace=directory,
                container_name="attempt",
                resource_limits={},
                workspace_pre_sha256="d" * 64,
            )
            sandbox = SANDBOX.DockerSandbox(config, receipt)
            result = asyncio.run(
                SANDBOX.dispatch(
                    {
                        "method": "agent/initialize",
                        "params": {"protocolVersion": 2, "vibeVersion": "3.1.0"},
                    },
                    sandbox,
                )
            )
        self.assertEqual(result["workspace"], "/workspace")
        self.assertEqual(result["python"], "/usr/bin/python3")
        self.assertNotIn(directory, str(result))

    def test_tree_digest_records_links_without_following_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "task.txt").write_text("task\n", encoding="utf-8")
            (root / "outside").symlink_to("/private/host/secret")
            first = SANDBOX.tree_digest(root)
            (root / "task.txt").write_text("changed\n", encoding="utf-8")
            second = SANDBOX.tree_digest(root)
        self.assertNotEqual(first, second)


class VeroSandboxReceiptTest(unittest.TestCase):
    @staticmethod
    def valid_receipt() -> dict:
        return {
            "attempt_id": "attempt-1",
            "task_id": "task-1",
            "started_at": "2026-11-07T00:00:00+00:00",
            "ended_at": "2026-11-07T00:01:00+00:00",
            "image_reference": "example.test/vero@sha256:" + "a" * 64,
            "model_artifact_digest": "sha256:" + "b" * 64,
            "inference_config_digest": "sha256:" + "c" * 64,
            "workspace": "/runtime/task",
            "container_name": "attempt",
            "container_id": "container-id",
            "image_id": "sha256:" + "a" * 64,
            "container_runtime_version": "27.4.0/27.4.0",
            "resource_limits": {
                "memory": "32g",
                "cpus": 8,
                "pids": 512,
                "maximum_command_seconds": 1200,
                "maximum_output_bytes": 1024,
                "maximum_file_bytes": 1024 * 1024,
            },
            "workspace_pre_sha256": "d" * 64,
            "workspace_post_sha256": "e" * 64,
            "methods": {"agent/initialize": 1, "sandbox/execute": 3},
            "command_timeouts": 0,
            "output_truncations": 0,
            "infrastructure_errors": [],
            "container_removed": True,
        }

    def test_completed_receipt_passes(self) -> None:
        RECEIPT.validate(self.valid_receipt(), PROTOCOL)

    def test_receipt_rejects_failed_cleanup(self) -> None:
        receipt = self.valid_receipt()
        receipt["container_removed"] = False
        with self.assertRaises(RECEIPT.ReceiptError):
            RECEIPT.validate(receipt, PROTOCOL)


if __name__ == "__main__":
    unittest.main()
