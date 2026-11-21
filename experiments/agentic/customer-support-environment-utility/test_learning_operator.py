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

GATEWAY_MESSAGES_PATH = ROOT / "execution/state_bench_extension/anarres_gateway_messages.py"
GATEWAY_MESSAGES_SPEC = importlib.util.spec_from_file_location(
    "anarres_gateway_messages", GATEWAY_MESSAGES_PATH
)
GATEWAY_MESSAGES = importlib.util.module_from_spec(GATEWAY_MESSAGES_SPEC)
assert GATEWAY_MESSAGES_SPEC.loader is not None
GATEWAY_MESSAGES_SPEC.loader.exec_module(GATEWAY_MESSAGES)

RUNNER_PATH = ROOT / "scripts/run_model_smoke.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_model_smoke", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)

BUILDER_PATH = ROOT / "scripts/build_learning_artifact.py"
BUILDER_SPEC = importlib.util.spec_from_file_location("build_learning_artifact", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(BUILDER_SPEC)
assert BUILDER_SPEC.loader is not None
BUILDER_SPEC.loader.exec_module(BUILDER)


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
    def test_artifact_builder_rejects_non_training_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "state"
            split_dir = checkout / "state_bench/domains/customer_support/splits"
            split_dir.mkdir(parents=True)
            (split_dir / "train_test.json").write_text(
                json.dumps({"splits": {"train": ["train-task"], "test": ["held-out-task"]}}),
                encoding="utf-8",
            )
            protocol = json.loads((ROOT / "PROTOCOL.json").read_text(encoding="utf-8"))
            plan = {
                "study_id": protocol["study_id"],
                "status": "CANDIDATES_AND_PREDICTION_FROZEN__HELD_OUT_OUTCOMES_UNOPENED",
                "held_out_outcomes_opened": False,
                "candidate_size": 1,
                "inputs": {"protocol_sha256": BUILDER.sha256(ROOT / "PROTOCOL.json")},
                "run_contract": {"learning_operator": {"id": "state_bench_episodic_bm25_v1"}},
                "candidates": {
                    "policy_relative": {
                        "task_ids": ["held-out-task"],
                        "membership_sha256": MODULE.membership_hash(["held-out-task"]),
                    }
                },
            }
            plan_path = Path(directory) / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            original_audit = BUILDER.audit_checkout
            BUILDER.audit_checkout = lambda _: {"revision": "a" * 40}
            try:
                with self.assertRaisesRegex(ValueError, "non-training task"):
                    BUILDER.build(checkout, plan_path, "policy_relative")
            finally:
                BUILDER.audit_checkout = original_audit

    def test_model_smoke_command_is_train_side_and_non_retrying(self):
        command = RUNNER.build_command(
            ["train-a", "train-b"],
            Path("/tmp/smoke"),
            "model",
            "high",
            2,
            "openai",
            "OPENAI_API_KEY",
            2,
        )
        self.assertIn("train-a,train-b", command)
        self.assertEqual(command[command.index("--num-runs") + 1], "2")
        self.assertEqual(command[command.index("--retry-attempts") + 1], "1")
        self.assertEqual(command[command.index("--agent-provider") + 1], "openai")
        self.assertEqual(command[command.index("--agent-api-key-var") + 1], "OPENAI_API_KEY")
        self.assertNotIn("--split", command)
        displayed = RUNNER.build_command(
            ["train-a", "train-b"],
            Path("/tmp/smoke"),
            "model",
            "high",
            2,
            "openai",
            "<configured-credential-variable>",
            2,
        )
        self.assertNotIn("OPENAI_API_KEY", displayed)

    def test_gateway_smoke_uses_custom_client_and_locked_runner(self):
        command = RUNNER.build_command(
            ["train-a"],
            Path("/tmp/canary"),
            "gpt-model",
            "low",
            1,
            "gateway",
            "unused",
            1,
        )
        self.assertIn("scripts/anarres_gateway_run_batch.py", command)
        self.assertEqual(command[command.index("--num-runs") + 1], "1")
        self.assertEqual(command[command.index("--agent-class") + 1], "AnarresGatewayAgent")
        self.assertEqual(
            command[command.index("--agent-client-class") + 1],
            "AnarresChatCompletionsClient",
        )
        self.assertNotIn("--agent-provider", command)
        self.assertNotIn("--agent-api-key-var", command)

    def test_gateway_messages_place_every_result_after_its_tool_call(self):
        conversation = [
            {"role": "user", "content": "find both orders"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"name": "lookup", "arguments": {"id": 1}, "result": {"status": "open"}},
                    {"name": "lookup", "arguments": {"id": 2}, "result": {"status": "closed"}},
                ],
            },
            {"role": "tool", "content": [{"result": {}}, {"result": {}}]},
            {"role": "user", "content": "continue"},
        ]
        messages = GATEWAY_MESSAGES.build_messages("system", conversation)
        assistant_index = next(i for i, item in enumerate(messages) if item["role"] == "assistant")
        calls = messages[assistant_index]["tool_calls"]
        tool_messages = messages[assistant_index + 1 : assistant_index + 3]
        self.assertEqual([item["role"] for item in tool_messages], ["tool", "tool"])
        self.assertEqual(
            [item["tool_call_id"] for item in tool_messages],
            [call["id"] for call in calls],
        )
        self.assertEqual(messages[-1], {"role": "user", "content": "continue"})

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

    def test_failed_trajectory_retains_kind_and_request_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            run = output / "run2"
            run.mkdir()
            (run / "train-a.failure.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "FAILED_TRAJECTORY",
                        "failure_kind": "policy_execution_limit",
                        "task_id": "train-a",
                        "run_index": 2,
                        "attempts": 1,
                        "error": "BaseAgent exceeded max tool rounds (8)",
                    }
                ),
                encoding="utf-8",
            )
            usage = output / "REQUEST_USAGE.jsonl"
            usage.write_text(
                "\n".join(
                    json.dumps(
                        {
                            "run_index": 2,
                            "task_id": "train-a",
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "total_tokens": 120,
                            "response_cost_usd": 0.01,
                        }
                    )
                    for _ in range(2)
                )
                + "\n",
                encoding="utf-8",
            )
            records, complete = RUNNER.inspect_outputs(output, ["train-a"], 2)
            RUNNER.attribute_request_usage(records, usage)
            failed = next(record for record in records if record["run"] == 2)
            self.assertFalse(complete)
            self.assertEqual(failed["failure_kind"], "policy_execution_limit")
            self.assertEqual(failed["failure_attempts"], 1)
            self.assertEqual(failed["request_accounting"]["requests"], 2)
            self.assertEqual(failed["request_accounting"]["total_tokens"], 240)
            self.assertAlmostEqual(failed["request_accounting"]["response_cost_usd"], 0.02)

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
