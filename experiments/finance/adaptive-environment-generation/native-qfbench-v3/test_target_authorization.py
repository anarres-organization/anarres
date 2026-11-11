import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TargetAuthorizationTest(unittest.TestCase):
    def test_authorization_matches_committed_decision(self):
        authorization = json.loads((ROOT / "TARGET_AUTHORIZATION.json").read_text())
        decision_path = ROOT / authorization["decision_path"]
        self.assertEqual(hashlib.sha256(decision_path.read_bytes()).hexdigest(), authorization["decision_sha256"])
        decision = json.loads(decision_path.read_text())
        self.assertEqual(decision["decision"], "select")
        self.assertEqual(decision["selected_candidate"], authorization["selected_candidate"])

    def test_only_targets_are_open(self):
        split = json.loads((ROOT.parent / "native-qfbench-v2/TASK_SPLIT.json").read_text())
        authorization = json.loads((ROOT / "TARGET_AUTHORIZATION.json").read_text())
        expected = {row["task_id"] for row in split["target"]}
        self.assertEqual(set(authorization["authorized_task_ids"]), expected)
        protected = {row["task_id"] for row in split["shared_protected"]}
        self.assertFalse(expected & protected)


if __name__ == "__main__":
    unittest.main()
