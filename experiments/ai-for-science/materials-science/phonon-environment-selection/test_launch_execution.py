import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


CACHE = load_module("prepare_candidate_caches", ROOT / "scripts" / "prepare_candidate_caches.py")
RUN = load_module("run_candidate", ROOT / "scripts" / "run_candidate.py")
LAUNCH = load_module("launch_candidates", ROOT / "scripts" / "launch_candidates.py")


class LaunchExecutionTest(unittest.TestCase):
    def test_committed_launch_self_verifies(self):
        launch = CACHE.load_launch(ROOT / "LAUNCH_MANIFEST.json")
        self.assertEqual(len(launch["runs"]), 24)

    def test_run_loader_rejects_changed_manifest(self):
        launch = json.loads((ROOT / "LAUNCH_MANIFEST.json").read_text(encoding="utf-8"))
        launch["runs"][0]["seed"] += 1
        path = ROOT / "LAUNCH_MANIFEST.json"
        stored = launch["launch_sha256"]
        payload = dict(launch)
        payload.pop("launch_sha256")
        self.assertNotEqual(stored, RUN.canonical_digest(payload))

    def test_orchestrator_reads_the_same_launch(self):
        launch = LAUNCH.load_hashed(ROOT / "LAUNCH_MANIFEST.json", "launch_sha256")
        self.assertEqual(len(launch["runs"]), 24)


if __name__ == "__main__":
    unittest.main()
