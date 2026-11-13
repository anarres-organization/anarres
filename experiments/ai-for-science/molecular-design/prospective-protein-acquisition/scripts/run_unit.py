from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.feature_extraction.text import HashingVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CONTRACT_PATH,
    canonical_json_bytes,
    contract_hashes,
    deterministic_cap,
    load_dataset,
    load_json,
    source_record,
    unit_name,
    verify_source,
)


def stable_seed(*parts: object) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def select_batch(
    strategy: str,
    mean: np.ndarray,
    std: np.ndarray,
    candidates: np.ndarray,
    batch_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if strategy == "random":
        return np.sort(rng.choice(candidates, size=batch_size, replace=False))
    if strategy == "greedy":
        score = mean
    elif strategy == "ucb":
        score = mean + std
    elif strategy == "uncertainty":
        score = std
    elif strategy == "thompson":
        score = rng.normal(mean, std)
    else:
        raise ValueError(strategy)
    order = np.lexsort((candidates, -score))
    return np.sort(candidates[order[:batch_size]])


def normalized_curve_auc(counts: list[int], recalls: list[float]) -> float:
    if len(counts) < 2 or counts[-1] == counts[0]:
        return float(recalls[-1])
    return float(np.trapezoid(recalls, counts) / (counts[-1] - counts[0]))


def run_unit(
    sequences: list[str],
    targets: list[float],
    dataset: str,
    strategy: str,
    seed: int,
) -> dict[str, object]:
    contract = load_json(CONTRACT_PATH)
    source_rows = len(sequences)
    minimum = contract["outcome_blind_support_gate"]["minimum_source_rows"]
    if source_rows < minimum:
        raise ValueError(f"dataset support below gate: {source_rows}")
    cap = contract["outcome_blind_support_gate"]["candidate_cap"]
    sequences, targets, membership_sha256 = deterministic_cap(
        dataset, sequences, targets, min(source_rows, cap)
    )
    y = np.asarray(targets, dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("non-finite target")

    vectorizer = HashingVectorizer(
        analyzer="char",
        ngram_range=(1, 3),
        n_features=256,
        alternate_sign=False,
        norm="l2",
    )
    features = vectorizer.transform(sequences).toarray().astype(np.float32)
    n_rows = len(sequences)
    batch_size = max(4, round(0.01 * n_rows))
    total_batches = (
        contract["budget"]["initial_batches"] + contract["budget"]["acquisition_batches"]
    )
    rng = np.random.default_rng(stable_seed("acquisition", dataset, strategy, seed))
    initial_rng = np.random.default_rng(stable_seed("initial", dataset, seed))
    observed = np.sort(initial_rng.choice(n_rows, size=batch_size, replace=False))

    top_count = max(1, int(np.ceil(contract["evaluation"]["top_fraction"] * n_rows)))
    top_indices = set(np.argsort(-y, kind="stable")[:top_count].tolist())
    counts: list[int] = []
    recalls: list[float] = []
    selection_hashes: list[str] = []

    def record() -> None:
        counts.append(int(len(observed)))
        recalls.append(len(top_indices.intersection(observed.tolist())) / top_count)
        selection_hashes.append(
            hashlib.sha256(",".join(map(str, observed.tolist())).encode()).hexdigest()
        )

    record()
    for round_index in range(1, total_batches):
        remaining = np.setdiff1d(np.arange(n_rows), observed, assume_unique=True)
        take = min(batch_size, len(remaining))
        model = ExtraTreesRegressor(
            n_estimators=32,
            max_features="sqrt",
            min_samples_leaf=2,
            bootstrap=False,
            n_jobs=1,
            random_state=stable_seed("model", dataset, strategy, seed, round_index),
        )
        model.fit(features[observed], y[observed])
        tree_predictions = np.vstack(
            [tree.predict(features[remaining]) for tree in model.estimators_]
        )
        mean = tree_predictions.mean(axis=0)
        std = tree_predictions.std(axis=0, ddof=0)
        chosen = select_batch(strategy, mean, std, remaining, take, rng)
        observed = np.sort(np.concatenate([observed, chosen]))
        record()

    return {
        "schema_version": 1,
        "study_id": contract["study_id"],
        "status": "OUTCOME_BEARING__DO_NOT_OPEN_BEFORE_COMPLETE_GATE",
        "identity": {"dataset": dataset, "strategy": strategy, "seed": seed},
        "contract_hashes": contract_hashes(),
        "source": {
            "filename": source_record(dataset)["filename"],
            "sha256": source_record(dataset)["sha256"],
            "source_rows": source_rows,
            "candidate_rows": n_rows,
            "candidate_membership_sha256": membership_sha256,
        },
        "budget": {
            "batch_size": batch_size,
            "observed_counts": counts,
            "final_fraction": counts[-1] / n_rows,
        },
        "outcome": {
            "top_fraction": contract["evaluation"]["top_fraction"],
            "top_count": top_count,
            "recall_curve": recalls,
            "normalized_curve_auc": normalized_curve_auc(counts, recalls),
            "endpoint_recall": recalls[-1],
        },
        "selection_sha256_by_batch": selection_hashes,
    }


def main() -> None:
    contract = load_json(CONTRACT_PATH)
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset", choices=contract["candidate_datasets"], required=True)
    parser.add_argument("--strategy", choices=sorted(contract["strategies"]), required=True)
    parser.add_argument("--seed", choices=contract["seeds"], type=int, required=True)
    args = parser.parse_args()
    source = verify_source(args.source_dir, args.dataset)
    sequences, targets = load_dataset(source)
    result = run_unit(sequences, targets, args.dataset, args.strategy, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / unit_name(args.dataset, args.strategy, args.seed)
    output.write_bytes(canonical_json_bytes(result))
    print(output)


if __name__ == "__main__":
    main()
