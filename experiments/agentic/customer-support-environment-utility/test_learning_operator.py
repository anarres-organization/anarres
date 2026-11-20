import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
MODULE_PATH = ROOT / "execution/state_bench_extension/anarres_learning_operator.py"
SPEC = importlib.util.spec_from_file_location("anarres_learning_operator", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

RUNNER_PATH = ROOT / "scripts/run_model_smoke.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_model_smoke", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)


def write_trajectory(path: Path, request: str, tool_name: str, response: str) -> None:
    path.write_text(
        json.dumps(
            {
                "conversation": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": request},
                    {
                        "role": "assistant",
                        "content": response,
                        "tool_calls": [{"name": tool_name, "arguments": {}, "result": {}}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


class LearningOperatorTest(unittest.TestCase):
    def test_model_smoke_command_is_train_side_and_non_retrying(self):
        command = RUNNER.build_command(
            ["train-a", "train-b"],
            Path("/tmp/smoke"),
            "model",
            "high",
            2,
            "openai",
            "OPENAI_API_KEY",
        )
        self.assertIn("train-a,train-b", command)
        self.assertEqual(command[command.index("--num-runs") + 1], "2")
        self.assertEqual(command[command.index("--retry-attempts") + 1], "1")
        self.assertEqual(command[command.index("--agent-provider") + 1], "openai")
        self.assertEqual(command[command.index("--agent-api-key-var") + 1], "OPENAI_API_KEY")
        self.assertNotIn("--split", command)

    def test_model_smoke_requires_scores_and_token_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            run = output / "run1"
            run.mkdir()
            payload = {
                "task_id": "train-a",
                "state_requirements_met": 1,
                "task_requirements_met": 1,
                "task_completion_pass": 1,
                "ux_score": 4.5,
                "token_usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                    "total_cost_usd": 0.01,
                },
            }
            (run / "train-a.json").write_text(json.dumps(payload), encoding="utf-8")
            records, complete = RUNNER.inspect_outputs(output, ["train-a"], 1)
            self.assertTrue(complete)
            self.assertTrue(records[0]["scoring_complete"])
            payload["ux_score"] = None
            (run / "train-a.json").write_text(json.dumps(payload), encoding="utf-8")
            _, complete = RUNNER.inspect_outputs(output, ["train-a"], 1)
            self.assertFalse(complete)

    def test_artifact_is_deterministic_and_retrieval_is_relevant(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_trajectory(
                root / "return.json",
                "I need to return a blender",
                "process_return",
                "I can help with the return after checking eligibility.",
            )
            write_trajectory(
                root / "shipping.json",
                "My package has not arrived",
                "get_shipment",
                "I checked the shipment and can explain the delay.",
            )
            task_ids = ["return", "shipping"]
            membership = MODULE.membership_hash(task_ids)
            first = MODULE.build_artifact(
                root,
                task_ids,
                source_revision="a" * 40,
                candidate_plan_sha256="b" * 64,
                arm="policy_relative",
                expected_membership_sha256=membership,
            )
            second = MODULE.build_artifact(
                root,
                task_ids,
                source_revision="a" * 40,
                candidate_plan_sha256="b" * 64,
                arm="policy_relative",
                expected_membership_sha256=membership,
            )
        self.assertEqual(first, second)
        result = MODULE.retrieve(first, "blender return eligibility", top_k=1)
        self.assertIn("return a blender", result[0])

    def test_artifact_rejects_membership_and_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_trajectory(root / "task.json", "return this", "process_return", "done")
            with self.assertRaisesRegex(ValueError, "membership"):
                MODULE.build_artifact(
                    root,
                    ["task"],
                    source_revision="a" * 40,
                    candidate_plan_sha256="b" * 64,
                    arm="arm",
                    expected_membership_sha256="c" * 64,
                )
            artifact = MODULE.build_artifact(
                root,
                ["task"],
                source_revision="a" * 40,
                candidate_plan_sha256="b" * 64,
                arm="arm",
                expected_membership_sha256=MODULE.membership_hash(["task"]),
            )
            artifact["records"][0]["task_id"] = "changed"
            with self.assertRaisesRegex(ValueError, "membership hash"):
                MODULE.validate_artifact(artifact)


if __name__ == "__main__":
    unittest.main()
