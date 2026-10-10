from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_hygiene_module():
    source = Path(__file__).resolve().parents[2] / "tools" / "check_repo_hygiene.py"
    spec = importlib.util.spec_from_file_location("check_repo_hygiene", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicSurfaceTest(unittest.TestCase):
    def test_rejects_machine_specific_cluster_path(self) -> None:
        hygiene = load_hygiene_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "notes.md"
            machine_path = "/" + "lfs" + "/cluster/run"
            candidate.write_text(f"artifact lives under {machine_path}", encoding="utf-8")
            with patch.object(hygiene, "ROOT", root):
                problems = hygiene.inspect(candidate)
        self.assertTrue(any("machine-specific storage path" in problem for problem in problems))

    def test_accepts_public_artifact_reference(self) -> None:
        hygiene = load_hygiene_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "artifact.json"
            candidate.write_text(
                '{"uri":"https://huggingface.co/datasets/org/release","sha256":"sha256:abc"}',
                encoding="utf-8",
            )
            with patch.object(hygiene, "ROOT", root):
                problems = hygiene.inspect(candidate)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
