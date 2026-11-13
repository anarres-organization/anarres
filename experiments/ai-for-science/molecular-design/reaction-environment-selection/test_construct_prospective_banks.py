from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPT = ROOT / "scripts" / "construct_prospective_banks.py"
SPEC = importlib.util.spec_from_file_location("construct_prospective_banks", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def item(index: int) -> dict:
    return {"record_id": f"r{index}"}


class ProspectiveBankConstructionTests(unittest.TestCase):
    def test_round_robin_is_deterministic_unique_and_balanced(self) -> None:
        first = [item(index) for index in (0, 1, 2, 3)]
        second = [item(index) for index in (0, 4, 5, 6)]
        result = MODULE.round_robin_unique([first, second], first + second, 6)
        self.assertEqual(
            [row["record_id"] for row in result],
            ["r0", "r4", "r1", "r5", "r2", "r6"],
        )

    def test_round_robin_uses_fallback_when_rank_streams_end(self) -> None:
        result = MODULE.round_robin_unique([[item(0)], [item(0)]], [item(0), item(1), item(2)], 3)
        self.assertEqual([row["record_id"] for row in result], ["r0", "r1", "r2"])

    def test_checks_require_strict_direction(self) -> None:
        summaries = {
            "candidate": {"higher": 2.0, "lower": 1.0},
            "reference": {"higher": 1.0, "lower": 2.0},
        }
        checks = [
            {
                "check_id": "high",
                "bank": "candidate",
                "reference_bank": "reference",
                "coordinate": "higher",
                "direction": "higher",
            },
            {
                "check_id": "low",
                "bank": "candidate",
                "reference_bank": "reference",
                "coordinate": "lower",
                "direction": "lower",
            },
        ]
        self.assertEqual(MODULE.apply_checks(summaries, checks), {"high": True, "low": True})

    def test_invalid_direction_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported direction"):
            MODULE.apply_checks(
                {"a": {"x": 1.0}, "b": {"x": 0.0}},
                [
                    {
                        "check_id": "x",
                        "bank": "a",
                        "reference_bank": "b",
                        "coordinate": "x",
                        "direction": "sideways",
                    }
                ],
            )

    def test_input_validation_binds_both_frozen_view_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = [root / "construction.jsonl", root / "confirmation.jsonl"]
            manifests = [root / "construction.json", root / "confirmation.json"]
            for path in records:
                path.write_text("{}\n")
            for path, seed, records_path in zip(manifests, (11, 13), records, strict=True):
                path.write_text(
                    json.dumps(
                        {
                            "view_seed": seed,
                            "output_sha256": MODULE.file_sha256(records_path),
                            "samples_sha256": "1" * 64,
                            "scores_sha256": "2" * 64,
                        }
                    )
                )
            measurement = {"sampling": {"construction_view_seed": 11}}
            bank = {
                "confirmation_rule": {
                    "construction_view_seed": 11,
                    "confirmation_view_seed": 13,
                }
            }
            prospective = {
                "construction_view_seed": 11,
                "confirmation_view_seed": 13,
            }
            validated = MODULE.validate_inputs(records, manifests, measurement, bank, prospective)
            self.assertEqual([item["view_seed"] for item in validated], [11, 13])
            bank["confirmation_rule"]["confirmation_view_seed"] = 17
            with self.assertRaisesRegex(ValueError, "frozen bank contract"):
                MODULE.validate_inputs(records, manifests, measurement, bank, prospective)


if __name__ == "__main__":
    unittest.main()
