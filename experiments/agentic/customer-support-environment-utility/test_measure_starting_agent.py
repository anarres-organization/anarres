import importlib.util
import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "measure_starting_agent.py"
SPEC = importlib.util.spec_from_file_location("measure_starting_agent", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def attempt(success, output_tokens, tool_calls, cost_usd):
    return {
        "success": success,
        "input_tokens": 2 * output_tokens,
        "output_tokens": output_tokens,
        "tool_calls": tool_calls,
        "tool_errors": 0,
        "redundant_calls": 0,
        "cost_usd": cost_usd,
        "state_requirements_met": success,
        "task_requirements_met": success,
        "ux_score": 4.0,
        "agent_model": {"model_name": "test-model", "reasoning_level": "high"},
        "development_judge_contract": None,
    }


class StartingAgentMeasurementTest(unittest.TestCase):
    def test_native_nested_accounting_fields_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task-a.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "task_completion_pass": 1,
                        "efficiency": {
                            "tool_calls": 4,
                            "tool_errors": 1,
                            "redundant_calls": 2,
                        },
                        "token_usage": {
                            "input_tokens": 240,
                            "output_tokens": 120,
                            "total_cost_usd": 0.03,
                        },
                        "state_requirements_met": 1,
                        "task_requirements_met": 0,
                        "ux_score": 3.5,
                        "agent_model": {
                            "model_name": "test-model",
                            "reasoning_level": "high",
                        },
                    }
                ),
                encoding="utf-8",
            )
            attempt, invalid = MODULE.read_scored_attempt(path, "task-a")
        self.assertIsNone(invalid)
        self.assertEqual(
            attempt,
            {
                "success": 1,
                "input_tokens": 240.0,
                "output_tokens": 120.0,
                "tool_calls": 4.0,
                "tool_errors": 1.0,
                "redundant_calls": 2.0,
                "cost_usd": 0.03,
                "state_requirements_met": 1,
                "task_requirements_met": 0,
                "ux_score": 3.5,
                "agent_model": {"model_name": "test-model", "reasoning_level": "high"},
                "development_judge_contract": None,
            },
        )

    def test_scientific_failure_is_separate_from_invalid_attempt(self):
        task_ids = ["task-a", "task-b"]
        task_types = {"task-a": "return", "task-b": "shipping"}
        attempts = {
            "task-a": [
                attempt(1, 100, 2, 0.1),
                attempt(0, 100, 3, 0.2),
            ],
            "task-b": [
                attempt(0, 100, 1, 0.1),
                attempt(0, 100, 1, 0.1),
            ],
        }
        invalid = defaultdict(int, {"missing_file": 1})
        summary = MODULE.summarize_attempts(task_ids, task_types, attempts, invalid)
        self.assertEqual(summary["scored_attempts"], 4)
        self.assertEqual(summary["scientific_failures"], 3)
        self.assertEqual(summary["invalid_attempts"], {"missing_file": 1})
        self.assertEqual(summary["mixed_task_count"], 1)
        self.assertAlmostEqual(summary["completion_advantage_mass"], 2.0)
        self.assertAlmostEqual(
            summary["completion_signal_density_per_million_output_tokens"], 5000.0
        )
        self.assertAlmostEqual(summary["completion_signal_effective_task_coverage"], 0.5)

    def test_missing_cost_makes_cost_aggregate_null(self):
        attempts = {
            "task-a": [
                attempt(1, 10, 1, None),
                attempt(0, 10, 1, 0.1),
            ]
        }
        summary = MODULE.summarize_attempts(
            ["task-a"], {"task-a": "return"}, attempts, defaultdict(int)
        )
        self.assertFalse(summary["trajectory_cost_accounting_complete"])
        self.assertIsNone(summary["total_cost_usd"])

    def test_development_sidecar_is_bound_to_trajectory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trajectory = root / "task-a.json"
            trajectory.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "efficiency": {
                            "tool_calls": 1,
                            "tool_errors": 0,
                            "redundant_calls": 0,
                        },
                        "token_usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "total_cost_usd": 0.01,
                        },
                        "agent_model": {
                            "model_name": "test-model",
                            "reasoning_level": None,
                        },
                    }
                ),
                encoding="utf-8",
            )
            sidecar = root / "score.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "status": "DEVELOPMENT_SCORE_COMPLETE",
                        "official_state_bench_compatible": False,
                        "task_id": "task-a",
                        "run_index": 1,
                        "trajectory": {"sha256": MODULE.sha256(trajectory)},
                        "judge_contract": {"contract_sha256": "a" * 64},
                        "scores": {
                            "state_requirements_met": 1,
                            "task_requirements_met": 0,
                            "task_completion_pass": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            measured, invalid = MODULE.read_scored_attempt(
                trajectory,
                "task-a",
                run_index=1,
                development_score_path=sidecar,
            )
            self.assertIsNone(invalid)
            self.assertEqual(measured["success"], 0)
            self.assertEqual(measured["state_requirements_met"], 1)
            self.assertEqual(measured["task_requirements_met"], 0)
            trajectory.write_text(trajectory.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "trajectory hash"):
                MODULE.read_scored_attempt(
                    trajectory,
                    "task-a",
                    run_index=1,
                    development_score_path=sidecar,
                )

    def test_development_measurement_requires_an_accepted_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            decision = Path(directory) / "decision.json"
            record = {
                "status": "ACCEPTED_FOR_TRAIN_SIDE_DEVELOPMENT",
                "official_state_bench_compatible": False,
                "reviewed_all_disagreements": True,
                "judge_contract_sha256": "a" * 64,
            }
            decision.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(MODULE.load_development_judge_decision(decision), record)
            record["status"] = "DEVELOPMENT_JUDGE_ABSTAIN"
            decision.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "was not accepted"):
                MODULE.load_development_judge_decision(decision)


if __name__ == "__main__":
    unittest.main()
