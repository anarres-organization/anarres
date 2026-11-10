#!/usr/bin/env python3
"""Score the sealed Square decision and regression predictions after release."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    result = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and values[order[stop]] == values[order[start]]:
            stop += 1
        result[order[start:stop]] = (start + stop - 1) / 2.0
        start = stop
    return result


def spearman(left: np.ndarray, right: np.ndarray) -> float:
    left_rank = ranks(left)
    right_rank = ranks(right)
    if np.std(left_rank) == 0 or np.std(right_rank) == 0:
        return float("nan")
    return float(np.corrcoef(left_rank, right_rank)[0, 1])


def read_evaluation(path: Path, protocol: dict) -> dict:
    blob = json.loads(path.read_text(encoding="utf-8"))
    if blob.get("study_id") != protocol["study_id"]:
        raise ValueError(f"{path} belongs to a different study")
    expected = {
        (state_id, replicate)
        for state_id in range(protocol["evaluation"]["states"])
        for replicate in range(protocol["evaluation"]["rollout_replicates_per_state"])
    }
    observed = {(row["state_id"], row["replicate"]) for row in blob["records"]}
    if observed != expected or len(blob["records"]) != len(expected):
        raise ValueError(f"{path} does not cover the frozen state-replicate matrix")
    if any(row["exception"] is not None for row in blob["records"]):
        raise ValueError(f"{path} contains simulator exceptions")
    return blob


def state_success(blob: dict, states: int) -> np.ndarray:
    values = [[] for _ in range(states)]
    for row in blob["records"]:
        values[row["state_id"]].append(float(row["success"]))
    return np.asarray([np.mean(row) for row in values], dtype=np.float64)


def percentile_interval(values: np.ndarray) -> list[float]:
    return [float(value) for value in np.percentile(values, [2.5, 97.5])]


def regression_rows(
    candidate_state: dict[str, np.ndarray],
    probe_state: np.ndarray,
    candidates: dict,
    state_strata: np.ndarray,
    candidate_ids: list[str],
) -> list[dict]:
    rows = []
    for candidate_id in candidate_ids:
        risks = np.asarray(
            [row["regression_risk"] for row in candidates["state_regression_risk"][candidate_id]],
            dtype=np.float64,
        )
        for stratum in sorted(set(state_strata.tolist())):
            mask = state_strata == stratum
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "stratum": int(stratum),
                    "frozen_risk": float(np.mean(risks[mask])),
                    "candidate_success": float(np.mean(candidate_state[candidate_id][:, mask])),
                    "probe_success": float(np.mean(probe_state[:, mask])),
                    "observed_change": float(
                        np.mean(candidate_state[candidate_id][:, mask])
                        - np.mean(probe_state[:, mask])
                    ),
                }
            )
    return rows


def summarize_regression(rows: list[dict], tail_rows: int) -> dict:
    risks = np.asarray([row["frozen_risk"] for row in rows])
    changes = np.asarray([row["observed_change"] for row in rows])
    ordered = sorted(
        rows, key=lambda row: (row["frozen_risk"], row["candidate_id"], row["stratum"])
    )
    low = ordered[:tail_rows]
    high = ordered[-tail_rows:]
    return {
        "spearman_risk_vs_success_change": spearman(risks, changes),
        "high_minus_low_risk_success_change": float(
            np.mean([row["observed_change"] for row in high])
            - np.mean([row["observed_change"] for row in low])
        ),
        "low_risk_rows": [
            {"candidate_id": row["candidate_id"], "stratum": row["stratum"]} for row in low
        ],
        "high_risk_rows": [
            {"candidate_id": row["candidate_id"], "stratum": row["stratum"]} for row in high
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-evaluations", nargs=15, type=Path, required=True)
    parser.add_argument("--probe-evaluations", nargs=3, type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--scoring-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    scoring = json.loads(args.scoring_contract.read_text(encoding="utf-8"))
    if scoring.get("candidate_outcomes_opened") is not False:
        raise ValueError("scoring contract was not frozen before candidate outcomes")
    bound = scoring["bound_inputs"]
    if sha256(args.protocol) != bound["PROTOCOL.json"]:
        raise ValueError("protocol differs from the scoring freeze")
    if sha256(Path(__file__)) != bound["scripts/score_candidate_results.py"]:
        raise ValueError("scoring implementation differs from the scoring freeze")
    if (
        scoring["study_id"] != protocol["study_id"]
        or candidates["study_id"] != protocol["study_id"]
    ):
        raise ValueError("study identities do not match")

    candidate_blobs = [read_evaluation(path, protocol) for path in args.candidate_evaluations]
    probe_blobs = [read_evaluation(path, protocol) for path in args.probe_evaluations]
    candidate_ids = [arm for arm in scoring["comparison_arms"] if arm != "all_data_reference"]
    expected_candidate_pairs = {
        (candidate_id, seed)
        for candidate_id in candidate_ids
        for seed in protocol["training"]["candidate_seeds"]
    }
    observed_candidate_pairs = {
        (blob["policy_id"], blob["training_seed"]) for blob in candidate_blobs
    }
    if observed_candidate_pairs != expected_candidate_pairs:
        raise ValueError("candidate evaluations do not match the frozen arm-seed matrix")
    expected_probe_seeds = set(protocol["measurement"]["probe_policy_training_seeds"])
    if {blob["training_seed"] for blob in probe_blobs} != expected_probe_seeds:
        raise ValueError("probe evaluations do not match the frozen seed matrix")
    if any(blob["policy_id"] != "all_data_probe" for blob in probe_blobs):
        raise ValueError("probe evaluation has the wrong policy identity")
    checkpoints = {blob["checkpoint_sha256"] for blob in candidate_blobs + probe_blobs}
    if len(checkpoints) != len(candidate_blobs) + len(probe_blobs):
        raise ValueError("every policy must use a distinct final checkpoint")

    states = protocol["evaluation"]["states"]
    candidate_seeds = protocol["training"]["candidate_seeds"]
    probe_seeds = protocol["measurement"]["probe_policy_training_seeds"]
    by_candidate = {(blob["policy_id"], blob["training_seed"]): blob for blob in candidate_blobs}
    by_probe = {blob["training_seed"]: blob for blob in probe_blobs}
    candidate_state = {
        candidate_id: np.stack(
            [state_success(by_candidate[(candidate_id, seed)], states) for seed in candidate_seeds]
        )
        for candidate_id in candidate_ids
    }
    probe_state = np.stack([state_success(by_probe[seed], states) for seed in probe_seeds])
    arm_seed_rates = {
        "all_data_reference": np.mean(probe_state, axis=1),
        **{
            candidate_id: np.mean(values, axis=1)
            for candidate_id, values in candidate_state.items()
        },
    }
    arm_means = {arm: float(np.mean(values)) for arm, values in arm_seed_rates.items()}
    predicted = scoring["point_prediction"]
    regret = max(arm_means.values()) - arm_means[predicted]
    pairwise = [
        {
            "left": left,
            "right": right,
            "mean_difference": arm_means[left] - arm_means[right],
        }
        for left, right in combinations(scoring["comparison_arms"], 2)
    ]

    state_strata = np.asarray(
        [row["stratum"] for row in candidates["state_regression_risk"][candidate_ids[0]]],
        dtype=np.int64,
    )
    rows = regression_rows(candidate_state, probe_state, candidates, state_strata, candidate_ids)
    tail_rows = len(rows) // 4
    regression = summarize_regression(rows, tail_rows)

    bootstrap = scoring["uncertainty"]
    rng = np.random.default_rng(bootstrap["random_seed"])
    regrets = np.empty(bootstrap["resamples"])
    correlations = np.empty(bootstrap["resamples"])
    tail_contrasts = np.empty(bootstrap["resamples"])
    for index in range(bootstrap["resamples"]):
        candidate_indices = rng.integers(0, len(candidate_seeds), len(candidate_seeds))
        probe_indices = rng.integers(0, len(probe_seeds), len(probe_seeds))
        resampled_candidates = {
            candidate_id: values[candidate_indices]
            for candidate_id, values in candidate_state.items()
        }
        resampled_probe = probe_state[probe_indices]
        means = {
            "all_data_reference": float(np.mean(resampled_probe)),
            **{
                candidate_id: float(np.mean(values))
                for candidate_id, values in resampled_candidates.items()
            },
        }
        regrets[index] = max(means.values()) - means[predicted]
        sampled_rows = regression_rows(
            resampled_candidates, resampled_probe, candidates, state_strata, candidate_ids
        )
        sampled_summary = summarize_regression(sampled_rows, tail_rows)
        correlations[index] = sampled_summary["spearman_risk_vs_success_change"]
        tail_contrasts[index] = sampled_summary["high_minus_low_risk_success_change"]

    result = {
        "schema_version": "anarres.robotics-square-results.v1",
        "study_id": protocol["study_id"],
        "status": "CANDIDATE_OUTCOMES_RELEASED_AND_SCORED",
        "candidate_outcomes_opened": True,
        "arm_seed_success_rates": {
            arm: [float(value) for value in values] for arm, values in arm_seed_rates.items()
        },
        "arm_mean_success_rates": arm_means,
        "observed_best_arm": max(arm_means, key=arm_means.get),
        "point_prediction": predicted,
        "allocation_regret": float(regret),
        "allocation_regret_95_interval": percentile_interval(regrets),
        "pairwise_arm_differences": pairwise,
        "candidate_by_stratum": rows,
        "regression": {
            **regression,
            "spearman_95_interval": percentile_interval(correlations[~np.isnan(correlations)]),
            "tail_contrast_95_interval": percentile_interval(tail_contrasts),
        },
        "inputs": {
            "protocol_sha256": sha256(args.protocol),
            "candidates_sha256": sha256(args.candidates),
            "scoring_contract_sha256": sha256(args.scoring_contract),
            "candidate_evaluations": {
                path.name: sha256(path) for path in args.candidate_evaluations
            },
            "probe_evaluations": {path.name: sha256(path) for path in args.probe_evaluations},
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "observed_best_arm": result["observed_best_arm"],
                "point_prediction": predicted,
                "allocation_regret": result["allocation_regret"],
                "regression": result["regression"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
