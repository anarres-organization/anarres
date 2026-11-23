import contextlib
import io
import json
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from anarres.robotics import cli
from jsonschema import Draft202012Validator
from test_fixture_driver import FIXTURE

ROOT = Path(__file__).resolve().parents[3]
HANDSHAKE = ["--anarres-adapter-protocol", "2", "--anarres-adapter-name", "robotics"]


def run(arguments: list[str]) -> tuple[int, dict]:
    stdout = io.StringIO()
    code = 0
    with (
        mock.patch.object(sys, "argv", ["anarres-robotics", *arguments]),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        try:
            cli.main()
        except SystemExit as error:
            code = int(error.code)
    text = stdout.getvalue()
    return code, json.loads(text) if text.strip() else {}


class RoboticsCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.source = self.directory / "candidate-a"
        shutil.copytree(FIXTURE, self.source)
        self.manifest = self.source / "anarres.toml"
        self.output = self.directory / "probe"

    def tearDown(self) -> None:
        shutil.rmtree(self.directory)

    def probe(self, *extra: str) -> tuple[int, dict]:
        return run(
            [
                *HANDSHAKE,
                "probe-source",
                "--manifest",
                str(self.manifest),
                "--policy",
                "fixture-policy",
                "--policy-revision",
                "sha256:" + "a" * 64,
                "--output",
                str(self.output),
                "--json",
                *extra,
            ]
        )

    def test_descriptor_matches_schema_and_package(self) -> None:
        loaded = set(sys.modules)
        code, descriptor = run(["--anarres-adapter-descriptor"])
        self.assertEqual(code, 0)
        self.assertNotIn("anarres.robotics.drivers.fixture", set(sys.modules) - loaded)
        schema_path = ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json"
        Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(
            descriptor
        )
        pyproject = tomllib.loads((ROOT / "packages/robotics/pyproject.toml").read_text())
        self.assertEqual(descriptor["version"], pyproject["project"]["version"])
        self.assertIn("robotics-fixture-v1", descriptor["source_formats"])
        self.assertNotIn("policy-probe", descriptor["capabilities"])

    def test_qualify_source(self) -> None:
        code, result = run(
            [*HANDSHAKE, "qualify-source", "--manifest", str(self.manifest), "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["probe_tasks"], 3)
        self.assertFalse(result["candidate_outcomes_opened"])

    def test_wrong_adapter_version_is_rejected(self) -> None:
        text = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(text.replace('"0.6.0"', '"0.5.1"'), encoding="utf-8")
        code, _ = run(["qualify-source", "--manifest", str(self.manifest), "--json"])
        self.assertEqual(code, 1)

    def test_probe_plans_by_default(self) -> None:
        with mock.patch.object(cli.protocol.subprocess, "run") as launched:
            code, result = self.probe()
        launched.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "planned")
        self.assertFalse(result["runner_launched"])
        request = json.loads((self.output / "request.json").read_text(encoding="utf-8"))
        self.assertEqual(request["limits"], {"max_steps": 400, "wall_clock_seconds": 3600})

    def test_execute_requires_runner(self) -> None:
        code, _ = self.probe("--execute")
        self.assertEqual(code, 1)
        self.assertFalse(self.output.exists())

    def test_execute_launches_declared_runner(self) -> None:
        code, result = self.probe(
            "--execute",
            "--runner",
            sys.executable,
            "--runner-arg=-m",
            "--runner-arg=anarres.robotics.runners.fixture",
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["runner_launched"])
        self.assertEqual(result["infrastructure_statuses"], {"reset_failed": 2, "valid": 4})

    def test_runner_failure_exits_nonzero(self) -> None:
        code, result = self.probe(
            "--execute",
            "--runner",
            sys.executable,
            "--runner-arg=-c",
            "--runner-arg=raise SystemExit(3)",
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "runner_failed")


if __name__ == "__main__":
    unittest.main()
