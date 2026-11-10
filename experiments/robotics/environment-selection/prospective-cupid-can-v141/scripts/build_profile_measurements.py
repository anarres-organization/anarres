#!/usr/bin/env python3
"""Compact sealed CUPID measurements into a public profile source record."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

from freeze_candidates import (
    CANONICAL_KEY,
    TIERS,
    correlation,
    jaccard,
    membership_hash,
    ordinal_ranks,
    read_score,
    top_set,
)

SCHEMA = "anarres.robotics-cupid-candidate-measurements.v2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {path}")
    return value


def effective_tier_coverage(counts: list[int]) -> float:
    total = sum(counts)
    return 0.0 if total == 0 else total * total / (len(TIERS) * sum(x * x for x in counts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", nargs=3, type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", nargs=3, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)

    protocol = read_object(args.protocol)
    qualification = read_object(args.qualification)
    metadata = read_object(args.metadata)
    candidates = read_object(args.candidates)
    scores = [read_score(path) for path in args.scores]

    if protocol.get("study_id") != candidates.get("study_id"):
        raise ValueError("candidate and protocol study identities differ")
    if qualification.get("study_id") != protocol.get("study_id"):
        raise ValueError("qualification and protocol study identities differ")
    if qualification.get("passed") is not True:
        raise ValueError("closed-loop qualification did not pass")
    if candidates.get("outcomes_read") is not False or metadata.get("outcomes_read") is not False:
        raise ValueError("candidate outcomes must remain unopened")
    prepared_dataset_sha256 = metadata.get("dataset_sha256", "")
    if len(prepared_dataset_sha256) != 64:
        raise ValueError("prepared dataset metadata lacks a SHA-256 identity")

    names = scores[0]["demos"]
    lengths = scores[0]["demo_lengths"]
    if len(names) != 300 or len(lengths) != len(names):
        raise ValueError("expected 300 scored demonstrations and lengths")
    if metadata.get("demonstrations") != names:
        raise ValueError("metadata does not cover the scored demonstrations in order")
    for score in scores[1:]:
        if score["demos"] != names or score["demo_lengths"] != lengths:
            raise ValueError("score files use different demonstrations or lengths")
    score_value_counts = [len(score["scores"][CANONICAL_KEY]) for score in scores]
    if any(count != len(names) for count in score_value_counts):
        raise ValueError("every scoring checkpoint must cover every demonstration")
    checkpoint_outcome_support = []
    for score in scores:
        outcomes = [int(value) for value in score["test"]["success"]]
        checkpoint_outcome_support.append(
            {
                "episodes": len(outcomes),
                "failures": len(outcomes) - sum(outcomes),
                "successes": sum(outcomes),
            }
        )

    ranks = [ordinal_ranks(score["scores"][CANONICAL_KEY], names) for score in scores]
    pairwise_spearman = [
        correlation(ranks[i], ranks[j]) for i, j in combinations(range(len(ranks)), 2)
    ]
    top_sets = [top_set(rank, names, len(names) // 2) for rank in ranks]
    pairwise_jaccard = [
        jaccard(top_sets[i], top_sets[j]) for i, j in combinations(range(len(ranks)), 2)
    ]
    mean_spearman = sum(pairwise_spearman) / len(pairwise_spearman)
    mean_jaccard = sum(pairwise_jaccard) / len(pairwise_jaccard)
    frozen_reliability = candidates["measurement_reliability"]
    if not math.isclose(mean_spearman, frozen_reliability["mean_pairwise_spearman"]):
        raise ValueError("recomputed rank reliability differs from frozen candidates")
    if not math.isclose(mean_jaccard, frozen_reliability["mean_pairwise_top_half_jaccard"]):
        raise ValueError("recomputed top-half overlap differs from frozen candidates")
    gate = protocol["measurement"]["reliability_gate"]
    gate_passed = (
        mean_spearman >= gate["minimum_mean_pairwise_spearman"]
        and mean_jaccard >= gate["minimum_mean_pairwise_top_half_jaccard"]
    )
    if gate_passed is not frozen_reliability.get("gate_passed"):
        raise ValueError("recomputed reliability gate differs from frozen candidates")

    merged = [sum(rank[i] for rank in ranks) / len(ranks) for i in range(len(names))]
    by_name = {name: i for i, name in enumerate(names)}
    records = {}
    for candidate_id, candidate in sorted(candidates["candidates"].items()):
        members = candidate["members"]
        if candidate["count"] != len(members) or len(members) != len(set(members)):
            raise ValueError(f"invalid candidate membership: {candidate_id}")
        if any(name not in by_name for name in members):
            raise ValueError(f"unknown demonstration in candidate: {candidate_id}")
        if candidate["membership_sha256"] != membership_hash(members):
            raise ValueError(f"membership digest differs for {candidate_id}")
        tier_counts = {
            tier: sum(metadata["tiers"][name] == tier for name in members) for tier in TIERS
        }
        records[candidate_id] = {
            "count": len(members),
            "membership_sha256": candidate["membership_sha256"],
            "tier_counts": tier_counts,
            "coordinates": {
                "mean_cupid_rank_percentile": (
                    sum(merged[by_name[name]] for name in members)
                    / (len(members) * (len(names) - 1))
                ),
                "operator_tier_effective_coverage": effective_tier_coverage(
                    list(tier_counts.values())
                ),
                "mean_demonstration_action_steps": (
                    sum(lengths[by_name[name]] for name in members) / len(members)
                ),
                "measurement_rank_reliability": mean_spearman,
            },
        }

    score_inputs = {path.name: sha256(path) for path in args.scores}
    if score_inputs != candidates.get("score_inputs"):
        raise ValueError("score-file digests differ from the frozen candidate record")
    for digest in args.checkpoint_sha256:
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("checkpoint digests must be lowercase SHA-256 values")
    subject_revision = hashlib.sha256(
        ("\n".join(args.checkpoint_sha256) + "\n").encode("utf-8")
    ).hexdigest()

    result = {
        "schema_version": SCHEMA,
        "study_id": protocol["study_id"],
        "status": "PRE_OUTCOME_MEASUREMENTS_COMPLETE__CANDIDATE_OUTCOMES_UNOPENED",
        "outcomes_read": False,
        "source_dataset_sha256": protocol["source"]["dataset_sha256"],
        "prepared_dataset_sha256": prepared_dataset_sha256,
        "subject": {
            "kind": "policy-ensemble",
            "id": "robomimic-diffusion-policy-can-v141-scoring-ensemble",
            "revision": f"sha256:{subject_revision}",
            "checkpoint_sha256": args.checkpoint_sha256,
        },
        "measurement": {
            "canonical_aggregation": CANONICAL_KEY,
            "checkpoint_outcome_support": checkpoint_outcome_support,
            "scoring_checkpoints": len(scores),
            "demonstrations": len(names),
            "expected_score_values": len(scores) * len(names),
            "observed_score_values": sum(score_value_counts),
            "score_missingness_rate": 0.0,
            "pairwise_spearman": pairwise_spearman,
            "mean_pairwise_spearman": mean_spearman,
            "pairwise_top_half_jaccard": pairwise_jaccard,
            "mean_pairwise_top_half_jaccard": mean_jaccard,
            "reliability_gate_passed": gate_passed,
        },
        "decision": candidates["decision"],
        "candidates": records,
        "native_inputs": {
            "candidate_freeze_sha256": sha256(args.candidates),
            "metadata_sha256": sha256(args.metadata),
            "score_sha256": score_inputs,
            "protocol_sha256": sha256(args.protocol),
            "qualification_sha256": sha256(args.qualification),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.out), "candidates": len(records)}, indent=2))


if __name__ == "__main__":
    main()
