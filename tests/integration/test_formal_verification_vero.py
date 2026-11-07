from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
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
CONTAINMENT = load_module("vero_validate_containment", ADAPTER / "validate_containment_contract.py")
SPLIT = json.loads((ADAPTER / "repository-split.json").read_text(encoding="utf-8"))
ORACLES = json.loads((ADAPTER / "development-oracle-panel.json").read_text(encoding="utf-8"))
LIFECYCLE_PANEL = json.loads(
    (ADAPTER / "development-lifecycle-panel-v2.json").read_text(encoding="utf-8")
)
PROBE_PROTOCOL_PATH = ADAPTER / "policy-probe-protocol.v1.json"
PROBE_PROTOCOL = json.loads(PROBE_PROTOCOL_PATH.read_text(encoding="utf-8"))
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
            )

    def test_probe_pins_the_frozen_containment_contract(self) -> None:
        interface = PROBE_PROTOCOL["execution_interface"]
        self.assertEqual(
            hashlib.sha256(CONTAINMENT_PATH.read_bytes()).hexdigest(),
            interface["containment_contract_sha256"],
        )


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
