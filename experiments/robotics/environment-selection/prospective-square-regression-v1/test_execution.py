import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREPARE = load("square_prepare_candidates", ROOT / "scripts/prepare_candidate_dataset.py")
sys.modules["prepare_candidate_dataset"] = PREPARE
SCORE = load("square_score_candidates", ROOT / "scripts/score_candidate_results.py")
EXECUTION = load("square_freeze_execution", ROOT / "scripts/freeze_execution.py")


class CandidateExecutionTest(unittest.TestCase):
    def test_released_execution_freeze_binds_every_input_and_run(self) -> None:
        freeze = json.loads((ROOT / "EXECUTION_FREEZE.json").read_text())
        self.assertFalse(freeze["candidate_outcomes_opened"])
        self.assertEqual(freeze["expected_candidate_runs"], 15)
        self.assertEqual(freeze["expected_candidate_evaluation_episodes"], 3840)
        for relative, expected in freeze["inputs"].items():
            self.assertEqual(PREPARE.sha256(ROOT / relative), expected)
        observed = {(row["candidate_id"], row["seed"]) for row in freeze["candidate_runs"]}
        self.assertEqual(
            observed,
            {
                (candidate, seed)
                for candidate in (
                    "random_50",
                    "length_50",
                    "coverage_50",
                    "failure_coverage_50",
                    "failure_coverage_short_50",
                )
                for seed in (3101, 3102, 3103)
            },
        )

    def test_execution_freeze_expands_the_exact_arm_seed_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_bank = root / "states.hdf5"
            state_bank.write_bytes(b"state-bank")
            manifest = root / "state.json"
            manifest.write_text(json.dumps({"state_bank_sha256": PREPARE.sha256(state_bank)}))
            protocol = {
                "study_id": "square-test",
                "source": {"dataset_sha256": "dataset"},
                "candidates": [
                    {"id": "all_data_reference"},
                    {"id": "candidate_a"},
                ],
                "training": {"candidate_seeds": [1, 2, 3]},
                "evaluation": {"states": 2, "rollout_replicates_per_state": 2},
            }
            protocol_path = root / "protocol.json"
            protocol_path.write_text(json.dumps(protocol))
            members = ["demo_0", "demo_1"]
            membership = PREPARE.hashlib.sha256(b"demo_0\ndemo_1\n").hexdigest()
            candidates = {
                "study_id": "square-test",
                "status": "CANDIDATES_AND_PREDICTIONS_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
                "candidate_outcomes_opened": False,
                "candidates": {
                    "all_data_reference": {
                        "count": 2,
                        "members": members,
                        "membership_sha256": membership,
                    },
                    "candidate_a": {
                        "count": 2,
                        "members": members,
                        "membership_sha256": membership,
                    },
                },
            }
            candidates_path = root / "candidates.json"
            candidates_path.write_text(json.dumps(candidates))
            scoring = {
                "study_id": "square-test",
                "candidate_outcomes_opened": False,
                "comparison_arms": ["all_data_reference", "candidate_a"],
                "point_prediction": "candidate_a",
                "integrity": {"required_candidate_policies": 3},
            }
            scoring_path = root / "scoring.json"
            scoring_path.write_text(json.dumps(scoring))
            sources_path = root / "sources.json"
            sources_path.write_text(
                json.dumps({"sources": [{"name": "CuraEval", "revision": "revision"}]})
            )
            script = root / "runner.py"
            script.write_text("pass\n")
            result = EXECUTION.build(
                candidates_path,
                protocol_path,
                scoring_path,
                sources_path,
                state_bank,
                manifest,
                [script],
            )
            self.assertEqual(result["expected_candidate_runs"], 3)
            self.assertEqual(result["expected_candidate_evaluation_episodes"], 12)
            self.assertEqual([run["seed"] for run in result["candidate_runs"]], [1, 2, 3])

    def test_scoring_contract_binds_protocol_and_implementation(self) -> None:
        contract = json.loads((ROOT / "SCORING_CONTRACT.json").read_text())
        self.assertFalse(contract["candidate_outcomes_opened"])
        self.assertEqual(
            PREPARE.sha256(ROOT / "PROTOCOL.json"), contract["bound_inputs"]["PROTOCOL.json"]
        )
        self.assertEqual(
            PREPARE.sha256(ROOT / "scripts/score_candidate_results.py"),
            contract["bound_inputs"]["scripts/score_candidate_results.py"],
        )

    def test_regression_summary_preserves_the_frozen_direction(self) -> None:
        rows = [
            {
                "candidate_id": "a",
                "stratum": index,
                "frozen_risk": float(index),
                "observed_change": float(-index),
            }
            for index in range(8)
        ]
        summary = SCORE.summarize_regression(rows, 2)
        self.assertAlmostEqual(summary["spearman_risk_vs_success_change"], -1.0)
        self.assertLess(summary["high_minus_low_risk_success_change"], 0.0)
        np.testing.assert_array_equal(SCORE.ranks(np.asarray([2.0, 1.0, 1.0])), [2.0, 0.5, 0.5])

    def test_prepared_masks_are_bound_to_frozen_memberships(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hdf5"
            with h5py.File(source, "w") as dataset:
                data = dataset.create_group("data")
                for index in range(6):
                    data.create_group(f"demo_{index}")
            protocol = {
                "study_id": "square-test",
                "source": {"dataset_sha256": PREPARE.sha256(source)},
                "candidates": [
                    {"id": "all_data_reference"},
                    {"id": "candidate_a"},
                ],
            }
            protocol_path = root / "protocol.json"
            protocol_path.write_text(json.dumps(protocol))
            members = ["demo_0", "demo_2", "demo_4"]
            candidates = {
                "study_id": "square-test",
                "status": "CANDIDATES_AND_PREDICTIONS_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
                "candidate_outcomes_opened": False,
                "candidates": {
                    "all_data_reference": {
                        "count": 6,
                        "members": [f"demo_{index}" for index in range(6)],
                        "membership_sha256": PREPARE.hashlib.sha256(
                            "".join(f"demo_{index}\n" for index in range(6)).encode()
                        ).hexdigest(),
                    },
                    "candidate_a": {
                        "count": 3,
                        "members": members,
                        "membership_sha256": PREPARE.hashlib.sha256(
                            b"demo_0\ndemo_2\ndemo_4\n"
                        ).hexdigest(),
                    },
                },
            }
            candidates_path = root / "candidates.json"
            candidates_path.write_text(json.dumps(candidates))
            prepared = root / "prepared.hdf5"
            report = PREPARE.prepare(source, prepared, candidates_path, protocol_path)
            self.assertFalse(report["candidate_outcomes_opened"])
            with h5py.File(prepared, "r") as dataset:
                observed = [
                    value.decode() for value in dataset["mask"][PREPARE.mask_key("candidate_a")][:]
                ]
            self.assertEqual(observed, members)

            prepared.chmod(0o644)
            with h5py.File(prepared, "a") as dataset:
                del dataset["mask"][PREPARE.mask_key("candidate_a")]
                dataset["mask"].create_dataset(
                    PREPARE.mask_key("candidate_a"), data=[b"demo_1", b"demo_3", b"demo_5"]
                )
            with self.assertRaisesRegex(ValueError, "prepared mask mismatch"):
                PREPARE.validate_prepared(prepared, candidates_path, protocol_path)


if __name__ == "__main__":
    unittest.main()
