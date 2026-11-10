import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class HoldoutScoreTest(unittest.TestCase):
    def test_expected_score(self) -> None:
        subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
        score = json.loads((HERE / "SCORE.json").read_text())
        self.assertEqual(score["panels"], 16)
        self.assertEqual(score["pairwise_correct"], 33)
        self.assertEqual(score["pairwise_scored"], 33)
        self.assertEqual(score["pairwise_abstained"], 4)
        self.assertEqual(score["pairwise_accuracy"], 1.0)
        self.assertEqual(score["mean_normalized_regret"], 0.0)


if __name__ == "__main__":
    unittest.main()
