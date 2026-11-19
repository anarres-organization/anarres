from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
VERO_ROOT = ROOT / "data" / "formal-verification" / "vero"
if str(VERO_ROOT) not in sys.path:
    sys.path.insert(0, str(VERO_ROOT))
CONTRACT_PATH = VERO_ROOT / "containment-contract-codex-sol.v3.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load(name: str, filename: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, VERO_ROOT / filename)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


PROBE = load("run_codex_sol_probe", "run_codex_sol_probe.py")
RUNNER = load("vero_run_containment_tests", "run_containment_tests.py")
VALIDATOR = load("vero_validate_task_boundary_receipt", "validate_task_boundary_receipt.py")


class FakeSandboxClient:
    """Answer agent-socket calls in memory and record every requested timeout."""

    def __init__(self, delay: float = 0.0) -> None:
        self.calls: list[tuple[str, object]] = []
        self.delay = delay

    def execute(self, command: str, cwd: str, timeout: float | None = None) -> dict:
        self.calls.append(("execute", timeout))
        if self.delay:
            time.sleep(min(self.delay, timeout or self.delay))
        return {"result": {"exitCode": 0, "stdout": "", "stderr": ""}}

    def read_file(self, path: str, max_bytes: int = 65536) -> dict:
        self.calls.append(("read", path))
        return {"result": {"contentBase64": None}}


def attempt(**fields: object) -> object:
    result = PROBE.AttemptResult("attempt", "primepy", "proof", 0)
    for name, value in fields.items():
        setattr(result, name, value)
    return result


class TaskSandboxRouteTest(unittest.TestCase):
    def command(self) -> list[str]:
        return PROBE.sandbox_server_command(
            python="/usr/bin/python3",
            socket_path=Path("/tmp/vero-test/s.sock"),
            image="sha256:" + "a" * 64,
            workspace=Path("/tmp/task"),
            receipt_path=Path("/tmp/receipt.json"),
            container_name_file=Path("/tmp/container-name"),
            attempt_id="attempt",
            task_id="primepy:proof",
            inference_config_digest="sha256:" + "b" * 64,
        )

    def option(self, command: list[str], flag: str) -> str:
        return command[command.index(flag) + 1]

    def test_route_runs_unprivileged_with_contract_limits(self) -> None:
        command = self.command()
        limits = CONTRACT["execution_boundaries"]["resource_limits"]
        self.assertNotEqual(self.option(command, "--user"), "0:0")
        self.assertEqual(int(self.option(command, "--pids")), limits["processes"])
        self.assertEqual(
            RUNNER.parse_memory(self.option(command, "--memory")), limits["memory_bytes"]
        )
        self.assertEqual(float(self.option(command, "--cpus")), limits["cpus"])
        self.assertEqual(int(self.option(command, "--maximum-file-bytes")), limits["file_bytes"])
        self.assertEqual(
            float(self.option(command, "--maximum-command-seconds")), limits["command_seconds"]
        )
        self.assertIn("--container-name-file", command)

    def test_controller_limits_match_contract(self) -> None:
        limits = CONTRACT["execution_boundaries"]["controller_limits"]
        self.assertEqual(PROBE.MAX_WALL_SECONDS, limits["wall_seconds"])
        self.assertEqual(PROBE.MAX_AGENT_TURNS, limits["turns"])
        self.assertEqual(PROBE.MAX_COMPLETION_TOKENS, limits["response_tokens"])
        self.assertEqual(PROBE.MAX_TOKENS_PER_ATTEMPT, limits["cumulative_output_tokens"])
        self.assertEqual(PROBE.HARNESS_VERSION, CONTRACT["interface"]["agent_harness_version"])

    def test_socket_paths_are_unique_short_and_fresh(self) -> None:
        paths = {PROBE.new_socket_path() for _ in range(64)}
        self.assertEqual(len(paths), 64)
        for path in paths:
            self.assertLess(len(str(path)), 100)
            self.assertFalse(path.parent.exists())

    def test_leftover_container_is_removed_only_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            name_file = Path(directory) / "container-name"
            self.assertFalse(PROBE.remove_leftover_container(name_file))
            name_file.write_text("anarres-vero-test\n", encoding="utf-8")
            calls: list[list[str]] = []

            def fake_run(arguments: list[str], **_: object) -> subprocess.CompletedProcess:
                calls.append(arguments)
                return subprocess.CompletedProcess(arguments, 0, "[]", "")

            with mock.patch.object(PROBE.subprocess, "run", side_effect=fake_run):
                self.assertTrue(PROBE.remove_leftover_container(name_file, "docker"))
        self.assertEqual(calls[-1][1:], ["rm", "--force", "anarres-vero-test"])


class ScoringTest(unittest.TestCase):
    def test_grader_failure_raises_instead_of_scoring_zero(self) -> None:
        failed = subprocess.CompletedProcess([], 1, "", "Traceback")
        image = "sha256:" + "d" * 64
        with tempfile.TemporaryDirectory() as directory:
            evaluation = Path(directory)
            with (
                mock.patch.object(PROBE.subprocess, "run", return_value=failed),
                self.assertRaises(PROBE.GradeInfrastructureError),
            ):
                PROBE.grade_attempt(
                    Path("/v"),
                    "python",
                    Path("/b"),
                    Path("/s"),
                    "proof",
                    evaluation,
                    docker_image=image,
                )
            unreadable = subprocess.CompletedProcess([], 0, "not json", "")
            with (
                mock.patch.object(PROBE.subprocess, "run", return_value=unreadable),
                self.assertRaises(PROBE.GradeInfrastructureError),
            ):
                PROBE.grade_attempt(
                    Path("/v"),
                    "python",
                    Path("/b"),
                    Path("/s"),
                    "proof",
                    evaluation / "x",
                    docker_image=image,
                )

    def test_grader_compiles_only_through_the_contained_lake(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            shim = PROBE.grader_lake_shim(Path(directory), "sha256:" + "d" * 64, "label")
            text = shim.read_text(encoding="utf-8")
        self.assertEqual(shim.name, "lake")
        for flag in (
            "--network none",
            "--ipc none",
            "--read-only",
            "--cap-drop ALL",
            "no-new-privileges",
            "/dev/mqueue:ro",
            "anarres.grader=label",
        ):
            self.assertIn(flag, text)
        # Sources are read-only; only Lake's build directory is writable.
        self.assertIn('--mount "type=bind,src=$here,dst=$here,readonly"', text)
        self.assertIn('--mount "type=bind,src=$here/.lake,dst=$here/.lake"', text)
        self.assertEqual(text.count("--mount"), 2)
        self.assertIn(f"{PROBE.GRADER_LAKE_SECONDS}s lake", text)
        self.assertLess(PROBE.GRADER_LAKE_SECONDS, PROBE.VERO_LAKE_SECONDS)
        self.assertNotIn("--user 0:0", text)

    def test_elaboration_time_code_is_recognized(self) -> None:
        pattern = re.compile(PROBE.ELABORATION_PATTERN)
        for line in (
            "#eval IO.println 1",
            "  open Foo in #check x",
            "theorem t : True := by native_decide",
            "@[implemented_by g] def f := 1",
            "macro_rules | `(x) => `(y)",
            "run_cmd pure ()",
            "initialize counter : IO.Ref Nat ← IO.mkRef 0",
        ):
            self.assertIsNotNone(pattern.search(line), line)
        for line in (
            "  exact foo",
            "  simp [List.range, Nat.succ]",
            "def elab_helper := 1",
            "  exact h'.syntax",
            "  exact #[1, 2].size",
        ):
            self.assertIsNone(pattern.search(line), line)

    def test_task_links_outside_the_boundary_block_grading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "task"
            (root / "Pkg").mkdir(parents=True)
            (root / "Pkg" / "Proof.lean").write_text("theorem t : True := trivial\n")
            (root / "inside").symlink_to(root / "Pkg" / "Proof.lean")
            self.assertEqual(PROBE.escaping_entries(root), [])
            (root / "Pkg" / "escape").symlink_to(Path(directory))
            self.assertEqual(PROBE.escaping_entries(root), ["Pkg/escape"])
        unsafe = attempt(integrity_errors=["task contains entries outside the boundary"])
        unsafe.grade = {"passed_specs": 9, "total_specs": 9}
        self.assertFalse(unsafe.scored)

    def test_summary_excludes_infrastructure_invalid_attempts(self) -> None:
        scored = attempt(grade={"passed_specs": 3, "total_specs": 9})
        failed = attempt(
            benchmark_id="arithmetic-v2",
            infrastructure_errors=["sandbox: container cleanup failed"],
            grade={"passed_specs": 0, "total_specs": 191},
        )
        ungraded = attempt(benchmark_id="piggybank-v2")
        totals = PROBE.summarize([scored, failed, ungraded])
        self.assertEqual(totals["scored_attempts"], 1)
        self.assertEqual(totals["infrastructure_invalid_attempts"], 1)
        self.assertEqual(totals["ungraded_attempts"], 1)
        self.assertEqual((totals["total_passed_specs"], totals["total_specs"]), (3, 9))
        self.assertEqual([row["passed_specs"] for row in totals["per_attempt"]], [3, None, None])
        self.assertFalse(totals["screen_pass"])

    def test_summary_without_scored_attempts_has_no_rate(self) -> None:
        totals = PROBE.summarize([attempt(infrastructure_errors=["grade: failed"])])
        self.assertIsNone(totals["pooled_strict_rate"])
        self.assertEqual(totals["total_specs"], 0)


class AgentLoopLimitTest(unittest.TestCase):
    def run_loop(self, policy: object, client: object, **options: object) -> object:
        result = attempt()
        PROBE.run_agent_loop(
            "instruction", client, "/workspace", result, "", responder=policy, **options
        )
        return result

    def test_turn_limit(self) -> None:
        result = self.run_loop(
            RUNNER.RepeatingPolicy("sandbox_execute", {"command": "true"}), FakeSandboxClient()
        )
        self.assertEqual(result.stop_reason, "max_turns")
        self.assertEqual(result.turns, PROBE.MAX_AGENT_TURNS)
        self.assertEqual(result.tool_calls, PROBE.MAX_AGENT_TURNS)

    def test_cumulative_token_limit(self) -> None:
        policy = RUNNER.RepeatingPolicy(
            "sandbox_execute",
            {"command": "true"},
            output_tokens=PROBE.MAX_TOKENS_PER_ATTEMPT // 2 + 1,
        )
        result = self.run_loop(policy, FakeSandboxClient())
        self.assertEqual(result.stop_reason, "token_limit")
        self.assertEqual(result.turns, 2)

    def test_wall_deadline_bounds_tool_commands(self) -> None:
        client = FakeSandboxClient(delay=5)
        policy = RUNNER.RepeatingPolicy("sandbox_execute", {"command": "sleep 60", "timeout": 300})
        started = time.monotonic()
        result = self.run_loop(policy, client, wall_seconds=0.5)
        self.assertEqual(result.stop_reason, "wall_time_limit")
        self.assertLess(time.monotonic() - started, 3)
        self.assertTrue(all(timeout <= 0.5 for _, timeout in client.calls))
        self.assertEqual(result.infrastructure_errors, [])

    def test_request_failure_inside_budget_is_infrastructure(self) -> None:
        def failing(*_: object, **__: object) -> dict:
            raise RuntimeError("OpenAI HTTP 500")

        result = self.run_loop(failing, FakeSandboxClient())
        self.assertEqual(result.stop_reason, "infrastructure_error")
        self.assertFalse(result.scored)

    def test_request_error_after_deadline_is_still_infrastructure(self) -> None:
        def late_failure(*_: object, timeout: float, **__: object) -> dict:
            time.sleep(timeout)
            raise RuntimeError("OpenAI HTTP 503")

        result = self.run_loop(late_failure, FakeSandboxClient(), wall_seconds=0.2)
        self.assertEqual(result.stop_reason, "infrastructure_error")

    def test_malformed_model_arguments_return_to_the_model(self) -> None:
        client = FakeSandboxClient()
        for name, arguments in (
            ("sandbox_execute", {"command": "true", "timeout": "60"}),
            ("sandbox_execute", {"cwd": "/workspace"}),
            ("sandbox_execute", {"command": "true", "timeout": True}),
            ("sandbox_read_file", {"path": "/workspace/x", "maxBytes": "10"}),
            ("sandbox_read_file", []),
        ):
            output = PROBE._execute_tool(name, arguments, client, "/workspace", 10.0)
            self.assertTrue(output.startswith("Error:"), (name, arguments))
        self.assertEqual(client.calls, [])
        policy = RUNNER.ScriptedPolicy([("sandbox_execute", {"command": 7})])
        result = self.run_loop(policy, client)
        self.assertEqual(result.stop_reason, "stop")
        self.assertEqual(result.infrastructure_errors, [])

    def test_null_arguments_do_not_crash_the_loop(self) -> None:
        def null_arguments(*_: object, **__: object) -> dict:
            null_arguments.calls += 1
            if null_arguments.calls > 1:
                return {"output": [], "usage": {}}
            call = {"type": "function_call", "name": "sandbox_execute", "call_id": "x"}
            return {"output": [{**call, "arguments": None}], "usage": {}}

        null_arguments.calls = 0
        result = self.run_loop(null_arguments, FakeSandboxClient())
        self.assertEqual(result.infrastructure_errors, [])

    def test_request_cut_off_by_deadline_is_the_wall_limit(self) -> None:
        def slow(*_: object, timeout: float, **__: object) -> dict:
            time.sleep(timeout)
            raise TimeoutError("timed out")

        result = self.run_loop(slow, FakeSandboxClient(), wall_seconds=0.2)
        self.assertEqual(result.stop_reason, "wall_time_limit")
        self.assertEqual(result.infrastructure_errors, [])

    def test_undeclared_tool_never_reaches_the_sandbox(self) -> None:
        client = FakeSandboxClient()
        output = PROBE._execute_tool("shell_on_controller", {"command": "id"}, client, "/w")
        self.assertTrue(output.startswith("Error: unknown tool"))
        self.assertEqual(client.calls, [])


class DecisionRuleTest(unittest.TestCase):
    def test_only_the_emulator_cache_is_tolerated_and_only_when_emulated(self) -> None:
        self.assertTrue(RUNNER.allowed_runtime_entries([], emulated=False))
        self.assertFalse(RUNNER.allowed_runtime_entries([".cache", ".cache/rosetta"], False))
        self.assertTrue(RUNNER.allowed_runtime_entries([".cache", ".cache/rosetta"], True))
        self.assertFalse(RUNNER.allowed_runtime_entries([".cache", ".bash_history"], True))
        self.assertFalse(RUNNER.allowed_runtime_entries(None, True))

    def test_undeclared_mount_is_reported(self) -> None:
        mounts = ["/", "/workspace", "/tmp", "/cache", "/proc/kcore", "/sys/fs/cgroup"]
        self.assertEqual(RUNNER.undeclared_mounts(mounts), [])
        self.assertEqual(RUNNER.undeclared_mounts([*mounts, "/opt/vero"]), ["/opt/vero"])

    def test_writes_outside_declared_roots_are_reported(self) -> None:
        writable = ["/workspace", "/workspace/Primepy", "/tmp/home", "/cache"]
        self.assertEqual(RUNNER.undeclared_writes(writable), [])
        self.assertEqual(
            RUNNER.undeclared_writes([*writable, "/dev/shm", "/tmpfoo"]), ["/dev/shm", "/tmpfoo"]
        )

    def test_environment_is_an_allowlist(self) -> None:
        self.assertEqual(RUNNER.undeclared_environment(["PATH", "HOME"]), [])
        self.assertEqual(
            RUNNER.undeclared_environment(["PATH", "OPENAI_API_KEY"]), ["OPENAI_API_KEY"]
        )

    def test_slot_replacement_preserves_markers_and_matches_exactly(self) -> None:
        text = (
            "-- !benchmark @start global_aux\n"
            "-- !benchmark @end global_aux\n"
            "-- !benchmark @start proof def=prove_a_b kind=prove target=spec_a_b\n"
            "  sorry\n"
            "-- !benchmark @end proof def=prove_a_b\n"
            "-- !benchmark @start proof def=prove_a kind=prove target=spec_a\n"
            "  sorry\n"
            "-- !benchmark @end proof def=prove_a\n"
        )
        edited = RUNNER.replace_slot(text, "proof", "  exact x\n", definition_prefix="prove_a")
        self.assertEqual(edited.count("  exact x\n"), 1)
        self.assertIn("def=prove_a kind=prove target=spec_a\n  exact x\n", edited)
        self.assertEqual(
            [line for line in edited.splitlines() if line.startswith("--")],
            [line for line in text.splitlines() if line.startswith("--")],
        )
        aux = RUNNER.replace_slot(text, "global_aux", "theorem helper : True := trivial\n")
        self.assertIn("@start global_aux\ntheorem helper", aux)
        self.assertEqual(RUNNER.target_definition(text), "prove_a_b")
        self.assertEqual(RUNNER.spec_status({"spec_a": "failed"}, "prove_a"), "failed")

    def test_runtime_agreement_detects_each_mismatch(self) -> None:
        source = {
            "status": "qualified",
            "source_id": "vero",
            "source_revision": "git:abc",
            "source_pin_sha256": "sha256:p",
            "lean_version": "4.29.1",
            "modes": ["proof", "codeproof"],
        }
        runtime = {
            "status": "qualified",
            "source_id": "vero",
            "source_revision": "git:abc",
            "source_pin_sha256": "sha256:p",
            "mode": "proof",
            "toolchain": {"lean_version": "4.29.1"},
            "sandbox": {
                "task_visibility": "task-only",
                "tool_allowlist": ["sandbox/execute", "sandbox/readFile"],
            },
            "network": {
                "task_external_egress": False,
                "controller_allowlist": ["http://127.0.0.1:8000"],
            },
            "resources": {"processes": 256, "memory_bytes": 16, "file_bytes": 8},
            "limits": {
                "wall_seconds": 5400,
                "turns": 100,
                "response_tokens": 16384,
                "cumulative_tokens": 200000,
            },
        }
        observed = {
            "source_id": "vero",
            "source_revision": "git:abc",
            "source_pin_sha256": "sha256:p",
            "mode": "proof",
            "sandbox_lean_version": "4.29.1",
            "grader_lean_version": "4.29.1",
            "sandbox_methods": ["sandbox/readFile", "sandbox/execute"],
            "controller_endpoint": "http://127.0.0.1:8000",
            "pids": 256,
            "memory_bytes": 16,
            "file_bytes": 8,
            "wall_seconds": 5400,
            "turns": 100,
            "response_tokens": 16384,
            "cumulative_tokens": 200000,
        }
        agreement = RUNNER.runtime_agreement(source, runtime, observed)
        self.assertTrue(all(agreement.values()))
        self.assertEqual(set(agreement), VALIDATOR.REQUIRED_AGREEMENT)
        changed = {**observed, "pids": 512, "grader_lean_version": "4.18.0"}
        agreement = RUNNER.runtime_agreement(source, runtime, changed)
        self.assertEqual(
            sorted(name for name, ok in agreement.items() if not ok),
            ["lean_version", "process_limit"],
        )

    def test_runner_covers_the_contract_test_set_exactly(self) -> None:
        source = (VERO_ROOT / "run_containment_tests.py").read_text(encoding="utf-8")
        produced = re.findall(r'outcome\(\s*"(\w+)"', source)
        declared = VALIDATOR.validate_contract(CONTRACT)
        self.assertEqual(sorted(produced), sorted(declared))
        self.assertEqual(len(produced), len(set(produced)))


class ReceiptValidationTest(unittest.TestCase):
    def receipt(self) -> dict:
        materialization = {"task_tree_sha256": "t", "instruction_sha256": "i"}
        receipt = {
            "schema_version": VALIDATOR.RECEIPT_SCHEMA,
            "contract_id": CONTRACT["contract_id"],
            "contract_sha256": f"sha256:{hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()}",
            "runtime_image": {
                "reference": "sha256:" + "c" * 64,
                "platform": {"image": "amd64", "host": "amd64", "emulated": False},
            },
            "route": {
                "harness_version": CONTRACT["interface"]["agent_harness_version"],
                "sandbox_methods": list(CONTRACT["interface"]["sandbox_methods"]),
                "resource_limits": dict(CONTRACT["execution_boundaries"]["resource_limits"]),
                "controller_limits": {
                    key: value
                    for key, value in CONTRACT["execution_boundaries"]["controller_limits"].items()
                    if not key.endswith("_rule")
                },
            },
            "controller": {
                "policy_contacted": False,
                "model_id": CONTRACT["interface"]["model_id"],
            },
            "task": {
                "materializations": {"a": materialization, "b": dict(materialization)},
                "protected_repositories_opened": False,
            },
            "reports": {
                "bound": True,
                "source_report_sha256": "sha256:s",
                "runtime_report_sha256": "sha256:r",
                "agreement": dict.fromkeys(VALIDATOR.REQUIRED_AGREEMENT, True),
            },
            "tests": [
                {"id": test["id"], "passed": True, "evidence": {}}
                for test in CONTRACT["required_tests"]
            ],
            "all_tests_passed": True,
            "qualified": True,
            "files": {},
        }
        receipt["receipt_id"] = RUNNER.receipt_id(receipt)
        return receipt

    def validate(self, receipt: dict, bundle: Path | None = None) -> None:
        VALIDATOR.validate_receipt(
            receipt, CONTRACT, hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(), bundle
        )

    def test_consistent_receipt_validates(self) -> None:
        self.validate(self.receipt())

    def test_edited_receipt_is_rejected(self) -> None:
        receipt = self.receipt()
        receipt["tests"][0]["passed"] = False
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "identifier"):
            self.validate(receipt)

    def test_qualification_requires_every_test_and_agreement(self) -> None:
        failing = self.receipt()
        failing["tests"][3]["passed"] = False
        failing["all_tests_passed"] = False
        failing["receipt_id"] = RUNNER.receipt_id(failing)
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "qualification disagrees"):
            self.validate(failing)
        disagreeing = self.receipt()
        disagreeing["reports"]["agreement"]["mode"] = False
        disagreeing["receipt_id"] = RUNNER.receipt_id(disagreeing)
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "qualification disagrees"):
            self.validate(disagreeing)

    def test_emulated_execution_never_qualifies(self) -> None:
        receipt = self.receipt()
        receipt["runtime_image"]["platform"]["emulated"] = True
        receipt["receipt_id"] = RUNNER.receipt_id(receipt)
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "qualification disagrees"):
            self.validate(receipt)
        receipt["qualified"] = False
        receipt["receipt_id"] = RUNNER.receipt_id(receipt)
        self.validate(receipt)

    def test_receipt_must_match_contract_limits_and_agreement_keys(self) -> None:
        changed = self.receipt()
        changed["route"]["resource_limits"]["processes"] = 4096
        changed["receipt_id"] = RUNNER.receipt_id(changed)
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "resource limits"):
            self.validate(changed)
        partial = self.receipt()
        partial["reports"]["agreement"] = {"source_identity": True}
        partial["qualified"] = True
        partial["receipt_id"] = RUNNER.receipt_id(partial)
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "every field-level agreement"):
            self.validate(partial)

    def test_missing_or_duplicate_test_is_rejected(self) -> None:
        receipt = self.receipt()
        receipt["tests"][-1] = copy.deepcopy(receipt["tests"][0])
        receipt["receipt_id"] = RUNNER.receipt_id(receipt)
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "exactly once"):
            self.validate(receipt)

    def test_bundle_files_must_match_their_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            (bundle / "sandbox-receipt-c.json").write_text("{}\n", encoding="utf-8")
            receipt = self.receipt()
            receipt["files"] = {"sandbox-receipt-c.json": "sha256:" + "0" * 64}
            receipt["receipt_id"] = RUNNER.receipt_id(receipt)
            with self.assertRaisesRegex(VALIDATOR.BoundaryError, "hash disagrees"):
                self.validate(receipt, bundle)

    def test_contract_rejects_root_container_user(self) -> None:
        contract = copy.deepcopy(CONTRACT)
        contract["execution_boundaries"]["task_sandbox"]["container_user"] = "root"
        with self.assertRaisesRegex(VALIDATOR.BoundaryError, "container root"):
            VALIDATOR.validate_contract(contract)


class FormalCliBoundaryTest(unittest.TestCase):
    def test_boundary_is_reported_separately_and_blocks_policy_probe(self) -> None:
        from anarres_formal_adapter import cli

        arguments = argparse.Namespace(repository=ROOT)
        report = cli.command_qualification(arguments)
        boundary = report["task_only_boundary"]
        self.assertEqual(boundary["contract_id"], CONTRACT["contract_id"])
        self.assertFalse(boundary["qualified"])
        self.assertFalse(boundary["receipt_released"])
        self.assertEqual(boundary["required_tests"], len(CONTRACT["required_tests"]))
        self.assertFalse(report["containment"]["task_only_boundary_passed"])
        self.assertFalse(report["decision"]["repeated_measurement_authorized"])
        status = cli.command_status(arguments)
        self.assertFalse(status["task_only_boundary_qualified"])
        self.assertFalse(status["policy_probe_available"])


if __name__ == "__main__":
    unittest.main()
