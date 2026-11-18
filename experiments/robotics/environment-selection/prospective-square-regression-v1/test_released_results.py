from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "reproduce_released_results.py"
SPEC = importlib.util.spec_from_file_location("reproduce_square_results", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
REPRODUCER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPRODUCER)


class ReleasedSquareResultTest(unittest.TestCase):
    def test_released_result_recomputes_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "reproduce_released_results.py"),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            observed = json.loads(output.read_text(encoding="utf-8"))
        expected = json.loads((ROOT / "RESULTS.json").read_text(encoding="utf-8"))
        self.assertEqual(observed, expected)

    def test_frozen_claims_match_the_release(self) -> None:
        result = json.loads((ROOT / "RESULTS.json").read_text(encoding="utf-8"))
        half_data = {
            key: value
            for key, value in result["arm_mean_success_rates"].items()
            if key != "all_data_reference"
        }
        self.assertEqual(result["point_prediction"], "failure_coverage_short_50")
        self.assertEqual(max(half_data, key=half_data.get), result["point_prediction"])
        self.assertEqual(result["observed_best_arm"], "all_data_reference")
        self.assertAlmostEqual(result["allocation_regret"], 0.0390625)
        self.assertGreater(result["regression"]["spearman_risk_vs_success_change"], 0)
        self.assertGreater(result["regression"]["high_minus_low_risk_success_change"], 0)

    def test_release_gate_matches_every_candidate_evaluation(self) -> None:
        candidates = sorted((ROOT / "evaluations" / "candidates").glob("*.json"))
        REPRODUCER.validate_release_gate(candidates)


if __name__ == "__main__":
    unittest.main()
