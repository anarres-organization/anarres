import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "build_candidate_plan.py"
SPEC = importlib.util.spec_from_file_location("build_candidate_plan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def synthetic_measurement() -> dict:
    records = []
    for index in range(16):
        successes = index % 5
        mass = 2.0 * successes * (5 - successes) / 4.0
        output_tokens = 500 + 100 * index
        records.append(
            {
                "task_id": f"task-{index:02d}",
                "task_type": f"family-{index % 4}",
                "scored_attempts": 5,
                "successes": successes,
                "success_rate": successes / 5,
                "mixed_outcomes": 0 < successes < 5,
                "completion_advantage_mass": mass,
                "completion_signal_density_per_million_output_tokens": (
                    1_000_000.0 * mass / output_tokens
                ),
                "output_tokens": output_tokens,
                "tool_calls": 10,
                "cost_usd": 0.1,
            }
        )
    return {
        "measurement_id": "state_bench_customer_support_starting_agent_v1",
        "source_revision": "a" * 40,
        "domain": "customer_support",
        "split": "train",
        "requested_runs_per_task": 5,
        "expected_attempts": 80,
        "summary": {
            "starting_agent": {"model_name": "test-model", "reasoning_level": "high"},
            "task_count": 16,
            "scored_attempts": 80,
            "invalid_attempts": {},
            "per_task": records,
        },
    }


def synthetic_protocol() -> dict:
    return {
        "study_id": "customer_support_environment_utility_v1",
        "source": {"revision": "a" * 40, "training_trajectory_count": 16},
    }


class CandidatePlanTest(unittest.TestCase):
    def test_candidates_are_matched_and_deterministic(self):
        first = MODULE.build_plan(synthetic_measurement(), synthetic_protocol(), 8, 9)
        second = MODULE.build_plan(synthetic_measurement(), synthetic_protocol(), 8, 9)
        self.assertEqual(first, second)
        self.assertEqual(first["predicted_choice"], "policy_relative")
        self.assertFalse(first["held_out_outcomes_opened"])
        self.assertEqual(
            set(first["candidates"]),
            {
                "source_proportional",
                "deterministic_random",
                "static_difficulty",
                "policy_relative",
            },
        )
        for candidate in first["candidates"].values():
            self.assertEqual(candidate["count"], 8)
            self.assertEqual(len(candidate["task_ids"]), 8)
            self.assertEqual(len(candidate["membership_sha256"]), 64)

    def test_incomplete_measurement_is_rejected(self):
        measurement = synthetic_measurement()
        measurement["summary"]["invalid_attempts"] = {"missing_file": 1}
        with self.assertRaisesRegex(ValueError, "infrastructure-invalid"):
            MODULE.build_plan(measurement, synthetic_protocol(), 8, 9)


if __name__ == "__main__":
    unittest.main()
