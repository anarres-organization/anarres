#!/usr/bin/env python3
"""Freeze target-specific materials features without candidate-training outcomes."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import yaml

FORMULA_PATTERN = re.compile(r"([A-Z][a-z]?)([0-9]*)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def formula_counts(formula: str) -> Counter[str]:
    compact_formula = re.sub(r"\s+", "", formula)
    counts = Counter()
    position = 0
    for match in FORMULA_PATTERN.finditer(compact_formula):
        if match.start() != position:
            raise ValueError(f"unsupported reduced formula: {formula}")
        counts[match.group(1)] += int(match.group(2) or 1)
        position = match.end()
    if position != len(compact_formula) or not counts:
        raise ValueError(f"unsupported reduced formula: {formula}")
    return counts


def target_counts(path: Path) -> Counter[str]:
    with bz2.open(path, "rt") as handle:
        payload = yaml.safe_load(handle)
    return Counter(point["symbol"] for point in payload["unit_cell"]["points"])


def normalized(counts: Counter[str]) -> dict[str, float]:
    total = sum(counts.values())
    return {element: count / total for element, count in counts.items()}


def distribution_overlap(left: Counter[str], right: Counter[str]) -> float:
    left_fraction = normalized(left)
    right_fraction = normalized(right)
    return sum(
        min(left_fraction.get(element, 0.0), right_fraction.get(element, 0.0))
        for element in left_fraction.keys() | right_fraction.keys()
    )


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def load_manifest(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != 80000:
        raise ValueError(f"expected 80000 measurement records, found {len(rows)}")
    return rows


def build(
    panel_path: Path,
    roles_path: Path,
    starting_targets_path: Path,
    manifest_path: Path,
    target_yaml_dir: Path,
) -> dict:
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    roles = json.loads(roles_path.read_text(encoding="utf-8"))
    starting = json.loads(starting_targets_path.read_text(encoding="utf-8"))
    manifest = load_manifest(manifest_path)
    starting_by_id = {row["material_id"]: row for row in starting["targets"]}
    target_rows = []
    for role in ("development", "prospective"):
        for material_id in roles["roles"][role]:
            counts = target_counts(target_yaml_dir / f"{material_id}.yaml.bz2")
            baseline = starting_by_id[material_id]
            target_rows.append(
                {
                    "material_id": material_id,
                    "role": role,
                    "counts": counts,
                    "elements": set(counts),
                    "descriptor": {
                        "elements": sorted(counts),
                        "element_count": len(counts),
                        "unitcell_atoms": sum(counts.values()),
                        "starting_frequency_mae_thz": baseline["frequency_mae_thz"],
                        "starting_reference_stable": baseline["reference_stable"],
                        "starting_predicted_stable": baseline["predicted_stable"],
                        "starting_reference_stability_margin_kelvin": baseline[
                            "reference_stability_margin_kelvin"
                        ],
                        "starting_predicted_stability_margin_kelvin": baseline[
                            "predicted_stability_margin_kelvin"
                        ],
                    },
                }
            )

    features = []
    for candidate in panel["candidates"]:
        records = [manifest[index] for index in candidate["record_indices"]]
        record_counts = [formula_counts(row["composition_reduced"]) for row in records]
        candidate_counts = Counter()
        for row, counts in zip(records, record_counts, strict=True):
            multiplier = row["natoms"] / sum(counts.values())
            for element, count in counts.items():
                candidate_counts[element] += count * multiplier
        record_elements = [set(counts) for counts in record_counts]
        for target in target_rows:
            similarities = sorted(
                (jaccard(elements, target["elements"]) for elements in record_elements),
                reverse=True,
            )
            top_count = max(1, math.ceil(0.05 * len(similarities)))
            features.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_role": candidate["role"],
                    "target_material_id": target["material_id"],
                    "target_role": target["role"],
                    "source_family": candidate["candidate_id"].split("__", 1)[0],
                    "selection_rule": candidate["candidate_id"].split("__", 1)[1],
                    "target_descriptor": target["descriptor"],
                    "chemical_support": {
                        "element_distribution_overlap": distribution_overlap(
                            candidate_counts, target["counts"]
                        ),
                        "all_target_elements_present": target["elements"].issubset(
                            candidate_counts
                        ),
                        "record_fraction_containing_all_target_elements": sum(
                            target["elements"].issubset(elements) for elements in record_elements
                        )
                        / len(record_elements),
                    },
                    "nearest_neighbor_affinity": {
                        "mean_element_set_jaccard": sum(similarities) / len(similarities),
                        "top_five_percent_element_set_jaccard": sum(similarities[:top_count])
                        / top_count,
                    },
                }
            )
    return {
        "artifact": "anarres_mlip_target_regression_features_v1",
        "status": "frozen_before_development_outcome_analysis",
        "inputs": {
            "candidate_panel_sha256": sha256(panel_path),
            "target_roles_sha256": sha256(roles_path),
            "starting_checkpoint_targets_sha256": sha256(starting_targets_path),
            "measurement_manifest_sha256": sha256(manifest_path),
        },
        "definitions": {
            "element_distribution_overlap": (
                "Histogram intersection between target unit-cell element fractions and "
                "candidate atom-weighted element fractions."
            ),
            "record_fraction_containing_all_target_elements": (
                "Fraction of candidate configurations whose element set contains every "
                "target element."
            ),
            "top_five_percent_element_set_jaccard": (
                "Mean element-set Jaccard similarity among the closest five percent of "
                "candidate configurations."
            ),
        },
        "counts": {
            "candidates": len(panel["candidates"]),
            "targets": len(target_rows),
            "candidate_target_pairs": len(features),
        },
        "features": features,
        "outcome_boundary": {
            "development_candidate_training_outcomes_used": False,
            "prospective_candidate_training_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--starting-targets", type=Path, required=True)
    parser.add_argument("--measurement-manifest", type=Path, required=True)
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(
        args.panel,
        args.target_roles,
        args.starting_targets,
        args.measurement_manifest,
        args.target_yaml_dir,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
