import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "gate_development_training.py"
SPEC = importlib.util.spec_from_file_location("gate_development_training", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DevelopmentTrainingGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.contract_path = self.root / "contract.json"
        self.contract = {
            "study": "study",
            "contract": "contract",
            "development_panel": {"arms": ["a", "b"]},
            "training": {
                "seeds": [1, 2],
                "maximum_updates": 2,
                "checkpoint_updates": [1, 2],
                "online_trajectories_per_update": 2,
            },
        }
        self.contract_path.write_text(json.dumps(self.contract))
        for arm in self.contract["development_panel"]["arms"]:
            for seed in self.contract["training"]["seeds"]:
                self.write_run(arm, seed)

    def tearDown(self):
        self.temporary.cleanup()

    def write_run(self, arm: str, seed: int):
        run = self.runs / f"{arm}-{seed}"
        (run / "checkpoints").mkdir(parents=True)
        training = run / "training.jsonl"
        training.write_text("{}\n{}\n")
        samples = run / "sample.jsonl"
        samples.write_text("{}\n{}\n{}\n{}\n")
        checkpoints = {}
        for step in (1, 2):
            checkpoint = run / "checkpoints" / f"step_{step:06d}.ckpt"
            checkpoint.write_text(f"{arm}-{seed}-{step}")
            checkpoints[str(step)] = sha256(checkpoint)
        manifest = {
            "study": "study",
            "contract": "contract",
            "status": "complete",
            "arm": arm,
            "seed": seed,
            "initial_step": 0,
            "final_step": 2,
            "checks": {"complete": True},
            "replay": {"items_sha256": hashlib.sha256(arm.encode()).hexdigest()},
            "artifact_sha256": {
                "contract": sha256(self.contract_path),
                "training_log": sha256(training),
                "online_samples": sha256(samples),
                "required_checkpoints": checkpoints,
            },
        }
        (run / "MATCHED_TRAINING_RUN.json").write_text(json.dumps(manifest))

    def test_complete_matrix_passes_without_opening_outcomes(self):
        result = MODULE.gate_training_matrix(self.contract_path, self.runs)
        self.assertEqual(result["run_count"], 4)
        self.assertEqual(result["checkpoint_count"], 8)
        self.assertFalse(result["endpoint_outcomes_opened"])
        self.assertEqual(
            result["status"],
            "DEVELOPMENT_TRAINING_COMPLETE__ENDPOINT_OUTCOMES_UNOPENED",
        )

    def test_missing_run_fails(self):
        missing = self.runs / "b-2" / "MATCHED_TRAINING_RUN.json"
        missing.unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            MODULE.gate_training_matrix(self.contract_path, self.runs)

    def test_checkpoint_mutation_fails(self):
        checkpoint = self.runs / "a-1" / "checkpoints" / "step_000001.ckpt"
        checkpoint.write_text("mutated")
        with self.assertRaisesRegex(ValueError, "wrong hash"):
            MODULE.gate_training_matrix(self.contract_path, self.runs)

    def test_empty_integrity_checks_fail(self):
        manifest_path = self.runs / "a-1" / "MATCHED_TRAINING_RUN.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["checks"] = {}
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "differs from the contract"):
            MODULE.gate_training_matrix(self.contract_path, self.runs)


if __name__ == "__main__":
    unittest.main()
