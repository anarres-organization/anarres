import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class NativeQFBenchV3ProtocolTest(unittest.TestCase):
    def test_candidate_contract(self):
        text = (ROOT / "candidates/conditional-contract/SKILL.md").read_text().lower()
        self.assertIn("one-step forecast", text)
        self.assertIn("terminal period", text)
        self.assertIn("remove this resource after the run", text)
        self.assertNotIn("verifier output", text.rsplit("contains no", 1)[0])

    def test_development_only_authorization(self):
        shared = json.loads((ROOT.parent / "native-qfbench-v2/TASK_SPLIT.json").read_text())
        authorization = json.loads((ROOT / "STAGE_AUTHORIZATION.json").read_text())
        expected = {row["task_id"] for row in shared["development"]}
        self.assertEqual(set(authorization["authorized_task_ids"]), expected)

    def test_freeze_manifest(self):
        manifest = json.loads((ROOT / "FREEZE_MANIFEST.sha256.json").read_text())
        for name, expected in manifest["files"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)
        for name, expected in manifest["shared_inputs"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
