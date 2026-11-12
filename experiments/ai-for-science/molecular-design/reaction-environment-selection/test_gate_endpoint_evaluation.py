import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "gate_endpoint_evaluation.py"
SPEC = importlib.util.spec_from_file_location("gate_endpoint_evaluation", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EndpointEvaluationGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.panels = self.root / "panels"
        self.panels.mkdir()
        self.contract_path = self.root / "contract.json"
        self.thresholds_path = self.root / "thresholds.json"
        self.contract = {
            "study": "study",
            "contract": "matched",
            "development_panel": {
                "arms": ["a", "b"],
                "prospective_banks_excluded": ["p", "q"],
            },
            "training": {"seeds": [1], "checkpoint_updates": [2, 4]},
            "evaluation": {
                "attempts_per_policy_seed_checkpoint": 2,
                "seeds": {"1": {"0": 10, "2": 12, "4": 14}},
            },
        }
        self.contract_path.write_text(json.dumps(self.contract))
        self.thresholds_path.write_text(json.dumps({"contract": "q07820-qualifying-hit-v1"}))
        for panel in MODULE.expected_panels(self.contract):
            self.write_panel(*panel)

    def tearDown(self):
        self.temporary.cleanup()

    def write_panel(self, arm: str, seed: int, step: int):
        panel = self.panels / MODULE.panel_name(arm, seed, step)
        panel.mkdir()
        samples = panel / "samples.jsonl"
        samples.write_text('{"smiles":"C"}\n{"smiles":"CC"}\n')
        docking = panel / "docking-records.jsonl"
        docking.write_text("{}\n{}\n")
        endpoint = panel / "endpoint-records.jsonl"
        endpoint.write_text("{}\n{}\n")
        (panel / "SAMPLE_MANIFEST.json").write_text(
            json.dumps(
                {
                    "study": "study",
                    "contract": "matched",
                    "status": "complete",
                    "arm": arm,
                    "training_seed": seed,
                    "checkpoint_step": step,
                    "evaluation_seed": self.contract["evaluation"]["seeds"][str(seed)][str(step)],
                    "attempts": 2,
                    "identity": {
                        "policy_sha256": hashlib.sha256(f"{arm}-{step}".encode()).hexdigest()
                    },
                    "artifact_sha256": {
                        "contract": sha256(self.contract_path),
                        "samples": sha256(samples),
                    },
                }
            )
        )
        (panel / "DOCKING_REPORT.json").write_text(
            json.dumps(
                {
                    "contract": "matched",
                    "status": "complete",
                    "sample_seed": self.contract["evaluation"]["seeds"][str(seed)][str(step)],
                    "attempts": 2,
                    "infrastructure_failures": 0,
                    "inputs": {"samples_sha256": sha256(samples)},
                    "output_records_sha256": sha256(docking),
                }
            )
        )
        (panel / "METRICS_REPORT.json").write_text(
            json.dumps(
                {
                    "contract": "matched",
                    "status": "complete",
                    "attempts": 2,
                    "inputs": {"docking_records_sha256": sha256(docking)},
                    "output_records_sha256": sha256(endpoint),
                }
            )
        )
        (panel / "QUALIFYING_HITS.json").write_text(
            json.dumps(
                {
                    "contract": "q07820-qualifying-hit-v1",
                    "status": "complete",
                    "attempts": 2,
                    "infrastructure_failures": 0,
                    "inputs": {
                        "records_sha256": sha256(endpoint),
                        "thresholds_sha256": sha256(self.thresholds_path),
                    },
                    "scored_records": [{}, {}],
                }
            )
        )

    def test_complete_matrix_authorizes_comparison(self):
        result = MODULE.gate_evaluation_matrix(
            self.contract_path,
            self.thresholds_path,
            self.panels,
        )
        self.assertEqual(result["panel_count"], 5)
        self.assertTrue(result["comparative_scoring_authorized"])

    def test_missing_panel_fails(self):
        panel = self.panels / MODULE.panel_name("b", 1, 4)
        for item in panel.iterdir():
            item.unlink()
        panel.rmdir()
        with self.assertRaisesRegex(ValueError, "missing"):
            MODULE.gate_evaluation_matrix(
                self.contract_path,
                self.thresholds_path,
                self.panels,
            )

    def test_prospective_panel_uses_only_frozen_prospective_arms(self):
        for path in list(self.panels.iterdir()):
            for item in path.iterdir():
                item.unlink()
            path.rmdir()
        for panel in MODULE.expected_panels(self.contract, "prospective"):
            self.write_panel(*panel)
        result = MODULE.gate_evaluation_matrix(
            self.contract_path,
            self.thresholds_path,
            self.panels,
            "prospective",
        )
        self.assertEqual(result["panel_kind"], "prospective")
        self.assertEqual(result["panel_count"], 5)

    def test_infrastructure_failure_blocks_comparison(self):
        report = self.panels / MODULE.panel_name("a", 1, 2) / "DOCKING_REPORT.json"
        value = json.loads(report.read_text())
        value["status"] = "invalid"
        value["infrastructure_failures"] = 1
        report.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "docking report"):
            MODULE.gate_evaluation_matrix(
                self.contract_path,
                self.thresholds_path,
                self.panels,
            )

    def test_mutated_endpoint_records_fail(self):
        panel = self.panels / MODULE.panel_name("a", 1, 4)
        (panel / "endpoint-records.jsonl").write_text("mutated\n")
        with self.assertRaisesRegex(ValueError, "metric report"):
            MODULE.gate_evaluation_matrix(
                self.contract_path,
                self.thresholds_path,
                self.panels,
            )


if __name__ == "__main__":
    unittest.main()
