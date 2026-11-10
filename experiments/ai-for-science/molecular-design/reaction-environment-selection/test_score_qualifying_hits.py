from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "score_qualifying_hits.py"
SPEC = importlib.util.spec_from_file_location("score_qualifying_hits", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def thresholds(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "contract": "q07820-qualifying-hit-v1",
                "instantiated_thresholds": {
                    "vina_affinity_maximum": -8.0,
                    "qed_strictly_greater_than": 0.5,
                    "synthetic_accessibility_strictly_less_than": 5.0,
                    "strain_energy_maximum": 10.0,
                    "clash_score_maximum": 2.0,
                    "interaction_score_minimum": 0.6,
                },
            }
        )
    )


def record(attempt_id: str, **updates: object) -> dict[str, object]:
    result: dict[str, object] = {
        "attempt_id": attempt_id,
        "canonical_smiles": "CCO",
        "infrastructure_status": "ok",
        "valid": True,
        "vina_affinity": -9.0,
        "qed": 0.6,
        "synthetic_accessibility": 4.0,
        "chemical_filters_pass": True,
        "posebusters_all_valid": True,
        "strain_energy": 9.0,
        "clash_score": 1.0,
        "interaction_score": 0.7,
    }
    result.update(updates)
    return result


def write_records(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(item) + "\n" for item in records))


def test_counts_unique_hits_over_all_attempts(tmp_path: Path) -> None:
    threshold_path = tmp_path / "thresholds.json"
    records_path = tmp_path / "records.jsonl"
    thresholds(threshold_path)
    write_records(
        records_path,
        [
            record("a"),
            record("b"),
            record("c", canonical_smiles="CCC", qed=0.5),
            record("d", canonical_smiles="CCN", strain_energy=None),
            record("e", canonical_smiles=""),
        ],
    )

    result = MODULE.score(records_path, threshold_path)

    assert result["status"] == "complete"
    assert result["qualifying_attempts"] == 2
    assert result["unique_qualifying_molecules"] == 1
    assert result["unique_qualifying_hit_rate"] == 0.2
    assert result["failed_gate_counts"]["qed"] == 1
    assert result["failed_gate_counts"]["strain_energy"] == 1
    assert result["failed_gate_counts"]["valid"] == 1


def test_infrastructure_failure_invalidates_panel(tmp_path: Path) -> None:
    threshold_path = tmp_path / "thresholds.json"
    records_path = tmp_path / "records.jsonl"
    thresholds(threshold_path)
    write_records(records_path, [record("a", infrastructure_status="timeout")])

    result = MODULE.score(records_path, threshold_path)

    assert result["status"] == "invalid_infrastructure_failure"
    assert result["infrastructure_failures"] == 1
    assert result["qualifying_attempts"] is None
    assert result["unique_qualifying_molecules"] is None
    assert result["unique_qualifying_hit_rate"] is None
