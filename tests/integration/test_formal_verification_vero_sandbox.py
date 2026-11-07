from __future__ import annotations

import asyncio
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERO_ROOT = ROOT / "data" / "formal-verification" / "vero"
if str(VERO_ROOT) not in sys.path:
    sys.path.insert(0, str(VERO_ROOT))
SOURCE = VERO_ROOT / "serve_vibe_sandbox.py"
RECEIPT_SOURCE = VERO_ROOT / "validate_sandbox_receipt.py"
RUNNER_SOURCE = VERO_ROOT / "run_probe_attempt.py"
RUNTIME_ROOT = VERO_ROOT / "runtime"
RUNTIME_SOURCE = RUNTIME_ROOT / "validate_runtime_lock.py"
CONTROLLER_ROOT = ROOT / "data" / "formal-verification" / "vero" / "controller"
CONTROLLER_SOURCE = CONTROLLER_ROOT / "validate_controller_lock.py"
INFERENCE_ROOT = ROOT / "data" / "formal-verification" / "vero" / "inference"
INFERENCE_SOURCE = INFERENCE_ROOT / "validate_inference_contract.py"
INFERENCE_QUALIFICATION_SOURCE = INFERENCE_ROOT / "qualify_inference_deployment.py"
MATERIALIZER_SOURCE = ROOT / "data" / "formal-verification" / "vero" / "materialize_probe_task.py"
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
RUNTIME_SPEC = importlib.util.spec_from_file_location("vero_validate_runtime_lock", RUNTIME_SOURCE)
if RUNTIME_SPEC is None or RUNTIME_SPEC.loader is None:
    raise RuntimeError(f"could not load {RUNTIME_SOURCE}")
RUNTIME = importlib.util.module_from_spec(RUNTIME_SPEC)
sys.modules[RUNTIME_SPEC.name] = RUNTIME
RUNTIME_SPEC.loader.exec_module(RUNTIME)
CONTROLLER_SPEC = importlib.util.spec_from_file_location(
    "vero_validate_controller_lock", CONTROLLER_SOURCE
)
if CONTROLLER_SPEC is None or CONTROLLER_SPEC.loader is None:
    raise RuntimeError(f"could not load {CONTROLLER_SOURCE}")
CONTROLLER = importlib.util.module_from_spec(CONTROLLER_SPEC)
sys.modules[CONTROLLER_SPEC.name] = CONTROLLER
CONTROLLER_SPEC.loader.exec_module(CONTROLLER)
INFERENCE_SPEC = importlib.util.spec_from_file_location(
    "vero_validate_inference_contract", INFERENCE_SOURCE
)
if INFERENCE_SPEC is None or INFERENCE_SPEC.loader is None:
    raise RuntimeError(f"could not load {INFERENCE_SOURCE}")
INFERENCE = importlib.util.module_from_spec(INFERENCE_SPEC)
sys.modules[INFERENCE_SPEC.name] = INFERENCE
INFERENCE_SPEC.loader.exec_module(INFERENCE)
INFERENCE_QUALIFICATION_SPEC = importlib.util.spec_from_file_location(
    "vero_qualify_inference_deployment", INFERENCE_QUALIFICATION_SOURCE
)
if INFERENCE_QUALIFICATION_SPEC is None or INFERENCE_QUALIFICATION_SPEC.loader is None:
    raise RuntimeError(f"could not load {INFERENCE_QUALIFICATION_SOURCE}")
INFERENCE_QUALIFICATION = importlib.util.module_from_spec(INFERENCE_QUALIFICATION_SPEC)
sys.modules[INFERENCE_QUALIFICATION_SPEC.name] = INFERENCE_QUALIFICATION
INFERENCE_QUALIFICATION_SPEC.loader.exec_module(INFERENCE_QUALIFICATION)
MATERIALIZER_SPEC = importlib.util.spec_from_file_location(
    "vero_materialize_probe_task", MATERIALIZER_SOURCE
)
if MATERIALIZER_SPEC is None or MATERIALIZER_SPEC.loader is None:
    raise RuntimeError(f"could not load {MATERIALIZER_SOURCE}")
MATERIALIZER = importlib.util.module_from_spec(MATERIALIZER_SPEC)
sys.modules[MATERIALIZER_SPEC.name] = MATERIALIZER
MATERIALIZER_SPEC.loader.exec_module(MATERIALIZER)
RUNNER_SPEC = importlib.util.spec_from_file_location("vero_run_probe_attempt", RUNNER_SOURCE)
if RUNNER_SPEC is None or RUNNER_SPEC.loader is None:
    raise RuntimeError(f"could not load {RUNNER_SOURCE}")
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER
RUNNER_SPEC.loader.exec_module(RUNNER)
PROTOCOL = json.loads(
    (ROOT / "data" / "formal-verification" / "vero" / "policy-probe-protocol.v1.json").read_text(
        encoding="utf-8"
    )
)
RUNTIME_LOCK_PATH = RUNTIME_ROOT / "runtime-lock.v1.json"
RUNTIME_LOCK = json.loads(RUNTIME_LOCK_PATH.read_text(encoding="utf-8"))
CONTROLLER_LOCK_PATH = CONTROLLER_ROOT / "controller-lock.v1.json"
CONTROLLER_LOCK = json.loads(CONTROLLER_LOCK_PATH.read_text(encoding="utf-8"))
INFERENCE_CONTRACT_PATH = INFERENCE_ROOT / "inference-contract.v1.json"
INFERENCE_CONTRACT = json.loads(INFERENCE_CONTRACT_PATH.read_text(encoding="utf-8"))
PROTOCOL_PATH = ROOT / "data" / "formal-verification" / "vero" / "policy-probe-protocol.v1.json"
PANEL = json.loads(
    (
        ROOT / "data" / "formal-verification" / "vero" / "development-lifecycle-panel-v2.json"
    ).read_text(encoding="utf-8")
)
SPLIT = json.loads(
    (ROOT / "data" / "formal-verification" / "vero" / "repository-split.json").read_text(
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
            "peak_memory_bytes": 1024 * 1024,
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

    def test_receipt_requires_positive_peak_memory(self) -> None:
        receipt = self.valid_receipt()
        receipt["peak_memory_bytes"] = None
        with self.assertRaises(RECEIPT.ReceiptError):
            RECEIPT.validate(receipt, PROTOCOL)


class VeroRuntimeLockTest(unittest.TestCase):
    PANEL_PATH = (
        ROOT / "data" / "formal-verification" / "vero" / "development-lifecycle-panel-v2.json"
    )
    SOURCE_PIN_PATH = ROOT / "data" / "formal-verification" / "vero" / "source-pin.json"

    def test_pre_build_runtime_lock_matches_the_qualified_source(self) -> None:
        RUNTIME.validate(
            RUNTIME_LOCK,
            lock_path=RUNTIME_LOCK_PATH,
            panel_path=self.PANEL_PATH,
            source_pin_path=self.SOURCE_PIN_PATH,
        )

    def test_qualified_runtime_requires_a_receipt(self) -> None:
        lock = json.loads(RUNTIME_LOCK_PATH.read_text(encoding="utf-8"))
        lock["status"] = "qualified"
        lock["built_image_reference"] = "example.test/vero@sha256:" + "a" * 64
        lock["built_image_id"] = "sha256:" + "b" * 64
        with self.assertRaises(RUNTIME.RuntimeLockError):
            RUNTIME.validate(
                lock,
                lock_path=RUNTIME_LOCK_PATH,
                panel_path=self.PANEL_PATH,
                source_pin_path=self.SOURCE_PIN_PATH,
            )

    def test_qualified_runtime_accepts_separate_reference_and_image_id(self) -> None:
        lock = json.loads(RUNTIME_LOCK_PATH.read_text(encoding="utf-8"))
        lock["status"] = "qualified"
        lock["built_image_reference"] = "example.test/vero@sha256:" + "a" * 64
        lock["built_image_id"] = "sha256:" + "b" * 64
        lock["qualification_receipt"] = "qualification-receipt.json"
        RUNTIME.validate(
            lock,
            lock_path=RUNTIME_LOCK_PATH,
            panel_path=self.PANEL_PATH,
            source_pin_path=self.SOURCE_PIN_PATH,
        )


class VeroControllerLockTest(unittest.TestCase):
    def test_isolated_controller_matches_the_probe_protocol(self) -> None:
        CONTROLLER.validate(
            CONTROLLER_LOCK,
            lock_path=CONTROLLER_LOCK_PATH,
            protocol_path=PROTOCOL_PATH,
        )

    def test_controller_rejects_a_nonlocal_inference_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(CONTROLLER_ROOT, root / "controller")
            copied_root = root / "controller"
            agent_path = copied_root / "agents" / "lean.toml"
            agent_path.write_text(
                agent_path.read_text(encoding="utf-8").replace(
                    "http://127.0.0.1:8000/v1", "https://example.invalid/v1"
                ),
                encoding="utf-8",
            )
            lock = json.loads((copied_root / "controller-lock.v1.json").read_text(encoding="utf-8"))
            lock["api_base"] = "https://example.invalid/v1"
            lock["agent_sha256"] = CONTROLLER.digest(agent_path)
            with self.assertRaises(CONTROLLER.ControllerLockError):
                CONTROLLER.validate(
                    lock,
                    lock_path=copied_root / "controller-lock.v1.json",
                    protocol_path=PROTOCOL_PATH,
                )


class VeroInferenceContractTest(unittest.TestCase):
    def test_pre_deployment_inference_contract_matches_the_probe(self) -> None:
        INFERENCE.validate(
            INFERENCE_CONTRACT,
            protocol_path=PROTOCOL_PATH,
            controller_lock_path=CONTROLLER_LOCK_PATH,
        )

    def test_qualified_inference_requires_complete_deployment_evidence(self) -> None:
        contract = json.loads(INFERENCE_CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["status"] = "qualified"
        with self.assertRaises(INFERENCE.InferenceContractError):
            INFERENCE.validate(
                contract,
                protocol_path=PROTOCOL_PATH,
                controller_lock_path=CONTROLLER_LOCK_PATH,
            )

    def test_live_command_must_match_every_frozen_serving_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory).resolve()
            command = [
                "vllm",
                "serve",
                str(model),
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--max-model-len",
                "200000",
                "--tensor-parallel-size",
                "4",
                "--attention-backend",
                "FLASH_ATTN_MLA",
                "--tool-call-parser",
                "mistral",
                "--reasoning-parser",
                "mistral",
                "--served-model-name",
                "mistralai/Leanstral-1.5-119B-A6B",
                "--enable-auto-tool-choice",
                "--gpu-memory-utilization",
                "0.92",
                "--max-num-seqs",
                "8",
                "--dtype",
                "bfloat16",
            ]
            observed = INFERENCE_QUALIFICATION.validate_live_command(
                command, INFERENCE_CONTRACT, model
            )
        self.assertEqual(observed["gpu_memory_utilization"], 0.92)
        self.assertEqual(observed["max_num_seqs"], 8)

    def test_model_artifact_manifest_is_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text("{}\n", encoding="utf-8")
            first = INFERENCE_QUALIFICATION.artifact_manifest(root)
            (root / "config.json").write_text('{"changed":true}\n', encoding="utf-8")
            second = INFERENCE_QUALIFICATION.artifact_manifest(root)
        self.assertNotEqual(first["root_sha256"], second["root_sha256"])

    def test_vllm_version_gate_uses_semantic_components(self) -> None:
        self.assertGreaterEqual(
            INFERENCE_QUALIFICATION.version_tuple("0.24.1+cu128"),
            INFERENCE_QUALIFICATION.version_tuple("0.24.0"),
        )


class VeroTaskMaterializationTest(unittest.TestCase):
    def test_visible_tree_accepts_a_self_contained_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "INSTRUCTION.md").write_text("task\n", encoding="utf-8")
            (root / "Main.lean").write_text("example : True := by trivial\n", encoding="utf-8")
            counts = MATERIALIZER.validate_visible_tree(root)
        self.assertEqual(counts, {"files": 2, "symlinks": 0})

    def test_visible_tree_rejects_a_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "INSTRUCTION.md").write_text("task\n", encoding="utf-8")
            (root / "escape").symlink_to("/private/host/secret")
            with self.assertRaises(MATERIALIZER.MaterializationError):
                MATERIALIZER.validate_visible_tree(root)

    def test_only_the_frozen_development_panel_is_selectable(self) -> None:
        selected = MATERIALIZER.selected_repository(PANEL, SPLIT, "piggybank-v2")
        self.assertEqual(selected["source_language"], "coq")
        with self.assertRaises(MATERIALIZER.MaterializationError):
            MATERIALIZER.selected_repository(PANEL, SPLIT, "unicode-v2")


class VeroAttemptLauncherTest(unittest.TestCase):
    def test_pending_protocol_cannot_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            (task / "INSTRUCTION.md").write_text("task\n", encoding="utf-8")
            materialization = {
                "source_id": PROTOCOL["source"]["vero_id"],
                "mode": "proof",
                "task_tree_sha256": MATERIALIZER.tree_digest(task),
            }
            with self.assertRaises(RUNNER.AttemptLaunchError):
                RUNNER.validate_ready(
                    protocol=PROTOCOL,
                    containment=json.loads(
                        (VERO_ROOT / "containment-contract.v1.json").read_text(encoding="utf-8")
                    ),
                    runtime=RUNTIME_LOCK,
                    controller=CONTROLLER_LOCK,
                    inference=INFERENCE_CONTRACT,
                    materialization=materialization,
                    task=task,
                    image="sha256:" + "a" * 64,
                )

    def test_ready_launcher_matches_the_full_immutable_image_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            (task / "INSTRUCTION.md").write_text("task\n", encoding="utf-8")
            model_digest = "sha256:" + "c" * 64
            image = "example.test/vero@sha256:" + "a" * 64
            protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
            protocol["status"] = "frozen_ready"
            protocol["execution_authorized"] = True
            protocol["starting_policy"]["local_artifact_digest"] = model_digest
            containment = json.loads(
                (VERO_ROOT / "containment-contract.v1.json").read_text(encoding="utf-8")
            )
            containment["status"] = "qualified"
            containment["qualified"] = True
            runtime = json.loads(RUNTIME_LOCK_PATH.read_text(encoding="utf-8"))
            runtime["status"] = "qualified"
            runtime["built_image_reference"] = image
            inference = json.loads(INFERENCE_CONTRACT_PATH.read_text(encoding="utf-8"))
            inference["status"] = "qualified"
            inference["model"]["local_artifact_digest"] = model_digest
            materialization = {
                "source_id": protocol["source"]["vero_id"],
                "mode": "proof",
                "task_tree_sha256": MATERIALIZER.tree_digest(task),
            }
            RUNNER.validate_ready(
                protocol=protocol,
                containment=containment,
                runtime=runtime,
                controller=CONTROLLER_LOCK,
                inference=inference,
                materialization=materialization,
                task=task,
                image=image,
            )

    def test_vibe_command_contains_only_the_frozen_tool_allowlist(self) -> None:
        command = RUNNER.build_vibe_command(
            vibe=Path("/runtime/vibe"),
            prompt=Path("/runtime/prompt.txt"),
            socket=Path("/runtime/agent.sock"),
            output=Path("/runtime/output"),
            lock=CONTROLLER_LOCK,
        )
        enabled = [
            command[index + 1] for index, value in enumerate(command) if value == "--enabled-tools"
        ]
        self.assertEqual(enabled, CONTROLLER_LOCK["tool_allowlist"])
        self.assertNotIn("web_search", enabled)
        self.assertNotIn("task", enabled)

    def test_launcher_environment_matches_the_frozen_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = RUNNER.isolated_environment(root, Path("/runtime/bin/vibe"))
        self.assertEqual(sorted(environment), sorted(CONTROLLER_LOCK["environment_allowlist"]))


if __name__ == "__main__":
    unittest.main()
