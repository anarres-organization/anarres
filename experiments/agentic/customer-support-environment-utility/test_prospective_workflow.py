import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


FREEZE = load_script("freeze_candidate_plan")
GATE = load_script("gate_candidate_results")
SCORE = load_script("score_candidate_results")
PREPARE = load_script("prepare_arm_manifest")


def run_contract():
    return {
        "study_id": "study",
        "status": "READY_TO_FREEZE",
        "starting_agent": {
            "model_name": "model",
            "model_revision": "revision",
            "agent_class": "Agent",
            "client_class": "Client",
            "reasoning_level": None,
        },
        "learning_operator": {
            "id": "operator",
            "revision": "revision",
            "artifact_builder": "builder.py",
            "retrieval_top_k": 3,
        },
        "candidate_size": 2,
        "development_runs_per_task": 2,
        "held_out_runs_per_task": 5,
        "infrastructure": {
            "retry_attempts": 3,
            "attempt_ledger": "attempts.jsonl",
            "failed_attempt_cost_accounting": "all attempts charged",
        },
        "evaluation": {
            "protocol": "state_bench_gpt54",
            "split": "test",
            "split_version": "train_test",
            "task_count": 50,
        },
    }


class ProspectiveWorkflowTest(unittest.TestCase):
    def test_gate_rehashes_artifacts_and_records_the_scoring_boundary(self):
        candidates = [
            "source_proportional",
            "deterministic_random",
            "static_difficulty",
            "policy_relative",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / "state"
            split_dir = checkout / "state_bench/domains/customer_support/splits"
            split_dir.mkdir(parents=True)
            (split_dir / "train_test.json").write_text(
                json.dumps({"splits": {"train": [], "test": ["task"]}}), encoding="utf-8"
            )
            plan = {
                "study_id": "study",
                "status": "CANDIDATES_AND_PREDICTION_FROZEN__HELD_OUT_OUTCOMES_UNOPENED",
                "held_out_outcomes_opened": False,
                "predicted_choice": "policy_relative",
                "candidates": {
                    name: {"membership_sha256": str(index) * 64}
                    for index, name in enumerate(candidates, start=1)
                },
                "freeze_inputs": {"run_contract_sha256": "f" * 64},
                "run_contract": run_contract(),
            }
            plan_path = root / "plan.json"
            protocol_path = root / "protocol.json"
            scoring_path = root / "scoring.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            protocol_path.write_text(
                json.dumps(
                    {
                        "study_id": "study",
                        "source": {"held_out_task_count": 1},
                    }
                ),
                encoding="utf-8",
            )
            scoring_path.write_text(
                json.dumps(
                    {
                        "study_id": "study",
                        "status": "SCORING_CONTRACT_FROZEN__HELD_OUT_OUTCOMES_UNOPENED",
                        "held_out_outcomes_opened": False,
                        "predicted_choice": "policy_relative",
                        "baseline_arm": "no_learning",
                        "candidate_arms": candidates,
                        "runs_per_task": 1,
                    }
                ),
                encoding="utf-8",
            )
            arms = {}
            for arm in ["no_learning", *candidates]:
                arm_root = root / arm
                run_dir = arm_root / "run1"
                run_dir.mkdir(parents=True)
                artifact = None
                relative_path = None
                if arm != "no_learning":
                    artifact = arm_root / "learning.json"
                    artifact.write_text(json.dumps({"arm": arm}), encoding="utf-8")
                    relative_path = "learning.json"
                manifest = PREPARE.prepare(
                    plan,
                    GATE.sha256(plan_path),
                    arm,
                    artifact,
                    relative_path,
                    0.01 if artifact else None,
                    1.0 if artifact else None,
                )
                (arm_root / "ARM_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
                (run_dir / "task.json").write_text(
                    json.dumps(
                        {
                            "task_id": "task",
                            "task_completion_pass": 1,
                            "state_requirements_met": 1,
                            "task_requirements_met": 1,
                            "ux_score": 4.0,
                            "input_tokens": 200,
                            "output_tokens": 100,
                            "cost_usd": 0.01,
                            "tool_calls": 2,
                            "tool_errors": 0,
                            "redundant_calls": 0,
                            "agent_model": {"model_name": "model", "reasoning_level": None},
                        }
                    ),
                    encoding="utf-8",
                )
                arms[arm] = arm_root.resolve()

            original_audit = GATE.audit_checkout
            GATE.audit_checkout = lambda _: {
                "revision": "revision",
                "test_split_count": 1,
                "official_runs_per_task": 1,
            }
            try:
                result = GATE.gate_results(checkout, plan_path, protocol_path, scoring_path, arms)
                self.assertEqual(result["status"], "CANDIDATE_RESULTS_COMPLETE__NOT_SCORED")
                self.assertTrue(result["held_out_outcomes_opened"])
                self.assertFalse(result["scientific_aggregates_computed"])
                (arms["policy_relative"] / "learning.json").write_text(
                    "changed\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(ValueError, "differs from its manifest"):
                    GATE.gate_results(checkout, plan_path, protocol_path, scoring_path, arms)
            finally:
                GATE.audit_checkout = original_audit

    def test_arm_manifest_binds_membership_and_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "learning.json"
            artifact.write_text("{}\n", encoding="utf-8")
            plan = {
                "study_id": "study",
                "status": "CANDIDATES_AND_PREDICTION_FROZEN__HELD_OUT_OUTCOMES_UNOPENED",
                "held_out_outcomes_opened": False,
                "candidates": {"policy_relative": {"membership_sha256": "a" * 64}},
                "freeze_inputs": {"run_contract_sha256": "b" * 64},
                "run_contract": run_contract(),
            }
            manifest = PREPARE.prepare(
                plan,
                "c" * 64,
                "policy_relative",
                artifact,
                "learning.json",
                0.01,
                1.0,
            )
        self.assertEqual(manifest["candidate_membership_sha256"], "a" * 64)
        self.assertEqual(len(manifest["learning_artifact_sha256"]), 64)
        self.assertEqual(manifest["learning_artifact_relative_path"], "learning.json")
        self.assertEqual(manifest["learning_artifact_build_cost_usd"], 0.01)
        baseline = PREPARE.prepare(plan, "c" * 64, "no_learning", None)
        self.assertIsNone(baseline["learning_artifact_sha256"])

    def test_freeze_requires_an_executable_contract(self):
        draft = {
            "study_id": "study",
            "status": "DRAFT_CANDIDATE_PLAN__HELD_OUT_OUTCOMES_UNOPENED",
            "held_out_outcomes_opened": False,
            "candidate_size": 2,
            "starting_agent": {"model_name": "model", "reasoning_level": None},
            "predicted_choice": "policy_relative",
            "candidates": {name: {} for name in ("a", "policy_relative")},
        }
        protocol = {"study_id": "study"}
        scoring = {
            "study_id": "study",
            "status": "SCORING_CONTRACT_FROZEN__HELD_OUT_OUTCOMES_UNOPENED",
            "held_out_outcomes_opened": False,
            "candidate_arms": ["a", "policy_relative"],
            "predicted_choice": "policy_relative",
            "runs_per_task": 5,
        }
        frozen = FREEZE.freeze(draft, protocol, scoring, run_contract())
        self.assertTrue(frozen["status"].startswith("CANDIDATES_AND_PREDICTION_FROZEN"))
        broken = run_contract()
        broken["starting_agent"]["model_revision"] = None
        with self.assertRaisesRegex(ValueError, "model_revision"):
            FREEZE.freeze(draft, protocol, scoring, broken)
        different_agent = run_contract()
        different_agent["starting_agent"]["model_name"] = "other-model"
        with self.assertRaisesRegex(ValueError, "differs from the measured agent"):
            FREEZE.freeze(draft, protocol, scoring, different_agent)

    def test_trajectory_gate_preserves_trace_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.json"
            path.write_text(
                json.dumps(
                    {
                        "task_id": "task",
                        "task_completion_pass": 0,
                        "state_requirements_met": 1,
                        "task_requirements_met": 0,
                        "ux_score": 3.0,
                        "input_tokens": 200,
                        "output_tokens": 100,
                        "cost_usd": 0.01,
                        "tool_calls": 2,
                        "tool_errors": 1,
                        "redundant_calls": 0,
                        "agent_model": {"model_name": "model", "reasoning_level": None},
                    }
                ),
                encoding="utf-8",
            )
            record = GATE.validate_trajectory(path, "task")
        self.assertEqual(record["task_completion_pass"], 0)
        self.assertEqual(record["state_requirements_met"], 1)

    def test_score_reports_gain_regression_and_trace_diagnostics(self):
        task_types = {"t1": "returns", "t2": "returns", "t3": "shipping", "t4": "shipping"}
        arm_rates = {
            "no_learning": [0.4, 0.6, 0.4, 0.6],
            "source_proportional": [0.6, 0.6, 0.4, 0.6],
            "deterministic_random": [0.4, 0.4, 0.4, 0.6],
            "static_difficulty": [0.6, 0.8, 0.4, 0.6],
            "policy_relative": [0.8, 0.8, 0.2, 0.8],
        }
        loaded = {}
        for arm, rates in arm_rates.items():
            loaded[arm] = {}
            for task_id, rate in zip(task_types, rates, strict=True):
                successes = int(rate * 5)
                loaded[arm][task_id] = [
                    {
                        "task_completion_pass": int(index < successes),
                        "state_requirements_met": int(index < successes),
                        "task_requirements_met": int(index < successes),
                        "ux_score": 4.0,
                        "cost_usd": 0.01,
                        "tool_calls": 2,
                        "tool_errors": 0,
                        "redundant_calls": 0,
                    }
                    for index in range(5)
                ]
        candidates = [
            "source_proportional",
            "deterministic_random",
            "static_difficulty",
            "policy_relative",
        ]
        plan = {"candidates": {arm: {"membership_sha256": arm * 2} for arm in candidates}}
        scoring = {
            "baseline_arm": "no_learning",
            "candidate_arms": candidates,
            "predicted_choice": "policy_relative",
            "regression": {"material_threshold": -0.2},
            "uncertainty": {"random_seed": 1, "resamples": 100},
            "trace_interpretation": "diagnostic only",
        }
        result = SCORE.score(loaded, task_types, plan, scoring)
        self.assertEqual(result["observed_best_candidates"], ["policy_relative"])
        self.assertEqual(result["observed_best_actions_including_no_learning"], ["policy_relative"])
        self.assertEqual(result["allocation_regret"], 0.0)
        self.assertEqual(
            result["task_regressions"]["policy_relative"]["material_regression_task_ids"],
            ["t3"],
        )
        self.assertEqual(result["trace_interpretation"], "diagnostic only")

    def test_allocation_regret_keeps_no_learning_as_an_action(self):
        task_types = {"t1": "returns"}
        arms = {
            "no_learning": 1.0,
            "source_proportional": 0.8,
            "deterministic_random": 0.8,
            "static_difficulty": 0.8,
            "policy_relative": 0.8,
        }
        loaded = {
            arm: {
                "t1": [
                    {
                        "task_completion_pass": int(index < rate * 5),
                        "state_requirements_met": int(index < rate * 5),
                        "task_requirements_met": int(index < rate * 5),
                        "ux_score": 4.0,
                        "cost_usd": 0.01,
                        "tool_calls": 1,
                        "tool_errors": 0,
                        "redundant_calls": 0,
                    }
                    for index in range(5)
                ]
            }
            for arm, rate in arms.items()
        }
        candidates = [name for name in arms if name != "no_learning"]
        plan = {"candidates": {arm: {"membership_sha256": arm} for arm in candidates}}
        scoring = {
            "baseline_arm": "no_learning",
            "candidate_arms": candidates,
            "predicted_choice": "policy_relative",
            "regression": {"material_threshold": -0.2},
            "uncertainty": {"random_seed": 1, "resamples": 10},
            "trace_interpretation": "diagnostic only",
        }
        result = SCORE.score(loaded, task_types, plan, scoring)
        self.assertAlmostEqual(result["allocation_regret"], 0.2)
        self.assertEqual(result["candidate_only_allocation_regret"], 0.0)
        self.assertEqual(result["observed_best_actions_including_no_learning"], ["no_learning"])


if __name__ == "__main__":
    unittest.main()
