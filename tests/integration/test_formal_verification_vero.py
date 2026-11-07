from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "data" / "formal-verification" / "vero"


def load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_module("vero_audit_source", ADAPTER / "audit_source.py")
RUNTIME = load_module("vero_audit_runtime", ADAPTER / "audit_runtime.py")
LIFECYCLE = load_module("vero_audit_task_lifecycle", ADAPTER / "audit_task_lifecycle.py")
PROBE = load_module("vero_validate_policy_probe", ADAPTER / "validate_policy_probe_protocol.py")
REPETITION = load_module(
    "vero_validate_repetition_design", ADAPTER / "validate_repetition_design.py"
)
QUEUE = load_module("vero_build_probe_queue", ADAPTER / "build_probe_queue.py")
AGGREGATE = load_module(
    "vero_aggregate_probe_measurements", ADAPTER / "aggregate_probe_measurements.py"
)
QUEUE_ITEM = load_module("vero_run_probe_queue_item", ADAPTER / "run_probe_queue_item.py")
CONTAINMENT = load_module("vero_validate_containment", ADAPTER / "validate_containment_contract.py")
SPLIT = json.loads((ADAPTER / "repository-split.json").read_text(encoding="utf-8"))
ORACLES = json.loads((ADAPTER / "development-oracle-panel.json").read_text(encoding="utf-8"))
LIFECYCLE_PANEL = json.loads(
    (ADAPTER / "development-lifecycle-panel-v2.json").read_text(encoding="utf-8")
)
PROBE_PROTOCOL_PATH = ADAPTER / "policy-probe-protocol.v1.json"
PROBE_PROTOCOL = json.loads(PROBE_PROTOCOL_PATH.read_text(encoding="utf-8"))
REPETITION_DESIGN_PATH = ADAPTER / "repetition-reliability.v1.json"
REPETITION_DESIGN = json.loads(REPETITION_DESIGN_PATH.read_text(encoding="utf-8"))
PROBE_QUEUE_PATH = ADAPTER / "probe-queue.v1.json"
PROBE_QUEUE = json.loads(PROBE_QUEUE_PATH.read_text(encoding="utf-8"))
CONTAINMENT_PATH = ADAPTER / "containment-contract.v1.json"
CONTAINMENT_CONTRACT = json.loads(CONTAINMENT_PATH.read_text(encoding="utf-8"))


def write_fixture(root: Path) -> dict:
    benchmark = root / "benchmarks" / "Example"
    files = {
        "LICENSE": "fixture license\n",
        "README.md": "fixture\n",
        "Example.lean": "import Example.Harness\n",
        "Example/Harness.lean": "def canonical := 1\n",
        "Example/Test.lean": "example : True := by trivial\n",
        "lakefile.toml": 'name = "Example"\n',
        "Example/Impl/Core.lean": "def value := 1\n",
        "Example/Spec/Core.lean": "def spec_value := value = 1\n",
    }
    for relative, content in files.items():
        path = benchmark / relative if relative not in {"LICENSE", "README.md"} else root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest = {
        "benchmark_id": "example-v1",
        "lean_version": "4.29.1",
        "modes_supported": ["proof", "codeproof"],
        "source": {
            "language": "python",
            "repo_url": "https://example.test/example",
            "commit_hash": "a" * 40,
        },
        "files": {
            "root_hub": "Example.lean",
            "harness": "Example/Harness.lean",
            "test": "Example/Test.lean",
            "lakefile": "lakefile.toml",
        },
        "packages": [
            {
                "name": "Example",
                "modules": [
                    {
                        "name": "Core",
                        "impl": "Example/Impl/Core.lean",
                        "spec": "Example/Spec/Core.lean",
                        "apis": [{"name": "value"}],
                        "specs": ["spec_value"],
                    }
                ],
            }
        ],
    }
    manifest_path = benchmark / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    artifacts = []
    for relative in ("LICENSE", "README.md"):
        path = root / relative
        artifacts.append(
            {
                "path": relative,
                "uri": f"https://example.test/{relative}",
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "media_type": "text/plain",
                "license": "MIT",
                "producing_run_or_upstream_release": "fixture-v1",
            }
        )

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD:benchmarks"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "schema_version": "anarres.formal-verification-source-pin.v1",
        "source_id": "fixture@v1",
        "commit": commit,
        "benchmark_tree_git_oid": tree,
        "lean_version": "4.29.1",
        "modes_supported": ["proof", "codeproof"],
        "artifacts": artifacts,
        "license_exceptions": {},
        "expected_counts": {
            "benchmarks": 1,
            "modules": 1,
            "apis": 1,
            "specs": 1,
            "trusted_axiom_benchmarks": 0,
            "trusted_axioms": 0,
            "source_languages": {"python": 1},
        },
    }


class VeroSourceAuditTest(unittest.TestCase):
    def test_audit_checks_pinned_source_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            pin = write_fixture(source)
            report = AUDIT.audit(source, pin)
        self.assertEqual(report["counts"]["benchmarks"], 1)
        self.assertEqual(report["checks"]["path_containment"], "pass")

    def test_manifest_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            pin = write_fixture(source)
            manifest_path = source / "benchmarks" / "Example" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["root_hub"] = "../escape.lean"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(AUDIT.AuditError):
                AUDIT.audit_manifest(manifest_path, pin)


class VeroRuntimeAuditTest(unittest.TestCase):
    def test_parse_lean_version(self) -> None:
        identity = RUNTIME.parse_lean_version(
            "Lean 4.29.1, arm64-apple-darwin24.6.0, commit f72c35b3f637, Release\n",
            "4.29.1",
        )
        self.assertEqual(identity["version"], "4.29.1")
        self.assertEqual(identity["commit"], "f72c35b3f637")

    def test_parse_pytest_output(self) -> None:
        summary = RUNTIME.parse_pytest_output("93 passed in 5.05s\n")
        self.assertEqual(summary["passed"], 93)

    def test_parse_pytest_output_rejects_skip(self) -> None:
        with self.assertRaises(RUNTIME.AuditError):
            RUNTIME.parse_pytest_output("93 passed, 1 skipped in 5.05s\n")


class VeroRepositorySplitTest(unittest.TestCase):
    def test_split_is_repository_disjoint_and_language_stratified(self) -> None:
        repositories = SPLIT["repositories"]
        identities = [record["benchmark_id"] for record in repositories]
        self.assertEqual(len(identities), 43)
        self.assertEqual(len(set(identities)), 43)
        self.assertEqual(SPLIT["selection_status"], "frozen_before_policy_measurement")
        self.assertEqual(
            {
                split: SPLIT["summary"][split]["repositories"]
                for split in ("development", "qualification", "prospective")
            },
            {"development": 23, "qualification": 10, "prospective": 10},
        )
        for split in ("development", "qualification", "prospective"):
            self.assertEqual(
                set(SPLIT["summary"][split]["source_languages"]),
                {"coq", "dafny", "python", "verus"},
            )

    def test_oracle_panel_uses_one_development_repository_per_language(self) -> None:
        by_id = {record["benchmark_id"]: record for record in SPLIT["repositories"]}
        oracles = ORACLES["repositories"]
        self.assertEqual(
            {record["source_language"] for record in oracles},
            {"coq", "dafny", "python", "verus"},
        )
        for record in oracles:
            self.assertEqual(by_id[record["benchmark_id"]]["split"], "development")
            language = record["source_language"]
            minimum = min(
                candidate["specifications"]
                for candidate in SPLIT["repositories"]
                if candidate["split"] == "development" and candidate["source_language"] == language
            )
            self.assertEqual(record["specifications"], minimum)

    def test_lifecycle_panel_preserves_exclusions_and_uses_development_only(self) -> None:
        by_id = {record["benchmark_id"]: record for record in SPLIT["repositories"]}
        selected = LIFECYCLE_PANEL["repositories"]
        self.assertEqual(
            {record["source_language"] for record in selected},
            {"coq", "dafny", "python", "verus"},
        )
        self.assertEqual(
            {record["benchmark_id"] for record in LIFECYCLE_PANEL["preserved_exclusions"]},
            {"unicode-v2", "verified_ironkv"},
        )
        for record in selected:
            self.assertEqual(by_id[record["benchmark_id"]]["split"], "development")


class VeroTaskLifecycleTest(unittest.TestCase):
    @staticmethod
    def noop_result(extras: int = 0) -> dict:
        return {
            "artifact_extras": extras,
            "build_ok": True,
            "summary": {
                "total_specs": 3,
                "passed_specs": 0,
                "unfilled_specs": 3,
                "failed_specs": 0,
                "overfilled_specs": 0,
            },
            "spec_statuses": {"unfilled": 3},
        }

    def test_validate_noop_separates_unfilled_from_failure(self) -> None:
        LIFECYCLE.validate_noop(self.noop_result(), expected_specs=3)

    def test_validate_noop_rejects_manifest_marker_drift(self) -> None:
        with self.assertRaises(LIFECYCLE.AuditError):
            LIFECYCLE.validate_noop(self.noop_result(extras=2), expected_specs=3)


class VeroPolicyProbeProtocolTest(unittest.TestCase):
    def test_frozen_probe_uses_only_the_development_panel(self) -> None:
        PROBE.validate(
            PROBE_PROTOCOL,
            LIFECYCLE_PANEL,
            SPLIT,
            panel_path=ADAPTER / "development-lifecycle-panel-v2.json",
            split_path=ADAPTER / "repository-split.json",
            containment_path=CONTAINMENT_PATH,
            runtime_lock_path=ADAPTER / "runtime" / "runtime-lock.v1.json",
            controller_lock_path=ADAPTER / "controller" / "controller-lock.v1.json",
            inference_contract_path=ADAPTER / "inference" / "inference-contract.v1.json",
            repetition_design_path=ADAPTER / "repetition-reliability.v1.json",
            measurement_analysis_path=ADAPTER / "measurement-analysis.v1.json",
        )

    def test_probe_remains_blocked_while_pre_run_gates_are_open(self) -> None:
        protocol = json.loads(PROBE_PROTOCOL_PATH.read_text(encoding="utf-8"))
        protocol["execution_authorized"] = True
        with self.assertRaises(PROBE.ProtocolError):
            PROBE.validate(
                protocol,
                LIFECYCLE_PANEL,
                SPLIT,
                panel_path=ADAPTER / "development-lifecycle-panel-v2.json",
                split_path=ADAPTER / "repository-split.json",
                containment_path=CONTAINMENT_PATH,
                runtime_lock_path=ADAPTER / "runtime" / "runtime-lock.v1.json",
                controller_lock_path=ADAPTER / "controller" / "controller-lock.v1.json",
                inference_contract_path=ADAPTER / "inference" / "inference-contract.v1.json",
                repetition_design_path=ADAPTER / "repetition-reliability.v1.json",
                measurement_analysis_path=ADAPTER / "measurement-analysis.v1.json",
            )

    def test_probe_rejects_controller_host_tool_execution(self) -> None:
        protocol = json.loads(PROBE_PROTOCOL_PATH.read_text(encoding="utf-8"))
        protocol["execution_interface"]["model_facing_tools_execute_on_controller_host"] = True
        with self.assertRaises(PROBE.ProtocolError):
            PROBE.validate(
                protocol,
                LIFECYCLE_PANEL,
                SPLIT,
                panel_path=ADAPTER / "development-lifecycle-panel-v2.json",
                split_path=ADAPTER / "repository-split.json",
                containment_path=CONTAINMENT_PATH,
                runtime_lock_path=ADAPTER / "runtime" / "runtime-lock.v1.json",
                controller_lock_path=ADAPTER / "controller" / "controller-lock.v1.json",
                inference_contract_path=ADAPTER / "inference" / "inference-contract.v1.json",
                repetition_design_path=ADAPTER / "repetition-reliability.v1.json",
                measurement_analysis_path=ADAPTER / "measurement-analysis.v1.json",
            )

    def test_probe_pins_the_frozen_containment_contract(self) -> None:
        interface = PROBE_PROTOCOL["execution_interface"]
        self.assertEqual(
            hashlib.sha256(CONTAINMENT_PATH.read_bytes()).hexdigest(),
            interface["containment_contract_sha256"],
        )


class VeroRepetitionDesignTest(unittest.TestCase):
    def test_frozen_design_selects_four_attempts(self) -> None:
        REPETITION.validate(REPETITION_DESIGN, LIFECYCLE_PANEL)
        self.assertEqual(REPETITION_DESIGN["selected_attempts_per_repository_mode"], 4)
        self.assertEqual(REPETITION_DESIGN["total_attempts"], 32)

    def test_design_rejects_a_different_selected_count(self) -> None:
        design = json.loads(REPETITION_DESIGN_PATH.read_text(encoding="utf-8"))
        design["selected_attempts_per_repository_mode"] = 3
        with self.assertRaises(REPETITION.RepetitionDesignError):
            REPETITION.validate(design, LIFECYCLE_PANEL)


class VeroProbeQueueTest(unittest.TestCase):
    def test_frozen_queue_matches_the_protocol_and_panel(self) -> None:
        expected = QUEUE.build_queue(
            PROBE_PROTOCOL,
            LIFECYCLE_PANEL,
            protocol_sha256=hashlib.sha256(PROBE_PROTOCOL_PATH.read_bytes()).hexdigest(),
            panel_sha256=hashlib.sha256(
                (ADAPTER / "development-lifecycle-panel-v2.json").read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(PROBE_QUEUE, expected)
        self.assertEqual(len(PROBE_QUEUE["attempts"]), 32)
        self.assertEqual(
            [record["queue_position"] for record in PROBE_QUEUE["attempts"]],
            list(range(1, 33)),
        )

    def test_queue_item_is_unique_and_contract_linked(self) -> None:
        selected = QUEUE_ITEM.select_entry(PROBE_QUEUE, PROBE_QUEUE["attempts"][0]["attempt_id"])
        self.assertEqual(selected["queue_position"], 1)
        QUEUE_ITEM.validate_queue_contract(
            PROBE_QUEUE,
            protocol_path=PROBE_PROTOCOL_PATH,
            panel_path=ADAPTER / "development-lifecycle-panel-v2.json",
        )

    def test_queue_item_rejects_protocol_drift(self) -> None:
        queue = json.loads(PROBE_QUEUE_PATH.read_text(encoding="utf-8"))
        queue["protocol_sha256"] = "0" * 64
        with self.assertRaises(QUEUE_ITEM.QueueItemError):
            QUEUE_ITEM.validate_queue_contract(
                queue,
                protocol_path=PROBE_PROTOCOL_PATH,
                panel_path=ADAPTER / "development-lifecycle-panel-v2.json",
            )

    def test_queue_worker_runs_every_stage_before_emitting_a_grade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = root / "protocol.json"
            panel = root / "panel.json"
            protocol.write_text("{}\n", encoding="utf-8")
            panel.write_text("{}\n", encoding="utf-8")
            queue = {
                "queue_id": "fixture",
                "status": "frozen_before_model_attempts",
                "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
                "panel_sha256": hashlib.sha256(panel.read_bytes()).hexdigest(),
                "attempts": [
                    {
                        "attempt_id": "repo-proof-r01",
                        "benchmark_id": "repo",
                        "mode": "proof",
                        "task_id": "repo:proof",
                        "queue_position": 1,
                    }
                ],
            }
            queue_path = root / "queue.json"
            queue_path.write_text(json.dumps(queue), encoding="utf-8")
            materializer = root / "materializer.py"
            materializer.write_text(
                """import argparse, json
p=argparse.ArgumentParser()
for x in ('source','pin','split','panel','benchmark-id','mode','output','receipt'):
 p.add_argument('--'+x, required=True)
a=p.parse_args()
from pathlib import Path
Path(a.output).mkdir()
Path(a.receipt).write_text(json.dumps({'ok': True}))
""",
                encoding="utf-8",
            )
            attempt_runner = root / "attempt.py"
            attempt_runner.write_text(
                """import argparse
from pathlib import Path
p=argparse.ArgumentParser()
fields=('attempt-id','task','materialization-receipt','output','work-root','vibe','image')
fields+=('docker','protocol','containment','runtime-lock','controller-lock')
fields+=('inference-contract','sandbox-server')
for x in fields:
 p.add_argument('--'+x, required=True)
a=p.parse_args(); Path(a.output).mkdir()
""",
                encoding="utf-8",
            )
            grader = root / "grader.py"
            grader.write_text(
                """import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
fields=('source','source-pin','panel','split','benchmark-id','mode','task')
fields+=('attempt-receipt','sandbox-receipt','vibe-export','output')
for x in fields:
 p.add_argument('--'+x, required=True)
a=p.parse_args(); Path(a.output).mkdir()
(Path(a.output)/'grade-receipt.json').write_text(json.dumps({'ok': True}))
""",
                encoding="utf-8",
            )
            no_op = root / "no-op.py"
            no_op.write_text("raise SystemExit(0)\n", encoding="utf-8")
            source = root / "source"
            work = root / "work"
            output = root / "output"
            source.mkdir()
            work.mkdir()
            output.mkdir()
            required_files = {}
            for name in (
                "source-pin",
                "split",
                "containment",
                "runtime-lock",
                "controller-lock",
                "inference-contract",
                "repetition-design",
                "measurement-analysis",
                "vibe",
                "sandbox-server",
            ):
                path = root / name
                path.write_text("{}\n", encoding="utf-8")
                required_files[name] = path
            command = [
                sys.executable,
                str(ADAPTER / "run_probe_queue_item.py"),
                "--queue",
                str(queue_path),
                "--attempt-id",
                "repo-proof-r01",
                "--source",
                str(source),
                "--panel",
                str(panel),
                "--protocol",
                str(protocol),
                "--work-root",
                str(work),
                "--output-root",
                str(output),
                "--image",
                "fixture@sha256:" + "a" * 64,
                "--docker",
                "docker",
                "--materializer",
                str(materializer),
                "--attempt-runner",
                str(attempt_runner),
                "--attempt-validator",
                str(no_op),
                "--grader",
                str(grader),
                "--protocol-validator",
                str(no_op),
                "--containment-validator",
                str(no_op),
                "--runtime-validator",
                str(no_op),
                "--controller-validator",
                str(no_op),
                "--inference-validator",
                str(no_op),
            ]
            for name, path in required_files.items():
                command.extend([f"--{name}", str(path)])
            subprocess.run(command, check=True, capture_output=True, text=True)
            receipt = json.loads(
                (output / "repo-proof-r01" / "queue-item-receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["status"], "graded")
            self.assertEqual(
                [stage["stage"] for stage in receipt["stages"]],
                [
                    "validate-protocol",
                    "validate-containment",
                    "validate-runtime",
                    "validate-controller",
                    "validate-inference",
                    "materialize",
                    "attempt",
                    "validate",
                    "grade",
                ],
            )


class VeroProbeAggregationTest(unittest.TestCase):
    def test_advantage_mass_matches_unnormalized_leave_one_out(self) -> None:
        self.assertEqual(AGGREGATE.advantage_mass(0, 4), 0.0)
        self.assertEqual(AGGREGATE.advantage_mass(1, 4), 2.0)
        self.assertEqual(AGGREGATE.advantage_mass(2, 4), 8 / 3)
        self.assertEqual(AGGREGATE.advantage_mass(4, 4), 0.0)

    def test_aggregate_keeps_repository_clusters_and_mode_coordinates(self) -> None:
        attempts = []
        receipts = {}
        reward_patterns = {
            "repo-a": ([1, 0, 0, 0], [0, 0, 0, 0]),
            "repo-b": ([1, 1, 0, 0], [1, 1, 1, 1]),
        }
        for repository, patterns in reward_patterns.items():
            for replicate in range(1, 5):
                attempt_id = f"{repository}-proof-r{replicate:02d}"
                attempts.append(
                    {
                        "attempt_id": attempt_id,
                        "benchmark_id": repository,
                        "mode": "proof",
                        "task_id": f"{repository}:proof",
                        "replicate": replicate,
                        "expected_specifications": 2,
                        "maximum_model_tokens": 50000,
                    }
                )
                rewards = [pattern[replicate - 1] for pattern in patterns]
                receipts[attempt_id] = {
                    "attempt_id": attempt_id,
                    "benchmark_id": repository,
                    "mode": "proof",
                    "task_id": f"{repository}:proof",
                    "infrastructure_valid": True,
                    "specifications_total": 2,
                    "model_tokens": 100,
                    "peak_memory_bytes": 1024,
                    "per_specification": [
                        {
                            "module": "M",
                            "specification": f"s{index}",
                            "strict_reward": reward,
                        }
                        for index, reward in enumerate(rewards)
                    ],
                }
        analysis = {
            "analysis_id": "fixture",
            "attempts_per_group": 4,
            "cluster_sensitivity": {
                "whole_repository_bootstrap_replicates": 20,
                "whole_repository_bootstrap_seed": 7,
                "central_interval": 0.90,
                "interpretation": "fixture",
            },
            "admission_summary": {
                "minimum_repositories_with_nonzero_verified_coverage": 2,
                "minimum_mixed_specification_groups": 2,
                "minimum_pooled_strict_success": 0.01,
                "maximum_pooled_strict_success": 0.80,
            },
        }
        result = AGGREGATE.aggregate(
            {"queue_id": "fixture", "attempts": attempts}, analysis, receipts
        )
        measurement = result["measurements_by_mode"]["proof"]["coordinates"]
        self.assertEqual(measurement["mixed_specification_groups"], 2)
        self.assertAlmostEqual(measurement["total_advantage_mass"], 14 / 3)
        self.assertEqual(
            set(
                result["measurements_by_mode"]["proof"]["cluster_sensitivity"][
                    "leave_one_repository_out"
                ]
            ),
            {"repo-a", "repo-b"},
        )
        self.assertTrue(result["admission_summary"]["passes_measurement_support_gate"])


class VeroContainmentContractTest(unittest.TestCase):
    def test_frozen_contract_is_complete_and_unqualified(self) -> None:
        CONTAINMENT.validate(CONTAINMENT_CONTRACT)
        self.assertFalse(CONTAINMENT_CONTRACT["qualified"])

    def test_contract_cannot_qualify_with_pending_tests(self) -> None:
        contract = json.loads(CONTAINMENT_PATH.read_text(encoding="utf-8"))
        contract["qualified"] = True
        contract["status"] = "qualified"
        with self.assertRaises(CONTAINMENT.ContractError):
            CONTAINMENT.validate(contract)


if __name__ == "__main__":
    unittest.main()
