import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "sample_endpoint_policy.py"
SPEC = importlib.util.spec_from_file_location("sample_endpoint_policy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EndpointPolicySampleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.policy = self.root / "policy.ckpt"
        self.policy.write_bytes(b"policy")
        self.contract_path = self.root / "contract.json"
        self.contract = {
            "study": "study",
            "contract": "contract",
            "starting_policy": {"weights_only_sha256": sha256(self.policy)},
            "development_panel": {"arms": ["graph"]},
            "training": {
                "seeds": [11],
                "maximum_updates": 20,
                "checkpoint_updates": [10, 20],
            },
            "evaluation": {"seeds": {"11": {"0": 101, "10": 102, "20": 103}}},
        }
        self.contract_path.write_text(json.dumps(self.contract))

    def tearDown(self):
        self.temporary.cleanup()

    def test_warm_start_requires_the_frozen_weights(self):
        identity = MODULE.validate_policy(
            contract=self.contract,
            contract_path=self.contract_path,
            policy=self.policy,
            arm="warm_start",
            training_seed=11,
            checkpoint_step=0,
            training_manifest=None,
        )
        self.assertEqual(identity["kind"], "warm_start")
        self.assertEqual(identity["policy_sha256"], sha256(self.policy))

    def test_trained_checkpoint_binds_manifest_and_contract(self):
        manifest_path = self.root / "MATCHED_TRAINING_RUN.json"
        manifest = {
            "study": "study",
            "contract": "contract",
            "status": "complete",
            "arm": "graph",
            "seed": 11,
            "final_step": 20,
            "checks": {"complete": True},
            "artifact_sha256": {
                "contract": sha256(self.contract_path),
                "required_checkpoints": {"10": sha256(self.policy)},
            },
        }
        manifest_path.write_text(json.dumps(manifest))
        identity = MODULE.validate_policy(
            contract=self.contract,
            contract_path=self.contract_path,
            policy=self.policy,
            arm="graph",
            training_seed=11,
            checkpoint_step=10,
            training_manifest=manifest_path,
        )
        self.assertEqual(identity["kind"], "trained_checkpoint")
        self.assertEqual(identity["training_manifest_sha256"], sha256(manifest_path))

    def test_mismatched_checkpoint_hash_fails(self):
        manifest_path = self.root / "MATCHED_TRAINING_RUN.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "study": "study",
                    "contract": "contract",
                    "status": "complete",
                    "arm": "graph",
                    "seed": 11,
                    "final_step": 20,
                    "checks": {"complete": True},
                    "artifact_sha256": {
                        "contract": sha256(self.contract_path),
                        "required_checkpoints": {"10": "0" * 64},
                    },
                }
            )
        )
        with self.assertRaisesRegex(ValueError, "checkpoint hash"):
            MODULE.validate_policy(
                contract=self.contract,
                contract_path=self.contract_path,
                policy=self.policy,
                arm="graph",
                training_seed=11,
                checkpoint_step=10,
                training_manifest=manifest_path,
            )


if __name__ == "__main__":
    unittest.main()
