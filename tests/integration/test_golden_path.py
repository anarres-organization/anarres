import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from anarres.environments.cli import build_manifest


class GoldenPathTest(unittest.TestCase):
    def test_example_produces_content_addressed_manifest(self) -> None:
        root = Path(__file__).resolve().parents[2]
        payload = json.loads(
            (root / "examples/environment-processing/probe.json").read_text(encoding="utf-8")
        )
        source_path = root / "examples/environment-processing/source.json"
        manifest = build_manifest(payload)

        self.assertEqual(
            payload["source_revision"],
            f"sha256:{hashlib.sha256(source_path.read_bytes()).hexdigest()}",
        )
        self.assertEqual(manifest["status_counts"]["admitted"], 2)
        self.assertEqual(manifest["status_counts"]["repair"], 1)
        self.assertEqual(manifest["status_counts"]["quarantine"], 1)
        self.assertTrue(manifest["manifest_digest"].startswith("sha256:"))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertGreater(path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
