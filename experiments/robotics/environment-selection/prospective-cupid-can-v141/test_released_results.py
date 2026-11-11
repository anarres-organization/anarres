from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts/score_released_panel.py"
SPEC = importlib.util.spec_from_file_location("score_released_panel", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


class ReleasedCanResultTest(unittest.TestCase):
    def test_released_result_recomputes_exactly(self) -> None:
        observed = SCORER.compute(
            json.loads((ROOT / "OUTCOMES.json").read_text()),
            json.loads((ROOT / "RELEASE_GATE.json").read_text()),
            json.loads((ROOT / "CANDIDATES.json").read_text()),
        )
        expected = json.loads((ROOT / "RESULTS.json").read_text())
        self.assertEqual(observed, expected)
        self.assertEqual(expected["best_arm_by_mean"], ["length_50"])
        self.assertAlmostEqual(expected["allocation_regret"], 0.014)

    def test_outcome_hash_tampering_is_rejected(self) -> None:
        outcomes = json.loads((ROOT / "OUTCOMES.json").read_text())
        outcomes["records"][0]["outcome_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "outcome hash"):
            SCORER.compute(
                outcomes,
                json.loads((ROOT / "RELEASE_GATE.json").read_text()),
                json.loads((ROOT / "CANDIDATES.json").read_text()),
            )


if __name__ == "__main__":
    unittest.main()
