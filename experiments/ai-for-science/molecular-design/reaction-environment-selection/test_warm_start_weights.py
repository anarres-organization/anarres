import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import torch

SCRIPT = Path(__file__).parent / "scripts" / "warm_start_weights.py"
SPEC = importlib.util.spec_from_file_location("warm_start_weights", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WarmStartWeightsTests(unittest.TestCase):
    def test_extraction_keeps_only_scientific_handoff_fields(self):
        checkpoint = {
            "rxnflow_version": "2.1.0",
            "step": 1000,
            "config": {"env_dir": "prepared"},
            "environment": {
                "rxnflow_version": "2.1.0",
                "content_sha256": "abc",
                "synthesis": {"reaction": "fixed"},
            },
            "model": {"weight": torch.tensor([1.0])},
            "sampling_model": {"weight": torch.tensor([2.0])},
            "objectives": ("qed",),
            "condition_dim": None,
            "optimizer": {"private": "excluded"},
            "lr_scheduler": {"private": "excluded"},
            "replay": {"private": "excluded"},
            "numpy_rng": {"private": "excluded"},
            "torch_rng": torch.tensor([3]),
            "cuda_rng": torch.tensor([4]),
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "checkpoint.pt"
            output = Path(directory) / "weights.pt"
            torch.save(checkpoint, source)
            MODULE.extract_weights(source, output)
            artifact = torch.load(output, weights_only=False)

        self.assertEqual(artifact["artifact_type"], MODULE.ARTIFACT_TYPE)
        self.assertEqual(artifact["source_step"], 1000)
        self.assertEqual(float(artifact["model"]["weight"][0]), 1.0)
        self.assertEqual(float(artifact["sampling_model"]["weight"][0]), 2.0)
        self.assertEqual(artifact["objectives"], ("qed",))
        for excluded in (
            "optimizer",
            "lr_scheduler",
            "replay",
            "numpy_rng",
            "torch_rng",
            "cuda_rng",
        ):
            self.assertNotIn(excluded, artifact)

    def test_extraction_rejects_in_place_output(self):
        path = Path("checkpoint.pt")
        with self.assertRaises(ValueError):
            MODULE.extract_weights(path, path)


if __name__ == "__main__":
    unittest.main()
