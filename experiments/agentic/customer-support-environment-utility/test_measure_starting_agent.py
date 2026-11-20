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


if __name__ == "__main__":
    unittest.main()
