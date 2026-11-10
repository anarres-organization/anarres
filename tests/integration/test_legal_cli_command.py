import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "target/debug/anarres"


@unittest.skipUnless(os.name == "posix", "executable-wrapper test requires POSIX")
class LegalCliCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            subprocess.run(
                ["cargo", "build", "--quiet", "-p", "anarres-cli"],
                cwd=ROOT,
                check=True,
            )

    def wrapper(self, directory: Path) -> Path:
        path = directory / "anarres-legal"
        path.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -m anarres.legal.cli "$@"\n',
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

    def test_doctor_and_direct_command_work_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)

            doctor = self.run_cli(directory, "adapter", "doctor", "legal", "--json")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(doctor.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["descriptor"]["name"], "legal")

            status = self.run_cli(
                directory,
                "legal",
                "status",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            result = json.loads(status.stdout)
            self.assertFalse(result["lab"]["profile_input"])
            self.assertFalse(result["syllogym"]["candidate_training_outcomes_used_by_adapter"])


if __name__ == "__main__":
    unittest.main()
