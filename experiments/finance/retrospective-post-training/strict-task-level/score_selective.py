#!/usr/bin/env python3
"""Evaluate source-held-out selective finance environment comparisons."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STRICT_SCORE = HERE / "score.py"
OUT = HERE / "SELECTIVE_SCORE.json"
MANIFEST = HERE / "SELECTIVE_MANIFEST.sha256.json"
TARGET_PRECISIONS = (0.80, 0.85, 0.90)


def load_strict():
    import importlib.util

    specification = importlib.util.spec_from_file_location("finance_strict", STRICT_SCORE)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {STRICT_SCORE}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def pair_records(rows: list[dict], value) -> list[dict]:
    panels: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        panels[(row["source"], row["panel"])].append(row)

    records = []
    for (source, panel), panel_rows in sorted(panels.items()):
        for index, left in enumerate(panel_rows):
            for right in panel_rows[index + 1 :]:
                predicted = value(left) - value(right)
                observed = left["utility"] - right["utility"]
                if predicted == 0 or observed == 0:
                    correct_credit = 0.5
                else:
                    correct_credit = float(predicted * observed > 0)
                records.append(
                    {
                        "source": source,
                        "panel": panel,
                        "margin": abs(predicted),
                        "correct_credit": correct_credit,
                    }
                )
    return records


def choose_threshold(records: list[dict], target_precision: float) -> dict | None:
    best = None
    for threshold in sorted({record["margin"] for record in records}):
        decided = [record for record in records if record["margin"] >= threshold]
        correct_credit = sum(record["correct_credit"] for record in decided)
        precision = correct_credit / len(decided)
        if precision < target_precision:
            continue
        candidate = {
            "threshold": threshold,
            "decided_pairs": len(decided),
            "correct_credit": correct_credit,
            "precision": precision,
        }
        if best is None or (candidate["decided_pairs"], -candidate["threshold"]) > (
            best["decided_pairs"],
            -best["threshold"],
        ):
            best = candidate
    return best


def source_heldout_selective(records: list[dict], target_precision: float) -> dict:
    folds = []
    for source in sorted({record["source"] for record in records}):
        training = [record for record in records if record["source"] != source]
        test = [record for record in records if record["source"] == source]
        calibration = choose_threshold(training, target_precision)
        if calibration is None:
            folds.append(
                {
                    "source": source,
                    "threshold_available": False,
                    "test_pairs": len(test),
                    "decided_pairs": 0,
                    "correct_credit": 0.0,
                }
            )
            continue
        decided = [record for record in test if record["margin"] >= calibration["threshold"]]
        folds.append(
            {
                "source": source,
                "threshold_available": True,
                "threshold": round(calibration["threshold"], 9),
                "training_precision": round(calibration["precision"], 6),
                "training_decided_pairs": calibration["decided_pairs"],
                "test_pairs": len(test),
                "decided_pairs": len(decided),
                "correct_credit": sum(record["correct_credit"] for record in decided),
            }
        )

    decided_pairs = sum(fold["decided_pairs"] for fold in folds)
    correct_credit = sum(fold["correct_credit"] for fold in folds)
    decided_folds = [fold for fold in folds if fold["decided_pairs"] > 0]
    return {
        "target_training_precision": target_precision,
        "heldout_pairs": len(records),
        "decided_pairs": decided_pairs,
        "coverage": round(decided_pairs / len(records), 6),
        "correct_credit": correct_credit,
        "selective_pairwise_accuracy": (
            None if decided_pairs == 0 else round(correct_credit / decided_pairs, 6)
        ),
        "sources_with_decisions": len(decided_folds),
        "source_macro_selective_accuracy": (
            None
            if not decided_folds
            else round(
                sum(fold["correct_credit"] / fold["decided_pairs"] for fold in decided_folds)
                / len(decided_folds),
                6,
            )
        ),
        "folds": folds,
    }


def analyze() -> dict:
    strict = load_strict()
    bridge = strict.load_analysis()
    rows = strict.admitted_rows(bridge)
    rules = {
        "practical_rule": pair_records(rows, bridge.practical_value),
        "more_data": pair_records(rows, lambda row: row["feature_values"]["data_volume"]),
    }
    output_rules = {}
    for name, records in rules.items():
        output_rules[name] = {
            "unfiltered_pairwise_accuracy": round(
                sum(record["correct_credit"] for record in records) / len(records), 6
            ),
            "operating_points": {
                f"target_{target:.2f}": source_heldout_selective(records, target)
                for target in TARGET_PRECISIONS
            },
        }

    return {
        "schema_version": 1,
        "status": "RETROSPECTIVE_SOURCE_HELDOUT_SELECTIVE_AUDIT",
        "support": {
            **strict.support(rows),
            "candidate_pairs": len(rules["practical_rule"]),
        },
        "method": {
            "heldout_unit": "source",
            "confidence": "absolute difference between fixed rule scores",
            "threshold_selection": (
                "maximum training-fold coverage subject to the target training precision"
            ),
            "heldout_outcomes_used_for_threshold": False,
            "tie_credit": 0.5,
        },
        "rules": output_rules,
        "interpretation": (
            "The fixed practical rule supports a higher-precision decide-or-abstain mode. "
            "The source-held-out retrospective audit calibrates the abstention threshold "
            "without using outcomes from the source being scored."
        ),
    }


def main() -> None:
    output = analyze()
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_paths = [
        ROOT / "FEATURE_MAPPING.md",
        ROOT / "data/recovered_panels.json",
        ROOT / "scripts/analyze_expanded_bridge.py",
        STRICT_SCORE,
        Path(__file__),
        OUT,
    ]
    manifest = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in manifest_paths
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
