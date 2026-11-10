import json
import tempfile
import unittest
from pathlib import Path

from anarres.finance import cli
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]


class FinanceCliTest(unittest.TestCase):
    def test_adapter_descriptor_is_stable_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "finance")
        self.assertEqual(descriptor["protocol_version"], 1)
        self.assertEqual(descriptor["executable"], "anarres-finance")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertEqual(
            descriptor["measurement_contracts"],
            ["finance.business-bench-starting-policy-qualification.v1"],
        )

    def test_status_reports_released_capabilities(self) -> None:
        result = cli.command_status(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["domain"], "agentic-finance")
        self.assertIn("retrospective_reproduction", result["capabilities"])
        self.assertFalse(result["prospective_environment_outcome_opened"])
        self.assertGreaterEqual(result["strict_retrospective_sources"], 1)

    def test_source_audit_uses_native_implementation(self) -> None:
        result = cli.command_audit_sources(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["generator_trials_passed"], 20)
        self.assertFalse(result["scientific_outcomes_opened"])

    def test_profile_command_exports_native_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "result": None,
                    "protocol": None,
                    "preflight": None,
                    "sources": None,
                    "harness": None,
                    "output_dir": Path(directory),
                    "force": False,
                },
            )()
            result = cli.command_profile(args)
            profile = json.loads(Path(result["output"]).read_text())
        self.assertEqual(result["status"], "exported")
        self.assertFalse(result["qualified"])
        self.assertEqual(profile["domain"], "agentic-finance")

    def test_frozen_holdout_can_be_rescored(self) -> None:
        args = type("Args", (), {"repository": ROOT, "name": "finharmbench"})()
        result = cli.command_score_holdout(args)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["holdout"], "heldout-finharmbench")
        self.assertEqual(
            result["score"]["accepted_models"],
            [
                "llama3_8b_instruct",
                "adaptllm_finance_chat_7b",
            ],
        )

    def test_zero_signal_record_preserves_cost_and_fails_readiness(self) -> None:
        rows = []
        for scenario in range(2):
            for rollout in range(4):
                rows.append(
                    {
                        "policy_id": "zero-signal-policy",
                        "workflow": "reconciliation",
                        "scenario_id": f"scenario-{scenario}",
                        "rollout_seed": rollout,
                        "infrastructure_valid": True,
                        "tool_protocol_valid": True,
                        "reward": 0,
                        "material_control_violation": False,
                        "generated_tokens": 500 + rollout,
                        "tool_calls": 2,
                        "truncated": False,
                    }
                )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attempts.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "input": path,
                    "expected_workflows": 1,
                    "expected_scenarios_per_workflow": 2,
                    "group_size": 4,
                    "output": None,
                    "force": False,
                },
            )()
            result = cli.command_qualify_policy(args)
        self.assertEqual(result["completion_rate"], 0.0)
        self.assertEqual(result["mixed_group_fraction"], 0.0)
        self.assertGreater(result["median_generated_tokens"], 0)
        self.assertFalse(result["qualified"])
        self.assertFalse(result["gates"]["completion_rate_between_0_02_and_0_80"])
        self.assertFalse(result["gates"]["mixed_group_fraction_at_least_0_10"])

    def test_reproduction_refuses_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {"status": "pass", "test_count": 1, "artifacts": {}}
            cli.write_json(output / "REPRODUCTION.json", report)
            with self.assertRaises(FileExistsError):
                cli.copy_reproduced_artifacts(output, output, report, force=False)


if __name__ == "__main__":
    unittest.main()
