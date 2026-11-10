import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "target/debug/anarres"


@unittest.skipUnless(os.name == "posix", "executable-wrapper test requires POSIX")
class FinanceCliCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            cargo = shutil.which("cargo")
            if cargo is None:
                self.skipTest("cargo is required to build the Anarres CLI")
            subprocess.run(
                [cargo, "build", "--quiet", "-p", "anarres-cli"],
                cwd=ROOT,
                check=True,
            )

    def wrapper(self, directory: Path) -> Path:
        path = directory / "anarres-finance"
        path.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -m anarres.finance.cli "$@"\n',
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def environment(self, directory: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([str(directory), environment.get("PATH", "")])
        source_paths = [
            ROOT / "packages/finance/src",
            ROOT / "packages/environments/src",
            ROOT / "packages/core/src",
        ]
        environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_paths)
        return environment

    def run_generic(self, directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(BINARY), *arguments],
            cwd=directory,
            env=self.environment(directory),
            capture_output=True,
            text=True,
            check=False,
        )

    def run_direct(self, directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(directory / "anarres-finance"), *arguments],
            cwd=directory,
            env=self.environment(directory),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_doctor_and_commands_work_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)

            doctor = self.run_generic(directory, "adapter", "doctor", "finance", "--json")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(doctor.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["descriptor"]["name"], "finance")
            self.assertEqual(
                report["descriptor"]["measurement_contracts"],
                ["finance.business-bench-starting-policy-qualification.v1"],
            )

            generic = self.run_generic(
                directory,
                "finance",
                "status",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(generic.returncode, 0, generic.stderr)
            generic_status = json.loads(generic.stdout)
            self.assertFalse(generic_status["prospective_environment_outcome_opened"])

            direct = self.run_direct(
                directory,
                "status",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(direct.returncode, 0, direct.stderr)
            self.assertEqual(json.loads(direct.stdout), generic_status)

            audit = self.run_generic(
                directory,
                "finance",
                "audit-sources",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertFalse(json.loads(audit.stdout)["scientific_outcomes_opened"])

            verify = self.run_generic(
                directory,
                "finance",
                "verify",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(verify.returncode, 0, verify.stderr)
            verify_result = json.loads(verify.stdout)
            self.assertEqual(verify_result["mode"], "compact")
            self.assertEqual(len(verify_result["holdouts"]), 5)

            profile_dir = directory / "profile"
            profile = self.run_generic(
                directory,
                "finance",
                "profile",
                "--repository",
                str(ROOT),
                "--output-dir",
                str(profile_dir),
                "--json",
            )
            self.assertEqual(profile.returncode, 0, profile.stderr)
            profile_result = json.loads(profile.stdout)
            self.assertFalse(profile_result["qualified"])
            self.assertTrue(Path(profile_result["output"]).is_file())

    def test_invalid_evidence_path_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)
            completed = self.run_generic(
                directory,
                "finance",
                "status",
                "--repository",
                str(directory / "missing"),
                "--json",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Anarres repository not found", completed.stderr)


if __name__ == "__main__":
    unittest.main()
