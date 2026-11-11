import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class NativeQFBenchV2ProtocolTest(unittest.TestCase):
    def test_partitions_are_disjoint(self):
        split = json.loads((ROOT / "TASK_SPLIT.json").read_text())
        parts = [
            {row["task_id"] for row in split[name]}
            for name in ("development", "target", "shared_protected")
        ]
        self.assertFalse(parts[0] & parts[1])
        self.assertFalse(parts[0] & parts[2])
        self.assertFalse(parts[1] & parts[2])

    def test_only_development_is_authorized(self):
        split = json.loads((ROOT / "TASK_SPLIT.json").read_text())
        authorization = json.loads((ROOT / "STAGE_AUTHORIZATION.json").read_text())
        expected = {row["task_id"] for row in split["development"]}
        self.assertEqual(set(authorization["authorized_task_ids"]), expected)

    def test_refined_candidate_declares_scope_and_removal(self):
        text = (ROOT / "candidates/refined/SKILL.md").read_text().lower()
        self.assertIn("scope and removal", text)
        self.assertIn("remove it after the run", text)
        self.assertNotIn("expected answer", text.replace("expected\n+answer", ""))

    def test_source_and_protocol_are_bound(self):
        source = json.loads((ROOT / "SOURCE.json").read_text())
        protocol = json.loads((ROOT / "PROTOCOL.json").read_text())
        self.assertEqual(source["commit"], "d2fc28b3492f2d73d192fa7eabadf150a19a62fb")
        self.assertEqual(protocol["agent_contract"]["attempts_per_task_condition"], 1)

    def test_freeze_manifest(self):
        manifest = json.loads((ROOT / "FREEZE_MANIFEST.sha256.json").read_text())
        for name, expected in manifest["files"].items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, name)
        predecessor = manifest["predecessor_decision"]
        actual = hashlib.sha256((ROOT / predecessor["path"]).read_bytes()).hexdigest()
        self.assertEqual(actual, predecessor["sha256"])


if __name__ == "__main__":
    unittest.main()
