#!/usr/bin/env python3
"""Normalize the Reisman target-specific acquisition archive.

The source is a pinned pickle archive. This script verifies its SHA-256 digest
before deserializing any member. Run it only with the released artifact listed
in SOURCES.json.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import pickle
import zipfile
from pathlib import Path
from statistics import mean
from typing import Any

EXPECTED_SHA256 = "ffc73a3104a2a35b25f21ae9e944d186f4962a5d2c3ac673d2e10da8deaf0192"
METHODS = (
    "random",
    "acqf_1-db0-01-a1",
    "acqf_10",
    "acqf_2-1",
    "acqf_3",
    "acqf_4-1",
    "acqf_5",
    "acqf_6",
    "acqf_7",
    "acqf_9",
)
NEIGHBOR_COUNTS = (1, 3, 5, 10, 20)
SIMILARITY_POWERS = (1, 2, 4)
SUFFIX = "_1_coldstart_custom.pkl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_identity(name: str) -> tuple[str, str, int] | None:
    prefix = "clean_run/res_rf_"
    if not name.startswith(prefix) or not name.endswith(SUFFIX):
        return None
    stem = name[len(prefix) : -len(SUFFIX)]
    for method in sorted(METHODS, key=len, reverse=True):
        marker = f"_{method}_"
        if marker not in stem:
            continue
        target, run = stem.rsplit(marker, maxsplit=1)
        if run.isdigit():
            return target, method, int(run)
    return None


def stable_index(curve: list[float], threshold: float = 0.9, duration: int = 10) -> int:
    count = 0
    for index, value in enumerate(curve):
        count = count + 1 if value >= threshold else 0
        if count == duration:
            return index
    return len(curve)


def load_curves(archive: Path) -> dict[tuple[str, str], list[tuple[int, list[float]]]]:
    curves: dict[tuple[str, str], list[tuple[int, list[float]]]] = collections.defaultdict(list)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            identity = parse_identity(member.filename)
            if identity is None:
                continue
            target, method, run = identity
            payload = pickle.loads(source.read(member))  # noqa: S301 - digest-pinned primary artifact
            curve = [float(values[0]) for values in payload[0][0]]
            curves[(target, method)].append((run, curve))
    return curves


def fingerprint_support() -> tuple[Any, Any, str]:
    try:
        import rdkit
        from rdkit import Chem, DataStructs
        from rdkit.Chem import rdFingerprintGenerator
    except ImportError as error:
        raise SystemExit(
            "RDKit is required for the structural nearest-target audit. "
            "Install the study dependency before running this normalizer."
        ) from error
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=512)
    return (Chem, DataStructs, generator), rdkit, rdkit.__version__


def aggregate(
    curves: dict[tuple[str, str], list[tuple[int, list[float]]]],
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    (chem, _, generator), _, rdkit_version = fingerprint_support()
    records = []
    fingerprints = {}
    for (target, method), runs in sorted(curves.items()):
        molecule = chem.MolFromSmiles(target)
        if molecule is None:
            raise ValueError(f"invalid target SMILES in released archive: {target}")
        canonical = chem.MolToSmiles(molecule)
        fingerprints[canonical] = generator.GetFingerprint(molecule)
        length = min(len(curve) for _, curve in runs)
        average = [mean(curve[index] for _, curve in runs) for index in range(length)]
        area = sum((average[index] + average[index + 1]) / 2 for index in range(length - 1))
        records.append(
            {
                "target_smiles": canonical,
                "method": method,
                "released_repetitions": len(runs),
                "missing_run_ids": sorted(set(range(1, 31)).difference(run for run, _ in runs)),
                "curve_steps": length,
                "stable_top1_index": stable_index(average),
                "top1_auc": area / max(1, length - 1),
            }
        )
    return records, fingerprints, rdkit_version


def add_utilities(records: list[dict[str, Any]], metric: str) -> None:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in records:
        grouped[row["target_smiles"]].append(row)
    for rows in grouped.values():
        values = [
            -float(row["stable_top1_index"]) if metric == "stable_top1" else float(row["top1_auc"])
            for row in rows
        ]
        low = min(values)
        high = max(values)
        for row, value in zip(rows, values, strict=True):
            row[f"{metric}_utility"] = (value - low) / (high - low) if high > low else 0.5


def decision_metrics(
    records: list[dict[str, Any]], predictions: dict[tuple[str, str], float], metric: str
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in records:
        grouped[row["target_smiles"]].append(row)
    credits = []
    regrets = []
    selections = []
    utility_key = f"{metric}_utility"
    for target, rows in sorted(grouped.items()):
        for left, right in itertools.combinations(rows, 2):
            observed = float(left[utility_key]) - float(right[utility_key])
            predicted = (
                predictions[(target, left["method"])] - predictions[(target, right["method"])]
            )
            if observed == 0 or predicted == 0:
                credits.append(0.5)
            else:
                credits.append(float(observed * predicted > 0))
        selected = max(
            rows,
            key=lambda row: (predictions[(target, row["method"])], row["method"]),
        )
        best = max(float(row[utility_key]) for row in rows)
        regret = best - float(selected[utility_key])
        regrets.append(regret)
        selections.append(
            {
                "target_smiles": target,
                "selected_method": selected["method"],
                "observed_best_methods": sorted(
                    row["method"] for row in rows if float(row[utility_key]) == best
                ),
                "normalized_regret": regret,
            }
        )
    return {
        "pairwise_ordering": mean(credits),
        "mean_normalized_regret": mean(regrets),
        "best_method_credit": mean(
            float(row["selected_method"] in row["observed_best_methods"]) for row in selections
        ),
        "targets": len(selections),
        "selected_method_counts": dict(
            sorted(collections.Counter(row["selected_method"] for row in selections).items())
        ),
        "selections": selections,
    }


def evaluate(
    records: list[dict[str, Any]], fingerprints: dict[str, Any], metric: str
) -> dict[str, Any]:
    _, data_structs, _ = fingerprint_support()[0]
    targets = sorted(fingerprints)
    utility_key = f"{metric}_utility"
    fixed_predictions = {}
    structural_predictions = {}
    neighbors = {}
    for target in targets:
        train = [row for row in records if row["target_smiles"] != target]
        priors = {
            method: mean(float(row[utility_key]) for row in train if row["method"] == method)
            for method in METHODS
        }
        similarity, neighbor = max(
            (
                data_structs.TanimotoSimilarity(fingerprints[target], fingerprints[candidate]),
                candidate,
            )
            for candidate in targets
            if candidate != target
        )
        neighbor_utilities = {
            row["method"]: float(row[utility_key])
            for row in records
            if row["target_smiles"] == neighbor
        }
        neighbors[target] = {"target_smiles": neighbor, "tanimoto_similarity": similarity}
        for method in METHODS:
            fixed_predictions[(target, method)] = priors[method]
            structural_predictions[(target, method)] = neighbor_utilities[method]
    return {
        "training_fold_fixed_method": decision_metrics(records, fixed_predictions, metric),
        "structural_nearest_target": decision_metrics(records, structural_predictions, metric),
        "nearest_target_by_smiles": neighbors,
    }


def similarity_weighted_predictions(
    records: list[dict[str, Any]],
    target: str,
    candidate_targets: list[str],
    fingerprints: dict[str, Any],
    data_structs: Any,
    metric: str,
    neighbor_count: int,
    similarity_power: int,
) -> dict[tuple[str, str], float]:
    utility_key = f"{metric}_utility"
    ordered = sorted(
        (
            data_structs.TanimotoSimilarity(fingerprints[target], fingerprints[candidate]),
            candidate,
        )
        for candidate in candidate_targets
    )
    neighbors = ordered[-min(neighbor_count, len(ordered)) :]
    weights = [max(similarity, 1e-12) ** similarity_power for similarity, _ in neighbors]
    predictions = {}
    for method in METHODS:
        values = {
            row["target_smiles"]: float(row[utility_key])
            for row in records
            if row["method"] == method
        }
        predictions[(target, method)] = sum(
            weight * values[neighbor]
            for weight, (_, neighbor) in zip(weights, neighbors, strict=True)
        ) / sum(weights)
    return predictions


def nested_similarity_audit(
    records: list[dict[str, Any]], fingerprints: dict[str, Any], metric: str
) -> dict[str, Any]:
    _, data_structs, _ = fingerprint_support()[0]
    targets = sorted(fingerprints)
    outer_predictions = {}
    chosen = {}
    for held_out in targets:
        training_targets = [target for target in targets if target != held_out]
        candidates = []
        for neighbor_count in NEIGHBOR_COUNTS:
            for similarity_power in SIMILARITY_POWERS:
                inner_predictions = {}
                for validation in training_targets:
                    inner_predictions.update(
                        similarity_weighted_predictions(
                            records,
                            validation,
                            [target for target in training_targets if target != validation],
                            fingerprints,
                            data_structs,
                            metric,
                            neighbor_count,
                            similarity_power,
                        )
                    )
                inner_records = [row for row in records if row["target_smiles"] in training_targets]
                inner = decision_metrics(inner_records, inner_predictions, metric)
                candidates.append(
                    (
                        inner["mean_normalized_regret"],
                        -inner["pairwise_ordering"],
                        neighbor_count,
                        similarity_power,
                    )
                )
        _, _, neighbor_count, similarity_power = min(candidates)
        chosen[held_out] = {
            "neighbor_count": neighbor_count,
            "similarity_power": similarity_power,
        }
        outer_predictions.update(
            similarity_weighted_predictions(
                records,
                held_out,
                training_targets,
                fingerprints,
                data_structs,
                metric,
                neighbor_count,
                similarity_power,
            )
        )
    result = decision_metrics(records, outer_predictions, metric)
    result["selection_contract"] = {
        "outer_holdout": "one complete target",
        "inner_holdout": "one complete target from the outer training fold",
        "primary_tuning_metric": "mean_normalized_regret",
        "tie_breaker": "pairwise_ordering",
        "neighbor_counts": list(NEIGHBOR_COUNTS),
        "similarity_powers": list(SIMILARITY_POWERS),
    }
    result["chosen_hyperparameters_by_target"] = chosen
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest = sha256(args.archive)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"source archive digest mismatch: {digest}")

    curves = load_curves(args.archive)
    records, fingerprints, rdkit_version = aggregate(curves)
    if len(fingerprints) != 50 or len(records) != 500:
        raise ValueError(
            "released panel does not contain the expected 50 targets and 500 conditions"
        )
    for metric in ("stable_top1", "top1_auc"):
        add_utilities(records, metric)
    output = {
        "schema_version": "anarres.molecular.reisman_regioselectivity_bridge.v1",
        "study": (
            "Designing Target-specific Data Sets for Regioselectivity Predictions "
            "on Complex Substrates"
        ),
        "evidence_tier": "retrospective_leave_one_target_out_decision_audit",
        "claim_boundary": (
            "The audit uses released simulated acquisition trajectories and outcomes from other "
            "targets. It is not a prospective wet-lab test or a pre-training "
            "RxnFlow profile result."
        ),
        "source_sha256": digest,
        "fingerprint_contract": {
            "implementation": "RDKit Morgan fingerprint",
            "radius": 2,
            "bits": 512,
            "similarity": "Tanimoto",
            "rdkit_version": rdkit_version,
        },
        "support": {
            "targets": len(fingerprints),
            "acquisition_methods": list(METHODS),
            "conditions": len(records),
            "released_runs": sum(row["released_repetitions"] for row in records),
            "conditions_with_30_runs": sum(row["released_repetitions"] == 30 for row in records),
            "conditions_with_29_runs": sum(row["released_repetitions"] == 29 for row in records),
        },
        "stable_top1_decision_audit": {
            **evaluate(records, fingerprints, "stable_top1"),
            "nested_similarity_weighted": nested_similarity_audit(
                records, fingerprints, "stable_top1"
            ),
        },
        "top1_auc_sensitivity": {
            **evaluate(records, fingerprints, "top1_auc"),
            "nested_similarity_weighted": nested_similarity_audit(
                records, fingerprints, "top1_auc"
            ),
        },
        "condition_records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
