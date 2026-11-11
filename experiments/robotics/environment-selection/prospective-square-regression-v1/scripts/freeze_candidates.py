#!/usr/bin/env python3
"""Freeze Square candidate memberships from a qualified probe-policy failure map."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np

TIERS = ("better", "okay", "worse")


def demo_number(name: str) -> int:
    return int(name.rsplit("_", 1)[1])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode(values) -> list[str]:
    return [value.decode() if isinstance(value, bytes) else str(value) for value in values]


def membership_hash(names: list[str]) -> str:
    payload = "\n".join(sorted(names, key=demo_number)) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def pose_feature(pose: np.ndarray) -> np.ndarray:
    x, y = map(float, pose[:2])
    qx, qy, qz, qw = map(float, pose[3:7])
    sin_yaw = 2.0 * (qw * qz + qx * qy)
    cos_yaw = 1.0 - 2.0 * (qy * qy + qz * qz)
    scale = math.hypot(cos_yaw, sin_yaw)
    if scale == 0.0:
        raise ValueError("object quaternion does not define a planar yaw")
    return np.asarray([x, y, cos_yaw / scale, sin_yaw / scale])


def standardize(demos: np.ndarray, states: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    joint = np.concatenate([demos, states], axis=0)
    mean = joint.mean(axis=0)
    scale = joint.std(axis=0)
    scale[scale < 1e-12] = 1.0
    return (demos - mean) / scale, (states - mean) / scale


def pairwise_distance(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum((left[:, None, :] - right[None, :, :]) ** 2, axis=2))


def greedy_coverage(
    distances: np.ndarray,
    names: list[str],
    tiers: dict[str, str],
    weights: np.ndarray,
    allowed: set[str],
    quota: int,
) -> list[str]:
    nearest_all = distances.min(axis=1)
    bandwidth = float(np.median(nearest_all))
    if bandwidth <= 1e-12:
        positive = distances[distances > 1e-12]
        bandwidth = float(np.median(positive)) if positive.size else 1.0
    similarity = np.exp(-(distances**2) / (2.0 * bandwidth * bandwidth))
    selected: list[str] = []
    counts = {tier: 0 for tier in TIERS}
    current = np.zeros(distances.shape[0], dtype=np.float64)
    by_name = {name: index for index, name in enumerate(names)}
    while len(selected) < quota * len(TIERS):
        best: tuple[float, int, str] | None = None
        for name in names:
            tier = tiers[name]
            if name not in allowed or name in selected or counts[tier] >= quota:
                continue
            column = similarity[:, by_name[name]]
            gain = float(np.sum(weights * np.maximum(column - current, 0.0)))
            key = (gain, -demo_number(name), name)
            if best is None or key > best:
                best = key
        if best is None:
            raise ValueError("candidate pool cannot satisfy the tier quotas")
        name = best[2]
        selected.append(name)
        counts[tiers[name]] += 1
        current = np.maximum(current, similarity[:, by_name[name]])
    return sorted(selected, key=demo_number)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--state-bank", type=Path, required=True)
    parser.add_argument("--state-bank-manifest", type=Path, required=True)
    parser.add_argument("--probe-measurements", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    manifest = json.loads(args.state_bank_manifest.read_text(encoding="utf-8"))
    measurement = json.loads(args.probe_measurements.read_text(encoding="utf-8"))
    if sha256(args.dataset) != protocol["source"]["dataset_sha256"]:
        raise ValueError("dataset identity differs from the frozen protocol")
    if sha256(args.state_bank) != manifest["state_bank_sha256"]:
        raise ValueError("state bank differs from its frozen manifest")
    if measurement.get("candidate_outcomes_opened") is not False:
        raise ValueError("probe record must precede candidate outcomes")
    if measurement.get("qualification_passed") is not True:
        raise ValueError("probe-policy failure signal did not qualify")

    with h5py.File(args.state_bank, "r") as bank:
        state_features = np.asarray(bank["features_xy_cosyaw_sinyaw"][:], dtype=np.float64)
        state_strata = np.asarray(bank["stratum"][:], dtype=np.int64)
    state_records = measurement.get("states", [])
    if [record.get("state_id") for record in state_records] != list(range(len(state_features))):
        raise ValueError("probe measurements do not cover the state bank in order")
    trials = np.asarray([record["trials"] for record in state_records], dtype=np.float64)
    failures = np.asarray([record["failures"] for record in state_records], dtype=np.float64)
    if np.any(trials <= 0) or np.any(failures < 0) or np.any(failures > trials):
        raise ValueError("invalid probe-policy success counts")
    failure_weights = (failures + 1.0) / (trials + 2.0)

    with h5py.File(args.dataset, "r") as dataset:
        names = sorted(dataset["data"].keys(), key=demo_number)
        if len(names) != protocol["source"]["demonstrations"]:
            raise ValueError("unexpected demonstration count")
        demo_features = np.stack(
            [pose_feature(dataset["data"][name]["obs"]["object"][0, :7]) for name in names]
        )
        lengths = {name: int(dataset["data"][name].attrs["num_samples"]) for name in names}
        tiers: dict[str, str] = {}
        for tier in TIERS:
            for name in decode(dataset["mask"][tier][:]):
                if name in tiers:
                    raise ValueError("demonstration belongs to multiple operator tiers")
                tiers[name] = tier
    if set(tiers) != set(names):
        raise ValueError("operator tiers do not cover the demonstration pool")

    standardized_demos, standardized_states = standardize(demo_features, state_features)
    distances = pairwise_distance(standardized_states, standardized_demos)
    quota = int(protocol["candidate_construction"]["operator_tier_quota"]["better"])
    all_names = set(names)
    short_pool: set[str] = set()
    for tier in TIERS:
        tier_names = [name for name in names if tiers[name] == tier]
        short_pool.update(
            sorted(tier_names, key=lambda name: (lengths[name], demo_number(name)))[:75]
        )

    random_indices = np.random.default_rng(0).choice(len(names), 150, replace=False)
    candidates = {
        "all_data_reference": names,
        "random_50": sorted((names[index] for index in random_indices), key=demo_number),
        "length_50": sorted(
            sorted(names, key=lambda name: (lengths[name], demo_number(name)))[:150],
            key=demo_number,
        ),
        "coverage_50": greedy_coverage(
            distances, names, tiers, np.ones(len(state_features)), all_names, quota
        ),
        "failure_coverage_50": greedy_coverage(
            distances, names, tiers, failure_weights, all_names, quota
        ),
        "failure_coverage_short_50": greedy_coverage(
            distances, names, tiers, failure_weights, short_pool, quota
        ),
    }

    by_name = {name: index for index, name in enumerate(names)}
    records = {}
    risks = {}
    for candidate_id, members in candidates.items():
        member_indices = [by_name[name] for name in members]
        nearest = distances[:, member_indices].min(axis=1)
        tier_counts = {tier: sum(tiers[name] == tier for name in members) for tier in TIERS}
        records[candidate_id] = {
            "count": len(members),
            "members": members,
            "membership_sha256": membership_hash(members),
            "tier_counts": tier_counts,
            "mean_action_steps": float(np.mean([lengths[name] for name in members])),
            "mean_state_coverage_distance": float(np.mean(nearest)),
            "failure_weighted_mean_state_coverage_distance": float(
                np.average(nearest, weights=failure_weights)
            ),
        }
        risks[candidate_id] = [
            {
                "state_id": index,
                "stratum": int(state_strata[index]),
                "probe_failure_probability": float(failure_weights[index]),
                "coverage_distance": float(nearest[index]),
                "regression_risk": float(failure_weights[index] * nearest[index]),
            }
            for index in range(len(state_features))
        ]

    result = {
        "schema_version": "anarres.robotics-square-candidates.v1",
        "study_id": protocol["study_id"],
        "status": "CANDIDATES_AND_PREDICTIONS_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
        "candidate_outcomes_opened": False,
        "decision": protocol["decision"],
        "candidates": records,
        "state_regression_risk": risks,
        "inputs": {
            "dataset_sha256": sha256(args.dataset),
            "state_bank_sha256": sha256(args.state_bank),
            "state_bank_manifest_sha256": sha256(args.state_bank_manifest),
            "probe_measurements_sha256": sha256(args.probe_measurements),
            "protocol_sha256": sha256(args.protocol),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "candidates": len(records)}, indent=2))


if __name__ == "__main__":
    main()
