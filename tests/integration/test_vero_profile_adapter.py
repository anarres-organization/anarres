import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "target/debug/anarres"
SCRIPT = ROOT / "data/formal-verification/vero/export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("vero_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FORMAL_SRC = ROOT / "data/formal-verification/vero/src"
sys.path.insert(0, str(FORMAL_SRC))
CLI_PATH = FORMAL_SRC / "anarres_formal_adapter/cli.py"
CLI_SPEC = importlib.util.spec_from_file_location("anarres_formal_cli", CLI_PATH)
assert CLI_SPEC is not None and CLI_SPEC.loader is not None
CLI = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(CLI)


class VeroProfileAdapterTest(unittest.TestCase):
    def test_adapter_descriptor_matches_the_shared_contract(self) -> None:
        descriptor = CLI.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["name"], "formal")
        self.assertEqual(descriptor["executable"], "anarres-formal")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertIn("qualification-report", descriptor["capabilities"])
        self.assertIn("source-qualification", descriptor["capabilities"])
        self.assertNotIn("policy-probe", descriptor["capabilities"])
        self.assertEqual(descriptor["source_formats"], ["vero-checkout-v1"])
        self.assertEqual(
            descriptor["measurement_contracts"],
            [
                "vero-leanstral-development-probe-v5:codeproof",
                "vero-leanstral-development-probe-v5:proof",
            ],
        )

    def test_installed_source_pin_matches_the_released_record(self) -> None:
        bundled = CLI.source_qualification.load_source_pin()
        released = json.loads(
            (ROOT / "data/formal-verification/vero/source-pin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(bundled, released)

    @staticmethod
    def write_source_manifest(root: Path, source: Path) -> Path:
        manifest = root / "anarres.toml"
        manifest.write_text(
            "\n".join(
                [
                    'schema_version = "anarres.environment-source.v1"',
                    'environment_id = "vero-public-v1"',
                    'domain = "formal-verification"',
                    'adapter = "formal"',
                    'adapter_version = "0.2.0"',
                    'native_format = "vero-checkout-v1"',
                    "",
                    "[source]",
                    f'uri = "{source}"',
                    'revision = "git:0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09"',
                    'license = "Apache-2.0 with benchmark-specific upstream licenses"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def test_direct_source_qualification_preserves_execution_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "vero"
            source.mkdir()
            manifest = self.write_source_manifest(root, source)
            audit = {
                "source_id": "sunblaze-ucb/vero@" + "0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09",
                "git_revision": "0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09",
                "benchmark_tree_git_oid": "21f18407dc780b2500f4a81be93261c8b4426bfb",
                "source_pin_sha256": "f" * 64,
                "counts": {
                    "benchmarks": 43,
                    "modules": 237,
                    "apis": 743,
                    "specs": 2705,
                    "source_languages": {"coq": 4, "dafny": 5, "python": 30, "verus": 4},
                },
                "verified_artifacts": 5,
                "lean_version": "4.29.1",
                "modes": ["proof", "codeproof"],
            }
            with mock.patch.object(CLI.source_qualification, "qualify", return_value=audit):
                report = CLI.command_qualify_source(
                    argparse.Namespace(manifest=manifest, json=True)
                )
            self.assertEqual(report["status"], "qualified")
            self.assertEqual(report["qualification_state"], "source_qualified_runtime_pending")
            self.assertFalse(report["runtime_qualified"])
            self.assertFalse(report["policy_probe_available"])
            self.assertFalse(report["model_execution_started"])
            self.assertFalse(report["qualification_or_prospective_tasks_opened"])

    def test_source_qualification_rejects_unpinned_manifest_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "vero"
            source.mkdir()
            manifest = self.write_source_manifest(root, source)
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "git:0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09",
                    "git:" + "1" * 40,
                ),
                encoding="utf-8",
            )
            completed = self.run_adapter(
                ["qualify-source", "--manifest", str(manifest), "--json"], root
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("released Vero commit", completed.stderr)

    def run_adapter(self, arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        source_paths = [
            ROOT / "data/formal-verification/vero/src",
            ROOT / "packages/core/src",
            ROOT / "packages/environments/src",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_paths)
        return subprocess.run(
            [sys.executable, "-m", "anarres_formal_adapter.cli", *arguments],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_adapter_runs_outside_checkout_and_preserves_negative_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory)
            descriptor = self.run_adapter(["--anarres-adapter-descriptor"], outside)
            self.assertEqual(descriptor.returncode, 0, descriptor.stderr)
            self.assertEqual(json.loads(descriptor.stdout)["name"], "formal")

            status = self.run_adapter(["status", "--repository", str(ROOT), "--json"], outside)
            self.assertEqual(status.returncode, 0, status.stderr)
            report = json.loads(status.stdout)
            self.assertEqual(report["strict_successes"], 0)
            self.assertFalse(report["support_gate_passed"])
            self.assertFalse(report["profile_ready"])
            self.assertFalse(report["downstream_training_authorized"])
            self.assertTrue(report["qualification_report_available"])
            self.assertEqual(report["native_source_format"], "vero-checkout-v1")
            self.assertTrue(report["native_source_qualification_available"])
            self.assertFalse(report["policy_probe_available"])
            self.assertEqual(report["infrastructure_valid_attempts"], 32)
            self.assertEqual(report["infrastructure_errors"], 0)
            for measured in report["mode_measurements"].values():
                self.assertEqual(measured["usable_signal_density"], 0.0)
                self.assertEqual(measured["effective_verification_coverage"], 0.0)
                self.assertGreater(measured["model_tokens"], 0)

            profiles = outside / "profiles"
            exported = self.run_adapter(
                [
                    "profile",
                    "--repository",
                    str(ROOT),
                    "--output-dir",
                    str(profiles),
                    "--json",
                ],
                outside,
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            export_report = json.loads(exported.stdout)
            self.assertEqual(export_report["profile_count"], 2)
            self.assertFalse(export_report["profiles_ready"])
            self.assertEqual(
                sorted(path.name for path in profiles.glob("*.profile-input.json")),
                [
                    "vero-development-codeproof-v5.profile-input.json",
                    "vero-development-proof-v5.profile-input.json",
                ],
            )

            verified = self.run_adapter(["verify", "--repository", str(ROOT), "--json"], outside)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            verification = json.loads(verified.stdout)
            self.assertEqual(verification["status"], "pass")
            self.assertFalse(verification["profiles_ready"])
            self.assertTrue(verification["qualification_support_passed"])
            self.assertFalse(verification["repeated_measurement_authorized"])

            qualification = self.run_adapter(
                ["qualification", "--repository", str(ROOT), "--json"], outside
            )
            self.assertEqual(qualification.returncode, 0, qualification.stderr)
            qualification_report = json.loads(qualification.stdout)
            self.assertEqual(qualification_report["status"], "released_reproduced")
            self.assertFalse(qualification_report["profile_input"])
            self.assertEqual(qualification_report["strict_support"]["passed_specifications"], 9)
            self.assertTrue(qualification_report["strict_support"]["support_threshold_passed"])
            self.assertFalse(qualification_report["containment"]["task_only_boundary_passed"])
            self.assertFalse(qualification_report["decision"]["repeated_measurement_authorized"])
            self.assertFalse(qualification_report["decision"]["candidate_ranking_authorized"])
            self.assertFalse(qualification_report["decision"]["downstream_training_authorized"])
            self.assertEqual(
                set(qualification_report["artifacts"]),
                {"execution", "infrastructure_retry", "protocol", "result"},
            )

    def export(self, output: Path) -> list[Path]:
        return MODULE.export_profiles(
            result_path=MODULE.DEFAULT_RESULT,
            protocol_path=MODULE.DEFAULT_PROTOCOL,
            source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
            output_dir=output,
        )

    def test_released_negative_measurement_exports_two_unready_profiles(self) -> None:
        schema_paths = sorted((ROOT / "schemas").rglob("*.schema.json"))
        schemas = [json.loads(path.read_text()) for path in schema_paths]
        registry = Registry()
        for item in schemas:
            if isinstance(item.get("$id"), str):
                registry = registry.with_resource(item["$id"], Resource.from_contents(item))
        schema = next(
            item
            for item in schemas
            if item.get("$id", "").endswith("environment-profile-input.v1.schema.json")
        )
        with tempfile.TemporaryDirectory() as directory:
            outputs = self.export(Path(directory))
            self.assertEqual(len(outputs), 2)
            profiles = [json.loads(path.read_text()) for path in outputs]
            self.assertEqual(
                {profile["attributes"]["mode"] for profile in profiles}, {"proof", "codeproof"}
            )
            for profile in profiles:
                Draft202012Validator(schema, registry=registry).validate(profile)
                checks = {check["check_id"]: check for check in profile["qualification_checks"]}
                self.assertEqual(checks["infrastructure-valid"]["status"], "pass")
                self.assertEqual(checks["preregistered-support"]["status"], "fail")
                values = {item["name"]: item["value"] for item in profile["coordinates"]}
                self.assertEqual(values["usable_signal_density"], 0.0)
                self.assertEqual(values["effective_verification_coverage"], 0.0)
                self.assertGreater(values["mean_model_tokens_per_attempt"], 0.0)
                self.assertEqual(len(profile["artifacts"]), 3)
                artifact_digests = {
                    artifact["role"]: artifact["reference"]["sha256"]
                    for artifact in profile["artifacts"]
                }
                self.assertEqual(
                    artifact_digests,
                    {
                        "measurement-contract": (
                            "sha256:ea3f696bb3b60da0d217d303d80bd5447be919014b8850fb9bd83a7441f99bf0"
                        ),
                        "native-measurements": (
                            "sha256:8c93cf6b1c345906bfcb83d3af6850f5b8717d303ed9bd33065efb60444ea3cb"
                        ),
                        "source-pin": (
                            "sha256:670361cdebb1d9d77d1dcd51b4e754734c8d4357dbb1291700ef97f9dca8850e"
                        ),
                    },
                )

    def test_export_is_byte_stable_for_released_evidence(self) -> None:
        expected = {
            "vero-development-codeproof-v5.profile-input.json": (
                "2df8fe89418f98ee6a4de4fa266dbea16c980143fd1cf89fe7b92c64cb85c4c1"
            ),
            "vero-development-proof-v5.profile-input.json": (
                "cbf4283bd32c754a45e3b50e8a6b323623ff54eb94555f40ace8d6d26da4de10"
            ),
        }
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_outputs = self.export(Path(first))
            second_outputs = self.export(Path(second))
            self.assertEqual(
                {path.name: path.read_bytes() for path in first_outputs},
                {path.name: path.read_bytes() for path in second_outputs},
            )
            self.assertEqual(
                {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in first_outputs
                },
                expected,
            )

    def test_frozen_protocol_digest_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            protocol = json.loads(MODULE.DEFAULT_PROTOCOL.read_text())
            protocol["starting_policy"]["temperature"] = 0.5
            modified = temporary / "protocol.json"
            modified.write_text(json.dumps(protocol))
            with self.assertRaisesRegex(MODULE.AdapterError, "does not match"):
                MODULE.export_profiles(
                    result_path=MODULE.DEFAULT_RESULT,
                    protocol_path=modified,
                    source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
                    output_dir=temporary / "profiles",
                )

    def test_missing_source_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = json.loads(MODULE.DEFAULT_SOURCE_PIN.read_text())
            source["commit"] = ""
            modified = temporary / "source-pin.json"
            modified.write_text(json.dumps(source))
            with self.assertRaisesRegex(MODULE.AdapterError, "nonempty commit"):
                MODULE.export_profiles(
                    result_path=MODULE.DEFAULT_RESULT,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    source_pin_path=modified,
                    output_dir=temporary / "profiles",
                )

    def test_infrastructure_failure_is_not_exported_as_reward_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = json.loads(MODULE.DEFAULT_RESULT.read_text())
            result["execution"]["infrastructure_valid_attempts"] = 31
            result["execution"]["infrastructure_errors"] = 1
            modified = temporary / "result.json"
            modified.write_text(json.dumps(result))
            with self.assertRaisesRegex(MODULE.AdapterError, "infrastructure-valid"):
                MODULE.export_profiles(
                    result_path=modified,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
                    output_dir=temporary / "profiles",
                )

    def test_missing_native_measurement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = json.loads(MODULE.DEFAULT_RESULT.read_text())
            del result["measurement"]["by_mode"]["proof"]["effective_coverage_H"]
            modified = temporary / "result.json"
            modified.write_text(json.dumps(result))
            with self.assertRaisesRegex(MODULE.AdapterError, "nonfinite coordinate"):
                MODULE.export_profiles(
                    result_path=modified,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
                    output_dir=temporary / "profiles",
                )

    def test_existing_profile_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.export(output)
            with self.assertRaises(FileExistsError):
                self.export(output)


@unittest.skipUnless(os.name == "posix", "executable-wrapper test requires POSIX")
class FormalCliCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            subprocess.run(
                ["cargo", "build", "--quiet", "-p", "anarres-cli"],
                cwd=ROOT,
                check=True,
            )

    def test_doctor_and_direct_command_work_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            wrapper = directory / "anarres-formal"
            wrapper.write_text(
                f"#!/bin/sh\nexec {shlex.quote(sys.executable)} "
                '-m anarres_formal_adapter.cli "$@"\n',
                encoding="utf-8",
            )
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join([str(directory), environment.get("PATH", "")])
            environment["PYTHONPATH"] = os.pathsep.join(
                [
                    str(ROOT / "data/formal-verification/vero/src"),
                    str(ROOT / "packages/core/src"),
                    str(ROOT / "packages/environments/src"),
                ]
            )

            doctor = subprocess.run(
                [str(BINARY), "adapter", "doctor", "formal", "--json"],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertTrue(json.loads(doctor.stdout)["valid"])

            status = subprocess.run(
                [
                    str(BINARY),
                    "formal",
                    "status",
                    "--repository",
                    str(ROOT),
                    "--json",
                ],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            report = json.loads(status.stdout)
            self.assertFalse(report["support_gate_passed"])
            self.assertFalse(report["candidate_ranking_authorized"])

            qualification = subprocess.run(
                [
                    str(BINARY),
                    "formal",
                    "qualification",
                    "--repository",
                    str(ROOT),
                    "--json",
                ],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(qualification.returncode, 0, qualification.stderr)
            report = json.loads(qualification.stdout)
            self.assertFalse(report["profile_input"])
            self.assertEqual(report["strict_support"]["passed_specifications"], 9)


if __name__ == "__main__":
    unittest.main()
