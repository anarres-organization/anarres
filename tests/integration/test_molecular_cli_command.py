import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/ai-for-science/molecular-design/reaction-environment-selection"
SOURCE = STUDY / "src"
sys.path.insert(0, str(SOURCE))
SHARED_SOURCES = [
    ROOT / "packages/core/src",
    ROOT / "packages/environments/src",
]

from anarres_molecular_adapter import cli  # noqa: E402

BINARY = ROOT / "target/debug/anarres"


class MolecularCliTest(unittest.TestCase):
    def test_descriptor_is_schema_valid_sorted_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["name"], "molecular")
        self.assertEqual(descriptor["executable"], "anarres-molecular")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertEqual(descriptor["measurement_contracts"], ["rxnflow-q07820-bank-v4"])

    def test_status_reports_passed_confirmation_and_sealed_outcomes(self) -> None:
        result = cli.command_status(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["target_id"], "Q07820")
        self.assertEqual(result["bank_count"], 6)
        self.assertTrue(result["bank_confirmation_passed"])
        self.assertTrue(result["profiles_ready"])
        self.assertTrue(result["development_training_authorized"])
        self.assertFalse(result["training_outcomes_opened"])
        self.assertEqual(result["confirmation_rule"], "selector_fidelity")
        self.assertEqual(result["failed_confirmation_checks"], [])

    def test_profile_reuses_native_exporter_without_rho_or_h(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = cli.command_profile(
                type(
                    "Args",
                    (),
                    {"repository": ROOT, "output_dir": Path(directory), "force": False},
                )()
            )
            profiles = [json.loads(Path(path).read_text()) for path in result["outputs"]]
        self.assertEqual(result["profile_count"], 6)
        self.assertTrue(result["profiles_ready"])
        for profile in profiles:
            coordinates = {coordinate["name"] for coordinate in profile["coordinates"]}
            self.assertEqual(coordinates, set(cli.load_exporter(ROOT).COORDINATES))
            self.assertNotIn("usable_signal_density", coordinates)
            self.assertNotIn("effective_coverage", coordinates)
            checks = {check["check_id"]: check for check in profile["qualification_checks"]}
            self.assertEqual(checks["oracle-infrastructure-valid"]["status"], "pass")
            self.assertEqual(checks["bank-confirmation"]["status"], "pass")
            self.assertEqual(checks["training-outcomes-sealed"]["status"], "pass")
            self.assertNotEqual(
                profile["attributes"]["construction_view_seed"],
                profile["attributes"]["confirmation_view_seed"],
            )
            self.assertFalse(profile["attributes"]["training_outcomes_opened"])

    def test_verify_is_deterministic_and_authorizes_the_next_gate(self) -> None:
        arguments = type("Args", (), {"repository": ROOT})()
        first = cli.command_verify(arguments)
        second = cli.command_verify(arguments)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "pass")
        self.assertTrue(first["bank_confirmation_passed"])
        self.assertTrue(first["development_training_authorized"])


@unittest.skipUnless(os.name == "posix", "executable-wrapper test requires POSIX")
class MolecularCliCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            subprocess.run(
                ["cargo", "build", "--quiet", "-p", "anarres-cli"],
                cwd=ROOT,
                check=True,
            )

    def wrapper(self, directory: Path) -> Path:
        path = directory / "anarres-molecular"
        python_path = os.pathsep.join(str(item) for item in [SOURCE, *SHARED_SOURCES])
        path.write_text(
            "#!/bin/sh\n"
            f"export PYTHONPATH={shlex.quote(python_path)}\n"
            f'exec {shlex.quote(sys.executable)} -m anarres_molecular_adapter.cli "$@"\n',
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def run_cli(self, directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([str(directory), environment.get("PATH", "")])
        return subprocess.run(
            [str(BINARY), *arguments],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_doctor_and_status_work_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)
            doctor = self.run_cli(directory, "adapter", "doctor", "molecular", "--json")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(doctor.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["descriptor"]["name"], "molecular")

            status = self.run_cli(
                directory,
                "molecular",
                "status",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            result = json.loads(status.stdout)
            self.assertTrue(result["bank_confirmation_passed"])
            self.assertTrue(result["development_training_authorized"])


if __name__ == "__main__":
    unittest.main()
