#!/usr/bin/env python3
"""Freeze nested phonon post-training candidates from starting-model measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

BUDGETS = (256, 512, 1024)
ATOM_STRATA = (
    (1, 5),
    (6, 8),
    (9, 10),
    (11, 12),
    (13, 14),
    (15, 16),
    (17, 20),
    (21, 22),
    (23, 24),
    (25, 28),
    (29, 32),
    (33, 36),
    (37, 44),
    (45, 54),
    (55, 72),
    (73, 192),
)
CANDIDATES = ("hash_uniform", "signal", "coverage", "signal_coverage")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def tie_hash(candidate: str, record_id: str) -> str:
    text = f"phonon-candidate-v1|{candidate}|{record_id}"
    return hashlib.sha256(text.encode()).hexdigest()


def atom_stratum(atom_count: int) -> int:
    for index, (lower, upper) in enumerate(ATOM_STRATA):
        if lower <= atom_count <= upper:
            return index
    raise ValueError(f"Atom count {atom_count} lies outside the frozen strata")


def largest_remainder_quotas(counts: list[int], budget: int) -> list[int]:
    if budget <= 0 or budget > sum(counts):
        raise ValueError("Budget must be positive and no larger than the pool")
    raw = [budget * count / sum(counts) for count in counts]
    quotas = [math.floor(value) for value in raw]
    remaining = budget - sum(quotas)
    order = sorted(range(len(counts)), key=lambda index: (-(raw[index] - quotas[index]), index))
    for index in order[:remaining]:
        quotas[index] += 1
    return quotas


def segment_quotas(counts: list[int]) -> list[list[int]]:
    cumulative = [largest_remainder_quotas(counts, budget) for budget in BUDGETS]
    for previous, current in zip(cumulative, cumulative[1:], strict=False):
        if any(after < before for before, after in zip(previous, current, strict=True)):
            raise ValueError("Largest-remainder quotas are not nested for this pool")
    segments = [cumulative[0]]
    for previous, current in zip(cumulative, cumulative[1:], strict=False):
        segments.append([after - before for before, after in zip(previous, current, strict=True)])
    return segments


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    identities = [row["record_id"] for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError(f"Duplicate measurement identities in {path}")
    return rows


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 1.0 if left == right else 0.0
    return numerator / (left_norm * right_norm)


def repeatability_audit(
    full_rows: list[dict[str, Any]], repeated_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    by_id = {row["record_id"]: row for row in full_rows}
    expected = sorted(
        by_id,
        key=lambda record_id: (
            hashlib.sha256(f"repeatability-v1|{record_id}".encode()).hexdigest(),
            record_id,
        ),
    )[:128]
    repeated_ids = [row["record_id"] for row in repeated_rows]
    if set(repeated_ids) != set(expected) or len(repeated_ids) != 128:
        raise ValueError("Repeatability measurement does not contain the frozen 128-record sample")
    repeated_by_id = {row["record_id"]: row for row in repeated_rows}
    signal_differences = []
    embedding_cosines = []
    for record_id in expected:
        first = by_id[record_id]
        second = repeated_by_id[record_id]
        signal_differences.append(
            abs(first["singleton_objective_signal"] - second["singleton_objective_signal"])
        )
        embedding_cosines.append(cosine(first["embedding"], second["embedding"]))
    maximum_signal_difference = max(signal_differences)
    minimum_embedding_cosine = min(embedding_cosines)
    passes = maximum_signal_difference <= 1e-5 and minimum_embedding_cosine >= 0.99999
    return {
        "records": 128,
        "maximum_absolute_signal_difference": maximum_signal_difference,
        "minimum_embedding_cosine_similarity": minimum_embedding_cosine,
        "passes": passes,
    }


def fixed_order(rows: list[dict[str, Any]], *, candidate: str, key) -> list[int]:
    counts = [0] * len(ATOM_STRATA)
    by_stratum: list[list[int]] = [[] for _ in ATOM_STRATA]
    for index, row in enumerate(rows):
        stratum = atom_stratum(int(row["atoms"]))
        counts[stratum] += 1
        by_stratum[stratum].append(index)
    for indexes in by_stratum:
        indexes.sort(
            key=lambda index: (key(rows[index]), tie_hash(candidate, rows[index]["record_id"]))
        )

    result: list[int] = []
    offsets = [0] * len(ATOM_STRATA)
    for quotas in segment_quotas(counts):
        segment = []
        for stratum, quota in enumerate(quotas):
            start = offsets[stratum]
            stop = start + quota
            segment.extend(by_stratum[stratum][start:stop])
            offsets[stratum] = stop
        segment.sort(
            key=lambda index: (key(rows[index]), tie_hash(candidate, rows[index]["record_id"]))
        )
        result.extend(segment)
    return result


def prepare_representation(rows: list[dict[str, Any]]):
    import numpy as np

    embeddings = np.asarray([row["embedding"] for row in rows], dtype=np.float64)
    if embeddings.shape != (7809, 256):
        raise ValueError(f"Expected measurement shape (7809, 256), found {embeddings.shape}")
    centered = embeddings - embeddings.mean(axis=0, keepdims=True)
    _u, singular_values, components = np.linalg.svd(centered, full_matrices=False)
    retained = components[:32]
    scales = singular_values[:32]
    if np.any(scales <= 0):
        raise ValueError("Retained representation components must have positive singular values")
    projected = (centered @ retained.T) / scales.reshape(1, -1)
    norms = np.linalg.norm(projected, axis=1, keepdims=True)
    normalized = projected / np.maximum(norms, 1e-12)
    representation_digest = hashlib.sha256(
        retained.astype("<f8").tobytes() + scales.astype("<f8").tobytes()
    ).hexdigest()
    return normalized, representation_digest


def normalized_signal_percentiles(rows: list[dict[str, Any]]):
    import numpy as np

    order = sorted(
        range(len(rows)),
        key=lambda index: (
            rows[index]["singleton_objective_signal"],
            tie_hash("signal_coverage", rows[index]["record_id"]),
        ),
    )
    percentiles = np.empty(len(rows), dtype=np.float64)
    denominator = max(len(rows) - 1, 1)
    for rank, index in enumerate(order):
        percentiles[index] = rank / denominator
    return percentiles


def adaptive_order(
    rows: list[dict[str, Any]], representation, *, candidate: str, hybrid: bool
) -> list[int]:
    import numpy as np

    counts = [0] * len(ATOM_STRATA)
    strata = np.empty(len(rows), dtype=np.int64)
    for index, row in enumerate(rows):
        strata[index] = atom_stratum(int(row["atoms"]))
        counts[int(strata[index])] += 1
    signal_percentiles = normalized_signal_percentiles(rows)
    centroid = representation.mean(axis=0)
    centroid_distance = np.linalg.norm(representation - centroid, axis=1)
    selected: list[int] = []
    available = np.ones(len(rows), dtype=bool)
    minimum_distance = np.full(len(rows), np.inf, dtype=np.float64)

    for quotas in segment_quotas(counts):
        used = [0] * len(ATOM_STRATA)
        for _ in range(sum(quotas)):
            allowed = available.copy()
            for stratum, quota in enumerate(quotas):
                if used[stratum] >= quota:
                    allowed &= strata != stratum
            indexes = np.flatnonzero(allowed)
            if indexes.size == 0:
                raise ValueError("No records remain under the current stratum quotas")
            if not selected:
                if hybrid:
                    distance = centroid_distance[indexes]
                    distance_range = float(distance.max() - distance.min())
                    normalized_distance = (
                        (distance - distance.min()) / distance_range
                        if distance_range > 0
                        else np.zeros_like(distance)
                    )
                    scores = 0.5 * signal_percentiles[indexes] + 0.5 * normalized_distance
                    best_value = float(scores.max())
                    tied = indexes[np.isclose(scores, best_value, rtol=0.0, atol=1e-15)]
                else:
                    best_value = float(centroid_distance[indexes].min())
                    tied = indexes[
                        np.isclose(centroid_distance[indexes], best_value, rtol=0.0, atol=1e-15)
                    ]
            else:
                distance = minimum_distance[indexes]
                if hybrid:
                    distance_range = float(distance.max() - distance.min())
                    normalized_distance = (
                        (distance - distance.min()) / distance_range
                        if distance_range > 0
                        else np.zeros_like(distance)
                    )
                    scores = 0.5 * signal_percentiles[indexes] + 0.5 * normalized_distance
                    best_value = float(scores.max())
                    tied = indexes[np.isclose(scores, best_value, rtol=0.0, atol=1e-15)]
                else:
                    best_value = float(distance.max())
                    tied = indexes[np.isclose(distance, best_value, rtol=0.0, atol=1e-15)]
            chosen = min(
                tied.tolist(), key=lambda index: tie_hash(candidate, rows[index]["record_id"])
            )
            selected.append(chosen)
            available[chosen] = False
            used[int(strata[chosen])] += 1
            new_distance = np.linalg.norm(representation - representation[chosen], axis=1)
            minimum_distance = np.minimum(minimum_distance, new_distance)
    return selected


def candidate_summary(rows: list[dict[str, Any]], indexes: list[int]) -> dict[str, Any]:
    selected = [rows[index] for index in indexes]
    return {
        "records": len(selected),
        "atoms": sum(int(row["atoms"]) for row in selected),
        "graph_edges": sum(int(row["graph_edges"]) for row in selected),
        "mean_singleton_objective_signal": sum(
            float(row["singleton_objective_signal"]) for row in selected
        )
        / len(selected),
        "unstable_at_minus0p1": sum(float(row["min_frequency"]) <= -0.1 for row in selected),
        "unique_reduced_formulas": len({row["formula_reduced"] for row in selected}),
        "atom_strata": {
            str(index): count
            for index, count in sorted(
                Counter(atom_stratum(int(row["atoms"])) for row in selected).items()
            )
        },
    }


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def freeze(full_path: Path, repeat_path: Path) -> dict[str, Any]:
    protocol_path = Path(__file__).resolve().parents[1] / "PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    rows = read_jsonl(full_path)
    if len(rows) != 7809:
        raise ValueError(f"Expected 7809 full-pool measurements, found {len(rows)}")
    repeated = read_jsonl(repeat_path)
    repeatability = repeatability_audit(rows, repeated)
    if not repeatability["passes"]:
        raise ValueError(f"Repeatability gate failed: {repeatability}")
    representation, representation_digest = prepare_representation(rows)

    orders = {
        "hash_uniform": fixed_order(
            rows,
            candidate="hash_uniform",
            key=lambda row: tie_hash("hash_uniform", row["record_id"]),
        ),
        "signal": fixed_order(
            rows,
            candidate="signal",
            key=lambda row: -float(row["singleton_objective_signal"]),
        ),
        "coverage": adaptive_order(rows, representation, candidate="coverage", hybrid=False),
        "signal_coverage": adaptive_order(
            rows, representation, candidate="signal_coverage", hybrid=True
        ),
    }
    candidates: dict[str, Any] = {}
    for candidate, order in orders.items():
        candidates[candidate] = {}
        for budget in BUDGETS:
            indexes = order[:budget]
            candidates[candidate][str(budget)] = {
                "record_ids": [rows[index]["record_id"] for index in indexes],
                "summary": candidate_summary(rows, indexes),
            }

    cost_audit: dict[str, Any] = {}
    for budget in BUDGETS:
        baseline_atoms = candidates["hash_uniform"][str(budget)]["summary"]["atoms"]
        cost_audit[str(budget)] = {}
        for candidate in CANDIDATES:
            atoms = candidates[candidate][str(budget)]["summary"]["atoms"]
            difference = abs(atoms - baseline_atoms) / baseline_atoms
            cost_audit[str(budget)][candidate] = difference
            if difference > 0.03:
                raise ValueError(
                    "Atom-count difference exceeds 3% for "
                    f"{candidate} at budget {budget}: {difference}"
                )

    overlap_audit: dict[str, Any] = {}
    for budget in BUDGETS:
        overlap_audit[str(budget)] = {}
        for left_index, left in enumerate(CANDIDATES):
            for right in CANDIDATES[left_index + 1 :]:
                value = jaccard(
                    set(candidates[left][str(budget)]["record_ids"]),
                    set(candidates[right][str(budget)]["record_ids"]),
                )
                overlap_audit[str(budget)][f"{left}__{right}"] = value
                if left != "hash_uniform" and right != "hash_uniform" and value > 0.85:
                    raise ValueError(
                        f"Nonbaseline candidate overlap exceeds 0.85 for {left}/{right} at {budget}"
                    )

    payload = {
        "schema_version": "1.0",
        "study": "prospective-phonon-environment-selection",
        "status": "candidates_frozen_outcomes_sealed",
        "protocol_schema_version": protocol["schema_version"],
        "protocol_sha256": canonical_digest(protocol),
        "measurement_sha256": sha256(full_path),
        "repeat_measurement_sha256": sha256(repeat_path),
        "repeatability": repeatability,
        "representation_sha256": representation_digest,
        "candidate_budgets": list(BUDGETS),
        "candidates": candidates,
        "cost_audit": cost_audit,
        "overlap_audit": overlap_audit,
        "prediction": {
            "best_candidate_at_256": "signal_coverage",
            "best_candidate_at_512": "signal_coverage",
            "best_candidate_at_1024": "signal_coverage",
            "complete_ranking": ["signal_coverage", "signal", "coverage", "hash_uniform"],
            "abstention": (
                "Abstain when the predicted utility margin is smaller than "
                "training-seed uncertainty estimated without the prospective external outcomes."
            ),
        },
        "training_seeds": [20261108, 20261109],
        "external_test_labels_inspected": False,
        "candidate_training_outcomes_exist": False,
    }
    payload["freeze_sha256"] = canonical_digest(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--repeat-measurement", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = freeze(args.measurement, args.repeat_measurement)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"freeze_sha256={payload['freeze_sha256']}")


if __name__ == "__main__":
    main()
