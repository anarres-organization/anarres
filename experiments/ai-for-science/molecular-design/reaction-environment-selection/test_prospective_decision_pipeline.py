from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def load_module(name: str, script: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FREEZE = load_module("freeze_prospective_decision", "freeze_prospective_decision.py")
SCORE = load_module("score_prospective_results", "score_prospective_results.py")
DEVELOPMENT = load_module("score_development_results", "score_development_results.py")

FEATURES = FREEZE.GRAPH


class ProspectiveDecisionPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.contract_path = self.root / "contract.json"
        self.prospective_contract_path = self.root / "prospective-contract.json"
        self.development_path = self.root / "development.json"
        self.banks_path = self.root / "banks.json"
        self.scorer_path = ROOT / "scripts" / "score_prospective_results.py"
        self.contract = {
            "study": "study",
            "contract": "contract",
            "development_panel": {
                "arms": ["a", "b", "c", "d"],
                "bank_size": 2,
                "prospective_banks_excluded": ["operational_hybrid", "graph_aware_hybrid"],
            },
            "training": {
                "seeds": [1, 2],
                "checkpoint_updates": [2, 4, 6],
                "target_oracle_attempt_budgets": [20, 40, 60],
            },
            "evaluation": {
                "attempts_per_policy_seed_checkpoint": 10,
                "primary_outcome": "rate",
            },
        }
        coordinates = {
            arm: {feature: float(index + offset + 1) for offset, feature in enumerate(FEATURES)}
            for index, arm in enumerate(self.contract["development_panel"]["arms"])
        }
        curves = []
        seed_records = []
        for arm_index, arm in enumerate(self.contract["development_panel"]["arms"]):
            for budget_index, budget in enumerate([20, 40, 60]):
                utility = 0.01 * (arm_index + 1) + 0.005 * budget_index
                curves.append(
                    {
                        "arm": arm,
                        "target_oracle_attempt_budget": budget,
                        "mean_utility": utility,
                    }
                )
                for seed in (1, 2):
                    seed_records.append(
                        {
                            "arm": arm,
                            "training_seed": seed,
                            "target_oracle_attempt_budget": budget,
                            "warm_start_rate": 0.1,
                            "utility": utility,
                        }
                    )
        self.development = {
            "contract": "contract",
            "prospective_outcomes_opened": False,
            "measurement_coordinates": coordinates,
            "mean_utility_curves": curves,
            "seed_records": seed_records,
        }
        self.contract_path.write_text(json.dumps(self.contract))
        self.prospective_contract_path.write_text(json.dumps({"contract": "prospective"}))
        self.banks = {
            "qualification": "pass",
            "outcomes_opened": False,
            "banks": {
                "operational_hybrid": {
                    "members": ["o1", "o2"],
                    "coordinates": {
                        feature: float(2 + offset) for offset, feature in enumerate(FEATURES)
                    },
                },
                "graph_aware_hybrid": {
                    "members": ["g1", "g2"],
                    "coordinates": {
                        feature: float(4 + offset) for offset, feature in enumerate(FEATURES)
                    },
                },
            },
            "inputs": {
                "prospective_contract_sha256": FREEZE.sha256(self.prospective_contract_path)
            },
        }
        self.development_path.write_text(json.dumps(self.development))
        self.banks_path.write_text(json.dumps(self.banks))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def freeze(self) -> dict:
        return FREEZE.freeze(
            self.contract_path,
            self.prospective_contract_path,
            self.development_path,
            self.banks_path,
            self.scorer_path,
        )

    def test_freeze_fits_both_models_without_opening_outcomes(self) -> None:
        result = self.freeze()
        self.assertFalse(result["prospective_outcomes_opened"])
        self.assertEqual(set(result["models"]), {"operational", "graph_aware"})
        self.assertEqual(len(result["decisions"]), 3)
        self.assertEqual(set(result["bank_membership_sha256"]), set(self.banks["banks"]))

    def test_development_scorer_requires_gated_complete_reports(self) -> None:
        bank_qualification = self.root / "bank-qualification.json"
        bank_qualification.write_text(
            json.dumps(
                {
                    "qualification": "pass",
                    "summaries": [
                        self.development["measurement_coordinates"],
                        self.development["measurement_coordinates"],
                    ],
                }
            )
        )
        panels = self.root / "development-panels"
        panels.mkdir()
        gate_records = []
        for arm in ["warm_start", *self.contract["development_panel"]["arms"]]:
            steps = (0,) if arm == "warm_start" else (2, 4, 6)
            for seed in (1, 2):
                for step in steps:
                    panel = panels / DEVELOPMENT.panel_name(arm, seed, step)
                    panel.mkdir()
                    report = panel / "qualifying-hit-score.json"
                    report.write_text(
                        json.dumps(
                            {
                                "status": "complete",
                                "attempts": 10,
                                "infrastructure_failures": 0,
                                "unique_qualifying_hit_rate": 0.1 + 0.001 * step,
                            }
                        )
                    )
                    gate_records.append(
                        {
                            "arm": arm,
                            "training_seed": seed,
                            "checkpoint_step": step,
                            "qualifying_report_name": report.name,
                            "qualifying_report_sha256": DEVELOPMENT.sha256(report),
                        }
                    )
        gate_path = self.root / "development-gate.json"
        gate_path.write_text(
            json.dumps(
                {
                    "comparative_scoring_authorized": True,
                    "panel_kind": "development",
                    "contract_sha256": DEVELOPMENT.sha256(self.contract_path),
                    "records": gate_records,
                }
            )
        )
        result = DEVELOPMENT.score(
            self.contract_path,
            bank_qualification,
            gate_path,
            panels,
        )
        self.assertFalse(result["prospective_outcomes_opened"])
        self.assertEqual(len(result["mean_utility_curves"]), 12)

    def test_freeze_rejects_opened_outcomes(self) -> None:
        self.banks["outcomes_opened"] = True
        self.banks_path.write_text(json.dumps(self.banks))
        with self.assertRaisesRegex(ValueError, "before any outcomes"):
            self.freeze()

    def test_freeze_rejects_unbound_construction_contract(self) -> None:
        self.banks["inputs"]["prospective_contract_sha256"] = "0" * 64
        self.banks_path.write_text(json.dumps(self.banks))
        with self.assertRaisesRegex(ValueError, "construction contract digest"):
            self.freeze()

    def test_score_requires_and_preserves_frozen_decisions(self) -> None:
        frozen = self.freeze()
        freeze_path = self.root / "freeze.json"
        freeze_path.write_text(json.dumps(frozen))
        panels = self.root / "panels"
        panels.mkdir()
        gate_records = []
        for bank_index, bank in enumerate(self.banks["banks"]):
            for seed in (1, 2):
                for step, budget in zip((2, 4, 6), (20, 40, 60), strict=True):
                    panel = panels / SCORE.panel_name(bank, seed, step)
                    panel.mkdir()
                    rate = 0.1 + 0.01 * (bank_index + 1) + 0.001 * budget
                    report = panel / "qualifying-hit-score.json"
                    report.write_text(
                        json.dumps(
                            {
                                "status": "complete",
                                "attempts": 10,
                                "infrastructure_failures": 0,
                                "unique_qualifying_hit_rate": rate,
                            }
                        )
                    )
                    gate_records.append(
                        {
                            "arm": bank,
                            "training_seed": seed,
                            "checkpoint_step": step,
                            "qualifying_report_name": report.name,
                            "qualifying_report_sha256": SCORE.sha256(report),
                        }
                    )
        gate_path = self.root / "gate.json"
        gate_path.write_text(
            json.dumps(
                {
                    "comparative_scoring_authorized": True,
                    "panel_kind": "prospective",
                    "contract_sha256": SCORE.sha256(self.contract_path),
                    "records": gate_records,
                }
            )
        )
        result = SCORE.score(
            self.contract_path,
            self.development_path,
            freeze_path,
            gate_path,
            panels,
        )
        self.assertTrue(result["prospective_outcomes_opened"])
        self.assertEqual(len(result["decisions"]), 3)
        self.assertEqual(
            [row["predicted_winner"] for row in result["decisions"]],
            [row["predicted_winner"] for row in frozen["decisions"]],
        )


if __name__ == "__main__":
    unittest.main()
