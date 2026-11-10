#!/usr/bin/env python3
"""Freeze an outcome-blind MLIP panel at matched atom and graph-edge budgets."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

STUDY = Path(__file__).resolve().parent
CONSTRUCTOR_PATH = STUDY / "construct_candidate_bank.py"
SPEC = importlib.util.spec_from_file_location("mlip_candidate_constructor", CONSTRUCTOR_PATH)
assert SPEC is not None
CONSTRUCTOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CONSTRUCTOR)

PANEL_FEATURES = (
    "signal_density_per_atom",
    "effective_signal_coverage",
    "chemical_system_entropy",
    "mean_target_affinity",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_ranked(records: list[dict], rule: str) -> list[dict]:
    ranked = sorted(records, key=lambda row: CONSTRUCTOR.ranking_key(rule, row))
    selected = []
    observed_parents = set()
    for row in ranked:
        if row["parent_id"] in observed_parents:
            continue
        observed_parents.add(row["parent_id"])
        selected.append(row)
    return selected


def select_matched(
    records: list[dict],
    rule: str,
    atom_budget: int,
    edge_budget: int,
    time_limit_seconds: float,
) -> tuple[list[dict], float]:
    """Find an exact cost match in the smallest feasible high-ranked prefix."""

    ranked = unique_ranked(records, rule)
    for fraction in (0.70, 0.80, 0.90, 1.00):
        prefix_count = math.ceil(len(ranked) * fraction)
        prefix = ranked[:prefix_count]
        atoms = np.asarray([row["natoms"] for row in prefix], dtype=float)
        edges = np.asarray([row["neighbor_edges"] for row in prefix], dtype=float)
        if atoms.sum() < atom_budget or edges.sum() < edge_budget:
            continue
        constraints = LinearConstraint(
            csr_matrix(np.vstack([atoms, edges])),
            np.asarray([atom_budget, edge_budget], dtype=float),
            np.asarray([atom_budget, edge_budget], dtype=float),
        )
        result = milp(
            np.zeros(prefix_count),
            integrality=np.ones(prefix_count),
            bounds=Bounds(0.0, 1.0),
            constraints=constraints,
            options={"time_limit": time_limit_seconds},
        )
        if result.x is None:
            continue
        selected = [row for row, value in zip(prefix, result.x, strict=True) if value > 0.5]
        if sum(row["natoms"] for row in selected) != atom_budget:
            raise AssertionError("cost-matched candidate has the wrong atom budget")
        if sum(row["neighbor_edges"] for row in selected) != edge_budget:
            raise AssertionError("cost-matched candidate has the wrong neighbor-edge budget")
        if len({row["parent_id"] for row in selected}) != len(selected):
            raise AssertionError("cost-matched candidate repeats a parent")
        return selected, fraction
    raise RuntimeError(f"{rule} has no exact cost match in the ranked record support")


def standardized_features(candidates: list[dict]) -> dict[str, np.ndarray]:
    matrix = np.asarray(
        [
            [
                math.log(candidate["signal_density_per_atom"]),
                candidate["effective_signal_coverage"],
                candidate["chemical_system_entropy"],
                candidate["mean_target_affinity"],
            ]
            for candidate in candidates
        ],
        dtype=float,
    )
    means = matrix.mean(axis=0)
    scales = matrix.std(axis=0)
    if np.any(scales == 0):
        raise ValueError("panel feature has zero variance")
    normalized = (matrix - means) / scales
    return {
        candidate["candidate_id"]: row
        for candidate, row in zip(candidates, normalized, strict=True)
    }


def jaccard(first: dict, second: dict) -> float:
    left = set(first["record_indices"])
    right = set(second["record_indices"])
    return len(left & right) / len(left | right)


def choose_panel(candidates: list[dict]) -> list[dict]:
    """Choose two candidates per source with balanced selector representation."""

    by_source: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        source, _ = candidate["candidate_id"].rsplit("__", 1)
        by_source[source].append(candidate)
    if len(by_source) != 8 or any(len(values) != 6 for values in by_source.values()):
        raise ValueError("panel selection expects eight sources and six selectors per source")

    features = standardized_features(candidates)
    options = []
    for source in sorted(by_source):
        ordered = sorted(by_source[source], key=lambda candidate: candidate["candidate_id"])
        for first, second in itertools.combinations(ordered, 2):
            first_rule = first["candidate_id"].rsplit("__", 1)[1]
            second_rule = second["candidate_id"].rsplit("__", 1)[1]
            distance = float(
                np.linalg.norm(features[first["candidate_id"]] - features[second["candidate_id"]])
            )
            overlap = jaccard(first, second)
            options.append(
                {
                    "source": source,
                    "first": first,
                    "second": second,
                    "rules": (first_rule, second_rule),
                    "distance": distance,
                    "overlap": overlap,
                }
            )

    sources = sorted(by_source)
    rules = list(CONSTRUCTOR.SELECTION_RULES)
    variables = len(options)
    objective = np.asarray(
        [-(option["distance"] - option["overlap"]) for option in options], dtype=float
    )
    rows = []
    lower = []
    upper = []
    for source in sources:
        rows.append([1.0 if option["source"] == source else 0.0 for option in options])
        lower.append(1.0)
        upper.append(1.0)
    for rule in rules:
        rows.append([float(option["rules"].count(rule)) for option in options])
        lower.append(2.0)
        upper.append(3.0)
    result = milp(
        objective,
        integrality=np.ones(variables),
        bounds=Bounds(0.0, 1.0),
        constraints=LinearConstraint(csr_matrix(np.asarray(rows)), lower, upper),
        options={"mip_rel_gap": 0.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"final panel selection failed: {result.message}")
    selected = []
    for option, value in zip(options, result.x, strict=True):
        if value > 0.5:
            selected.extend([option["first"], option["second"]])
    return sorted(selected, key=lambda candidate: candidate["candidate_id"])


def choose_prospective(panel: list[dict], count: int = 4) -> set[str]:
    """Choose a source-disjoint, selector-disjoint maximin prospective subset."""

    features = standardized_features(panel)
    best: tuple[tuple[float, float, str], set[str]] | None = None
    for subset in itertools.combinations(panel, count):
        sources = [candidate["candidate_id"].rsplit("__", 1)[0] for candidate in subset]
        rules = [candidate["candidate_id"].rsplit("__", 1)[1] for candidate in subset]
        if len(set(sources)) != count or len(set(rules)) != count:
            continue
        distances = [
            float(
                np.linalg.norm(features[first["candidate_id"]] - features[second["candidate_id"]])
            )
            for first, second in itertools.combinations(subset, 2)
        ]
        identifiers = sorted(candidate["candidate_id"] for candidate in subset)
        tie = hashlib.sha256("\n".join(identifiers).encode()).hexdigest()
        score = (min(distances), sum(distances), tie)
        if best is None or score > best[0]:
            best = (score, set(identifiers))
    if best is None:
        raise RuntimeError("no valid prospective split was found")
    return best[1]


def construct(
    manifest_path: Path,
    measurement_paths: list[Path],
    target_roles_path: Path,
    target_yaml_dir: Path,
    atom_budget: int,
    edge_budget: int,
    time_limit_seconds: float,
) -> dict:
    targets = CONSTRUCTOR.target_element_sets(
        target_roles_path, target_yaml_dir, "checkpoint_qualification"
    )
    records = CONSTRUCTOR.load_records(manifest_path, measurement_paths)
    families: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        families[row["source_family"]].append(row)

    candidates = []
    for family in sorted(families):
        family_records = families[family]
        CONSTRUCTOR.score_family(family_records, targets)
        for rule in CONSTRUCTOR.SELECTION_RULES:
            selected, prefix_fraction = select_matched(
                family_records,
                rule,
                atom_budget,
                edge_budget,
                time_limit_seconds,
            )
            candidate = CONSTRUCTOR.summarize_candidate(f"{family}__{rule}", selected)
            candidate["ranked_prefix_fraction"] = prefix_fraction
            candidates.append(candidate)

    panel = choose_panel(candidates)
    prospective = choose_prospective(panel)
    for candidate in panel:
        candidate["role"] = (
            "prospective" if candidate["candidate_id"] in prospective else "development"
        )
    roles = {
        role: sorted(candidate["candidate_id"] for candidate in panel if candidate["role"] == role)
        for role in ("development", "prospective")
    }
    role_hashes = {
        role: hashlib.sha256(("\n".join(values) + "\n").encode()).hexdigest()
        for role, values in roles.items()
    }
    source_counts = Counter(c["candidate_id"].rsplit("__", 1)[0] for c in panel)
    rule_counts = Counter(c["candidate_id"].rsplit("__", 1)[1] for c in panel)
    overlaps = [
        jaccard(first, second)
        for first, second in itertools.combinations(panel, 2)
        if first["candidate_id"].rsplit("__", 1)[0] == second["candidate_id"].rsplit("__", 1)[0]
    ]
    return {
        "artifact": "anarres_mlip_cost_matched_panel_v1",
        "status": "frozen_pretraining__candidate_outcomes_sealed",
        "inputs": {
            "manifest_sha256": sha256(manifest_path),
            "measurement_sha256": {path.name: sha256(path) for path in measurement_paths},
            "target_roles_sha256": sha256(target_roles_path),
            "target_yaml_sha256": {
                path.name: sha256(path) for path in sorted(target_yaml_dir.glob("*.yaml.bz2"))
            },
        },
        "construction": {
            "atom_budget_per_candidate": atom_budget,
            "neighbor_edge_budget_per_candidate": edge_budget,
            "maximum_records_per_parent": 1,
            "source_families": sorted(families),
            "selection_rules": list(CONSTRUCTOR.SELECTION_RULES),
            "panel_candidates_per_source": 2,
            "selector_count_bounds": [2, 3],
            "prospective_candidates": 4,
            "solver": f"scipy.optimize.milp {scipy.__version__}",
            "cost_matching_rule": "smallest_feasible_high_ranked_prefix",
            "uses_candidate_training_outcomes": False,
            "uses_development_or_prospective_target_outcomes": False,
        },
        "panel_audit": {
            "candidate_count": len(panel),
            "role_counts": {role: len(values) for role, values in roles.items()},
            "source_counts": dict(sorted(source_counts.items())),
            "selector_counts": dict(sorted(rule_counts.items())),
            "maximum_within_source_jaccard_overlap": max(overlaps),
            "role_hashes": role_hashes,
        },
        "candidates": panel,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, nargs="+", required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--atom-budget", type=int, default=50_000)
    parser.add_argument("--edge-budget", type=int, default=2_100_000)
    parser.add_argument("--time-limit-seconds", type=float, default=60.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = construct(
        args.manifest,
        sorted(args.measurements),
        args.target_roles,
        args.target_yaml_dir,
        args.atom_budget,
        args.edge_budget,
        args.time_limit_seconds,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["panel_audit"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
