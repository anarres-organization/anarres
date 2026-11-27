import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from anarres.robotics.contract import RoboticsContractError, validate_attempt
from anarres.robotics.drivers.base import load_driver
from anarres.robotics.runners import protocol
from jsonschema import Draft202012Validator
from test_fixture_driver import FIXTURE, load_fixture

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_RUNNER = [sys.executable, "-m", "anarres.robotics.runners.fixture"]
LIMITS = {"max_steps": 400, "wall_clock_seconds": 60}


def schema(name: str) -> Draft202012Validator:
    path = ROOT / "schemas" / "robotics" / name
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


class RunnerProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        root = self.directory / "source"
        shutil.copytree(FIXTURE, root)
        source = load_fixture(root)
        driver = load_driver("robotics-fixture-v1")
        self.request = protocol.build_request(
            source,
            driver.describe(source),
            driver,
            policy="fixture-policy",
            policy_revision="sha256:" + "a" * 64,
            limits=LIMITS,
        )
        self.output = self.directory / "probe"

    def tearDown(self) -> None:
        shutil.rmtree(self.directory)

    def test_request_matches_schema(self) -> None:
        schema("policy-runner-request.v1.schema.json").validate(self.request)

    def test_planning_launches_nothing(self) -> None:
        with mock.patch.object(protocol.subprocess, "run") as run:
            result = protocol.plan(self.request, self.output)
        run.assert_not_called()
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["attempts"], 6)
        self.assertFalse((self.output / "attempts.jsonl").exists())

    def test_plan_is_stable_and_immutable(self) -> None:
        first = protocol.plan(self.request, self.output)
        self.assertEqual(protocol.plan(self.request, self.output), first)
        changed = {**self.request, "limits": {**LIMITS, "max_steps": 10}}
        with self.assertRaisesRegex(RoboticsContractError, "immutable"):
            protocol.plan(changed, self.output)

    def test_execution_keeps_infrastructure_failures_separate(self) -> None:
        protocol.plan(self.request, self.output)
        result = protocol.execute(FIXTURE_RUNNER, self.output)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["infrastructure_statuses"], {"reset_failed": 2, "valid": 4})
        result_path = self.output / "runner-result.json"
        schema("policy-runner-result.v1.schema.json").validate(
            json.loads(result_path.read_text(encoding="utf-8"))
        )
        self.assertEqual(result["runner"]["name"], "anarres-robotics-fixture-runner")
        attempt_schema = schema("probe-attempt.v1.schema.json")
        for row in protocol.read_attempts(self.output / "attempts.jsonl"):
            attempt_schema.validate(row)
            if row["infrastructure_status"] != "valid":
                self.assertIsNone(row["success"])

    def test_partial_runner_output_is_incomplete(self) -> None:
        protocol.plan(self.request, self.output)
        protocol.execute(FIXTURE_RUNNER, self.output)
        attempts = self.output / "attempts.jsonl"
        attempts.write_text(
            "".join(attempts.read_text(encoding="utf-8").splitlines(True)[:-1]), encoding="utf-8"
        )
        with mock.patch.object(protocol.subprocess, "run") as run:
            run.return_value.returncode = 0
            result = protocol.execute(FIXTURE_RUNNER, self.output)
        self.assertEqual(result["status"], "incomplete")

    def test_runner_crash_is_reported_without_outcomes(self) -> None:
        protocol.plan(self.request, self.output)
        result = protocol.execute([sys.executable, "-c", "raise SystemExit(3)"], self.output)
        self.assertEqual(result["status"], "runner_failed")
        self.assertFalse((self.output / "attempts.jsonl").exists())

    def test_runner_exceeding_wall_clock_is_an_infrastructure_timeout(self) -> None:
        request = {**self.request, "limits": {**LIMITS, "wall_clock_seconds": 1}}
        protocol.plan(request, self.output)
        result = protocol.execute(
            [sys.executable, "-c", "import time; time.sleep(30)"], self.output
        )
        self.assertEqual(result["status"], "runner_failed")
        self.assertEqual(result["infrastructure_status"], "timeout")
        self.assertFalse((self.output / "attempts.jsonl").exists())

    def test_runner_result_without_identity_is_rejected(self) -> None:
        protocol.plan(self.request, self.output)
        protocol.execute(FIXTURE_RUNNER, self.output)
        result_path = self.output / "runner-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        del result["runner"]
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with mock.patch.object(protocol.subprocess, "run") as run:
            run.return_value.returncode = 0
            with self.assertRaisesRegex(RoboticsContractError, "identify the runner"):
                protocol.execute(FIXTURE_RUNNER, self.output)

    def test_failure_with_scientific_outcome_is_rejected(self) -> None:
        row = {
            "schema_version": "anarres.robotics-probe-attempt.v1",
            "infrastructure_status": "reset_failed",
            "success": False,
            "termination": "failure",
        }
        with self.assertRaisesRegex(RoboticsContractError, "infrastructure failure"):
            validate_attempt(row)


if __name__ == "__main__":
    unittest.main()
