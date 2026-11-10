import json
import tempfile
import unittest
from pathlib import Path

from anarres.finance import cli

ROOT = Path(__file__).resolve().parents[3]


class FinanceCliTest(unittest.TestCase):
    def test_adapter_descriptor_is_stable_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "finance")
        self.assertEqual(descriptor["protocol_version"], 1)
        self.assertEqual(descriptor["executable"], "anarres-finance")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))

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

    def test_reproduction_refuses_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {"status": "pass", "test_count": 1, "artifacts": {}}
            cli.write_json(output / "REPRODUCTION.json", report)
            with self.assertRaises(FileExistsError):
                cli.copy_reproduced_artifacts(output, output, report, force=False)


if __name__ == "__main__":
    unittest.main()
