#!/usr/bin/env python3
"""Derive equal-size Snowball candidate measurements from one frozen probe bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_weights(panel: dict, candidate: dict, mapping: dict[str, str]) -> dict[str, float]:
    weights = {source: float(weight) for source, weight in panel["fixed_source_shares"].items()}
    for name, weight in candidate["shares"].items():
        if name not in mapping:
            raise ValueError(f"candidate share {name} has no source mapping")
        source = mapping[name]
        if source in weights:
            raise ValueError(f"source {source} appears in both fixed and exchanged shares")
        weights[source] = float(weight)
    if any(not math.isfinite(weight) or weight < 0 for weight in weights.values()):
        raise ValueError("candidate source shares must be finite and non-negative")
    if not math.isclose(sum(weights.values()), 1.0):
        raise ValueError("candidate source shares must sum to one")
    return weights


def largest_remainder(weights: dict[str, float], total: int) -> dict[str, int]:
    raw = {source: total * weight for source, weight in weights.items()}
    quotas = {source: math.floor(value) for source, value in raw.items()}
    remaining = total - sum(quotas.values())
    order = sorted(raw, key=lambda source: (-(raw[source] - quotas[source]), source))
    for source in order[:remaining]:
        quotas[source] += 1
    if sum(quotas.values()) != total:
        raise ValueError("largest-remainder allocation does not match the candidate size")
    return quotas


def rank_key(seed: int, source_id: str, prompt_group_id: str) -> str:
    payload = f"{seed}\0{source_id}\0{prompt_group_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def coordinates(groups: list[dict]) -> dict:
    masses = [float(group["admitted_advantage_mass"]) for group in groups]
    total_mass = sum(masses)
    total_tokens = sum(int(group["generated_tokens"]) for group in groups)
    squared_mass = sum(mass * mass for mass in masses)
    return {
        "usable_signal_density_per_million_generated_tokens": 1_000_000 * total_mass / total_tokens,
        "effective_prompt_coverage": (
            0.0 if squared_mass == 0 else total_mass * total_mass / squared_mass / len(groups)
        ),
        "total_admitted_advantage_mass": total_mass,
        "generated_tokens": total_tokens,
        "prompt_groups": len(groups),
    }


def validate_group(group: dict) -> None:
    required = {
        "source_id",
        "prompt_group_id",
        "attempts",
        "valid_rewards",
        "admitted_attempts",
        "infrastructure_invalid_attempts",
        "verifier_invalid_attempts",
        "trace_failure_attempts",
        "admitted_advantage_mass",
        "generated_tokens",
    }
    missing = sorted(required - set(group))
    if missing:
        raise ValueError(f"probe-bank group lacks fields: {', '.join(missing)}")
    if not isinstance(group["source_id"], str) or not group["source_id"]:
        raise ValueError("probe-bank group source identity must be non-empty")
    if not isinstance(group["prompt_group_id"], str) or not group["prompt_group_id"]:
        raise ValueError("probe-bank prompt-group identity must be non-empty")
    for field in (
        "attempts",
        "valid_rewards",
        "admitted_attempts",
        "infrastructure_invalid_attempts",
        "verifier_invalid_attempts",
        "trace_failure_attempts",
    ):
        if not isinstance(group[field], int) or isinstance(group[field], bool) or group[field] < 0:
            raise ValueError(f"probe-bank group {field} must be a non-negative integer")
    if group["valid_rewards"] > group["attempts"]:
        raise ValueError("probe-bank valid rewards exceed attempts")
    if group["admitted_attempts"] > group["valid_rewards"]:
        raise ValueError("probe-bank admitted attempts exceed valid rewards")
    mass = group["admitted_advantage_mass"]
    if not isinstance(mass, int | float) or isinstance(mass, bool) or not math.isfinite(mass):
        raise ValueError("probe-bank admitted advantage mass must be finite")
    if mass < 0:
        raise ValueError("probe-bank admitted advantage mass must be non-negative")
    if not isinstance(group["generated_tokens"], int) or group["generated_tokens"] <= 0:
        raise ValueError("probe-bank generated tokens must be a positive integer")


def derive(contract: dict, panel: dict, bank: dict) -> dict:
    if contract.get("status") != "FROZEN_AFTER_PROBES_BEFORE_CANDIDATE_TRAINING":
        raise ValueError("candidate derivation contract is not frozen at the required chronology")
    if panel.get("artifact") != contract["candidate_panel_artifact"]:
        raise ValueError("candidate panel identity differs from the derivation contract")
    if bank.get("schema_version") != "anarres.snowball-probe-bank.v1":
        raise ValueError("unsupported Snowball probe-bank schema")
    candidate_size = contract["candidate_prompt_groups"]
    if not isinstance(candidate_size, int) or candidate_size <= 0:
        raise ValueError("candidate prompt-group count must be a positive integer")
    seed = contract["selection_seed"]
    if not isinstance(seed, int):
        raise ValueError("selection seed must be an integer")

    by_source: dict[str, list[dict]] = defaultdict(list)
    seen_groups = set()
    for group in bank["groups"]:
        validate_group(group)
        identity = group["prompt_group_id"]
        if identity in seen_groups:
            raise ValueError(f"duplicate prompt-group identity {identity}")
        seen_groups.add(identity)
        by_source[group["source_id"]].append(group)
    declared_sources = {row["source_id"] for row in bank["sources"]}
    if set(by_source) != declared_sources:
        raise ValueError("probe-bank source summaries and prompt groups differ")
    ordered = {
        source: sorted(
            groups,
            key=lambda group: (
                rank_key(seed, source, group["prompt_group_id"]),
                group["prompt_group_id"],
            ),
        )
        for source, groups in by_source.items()
    }

    candidates = []
    for candidate in panel["candidates"]:
        weights = source_weights(panel, candidate, contract["source_mapping"])
        if set(weights) != set(ordered):
            raise ValueError(
                f"candidate {candidate['candidate_id']} sources differ from the probe bank"
            )
        quotas = largest_remainder(weights, candidate_size)
        shortages = {
            source: quota - len(ordered[source])
            for source, quota in quotas.items()
            if quota > len(ordered[source])
        }
        if shortages:
            detail = ", ".join(f"{source}: {count}" for source, count in sorted(shortages.items()))
            raise ValueError(
                f"probe bank lacks prompt groups for {candidate['candidate_id']}: {detail}"
            )
        selected = [group for source, quota in quotas.items() for group in ordered[source][:quota]]
        selected.sort(key=lambda group: (group["source_id"], group["prompt_group_id"]))
        validity = Counter()
        for group in selected:
            for field in (
                "attempts",
                "valid_rewards",
                "admitted_attempts",
                "infrastructure_invalid_attempts",
                "verifier_invalid_attempts",
                "trace_failure_attempts",
            ):
                validity[field] += int(group[field])
        candidates.append(
            {
                "candidate_id": candidate["candidate_id"],
                "source_shares": dict(sorted(weights.items())),
                "source_prompt_groups": dict(sorted(quotas.items())),
                "coordinates": coordinates(selected),
                "validity_counts": dict(sorted(validity.items())),
                "prompt_groups": [
                    {"source_id": group["source_id"], "prompt_group_id": group["prompt_group_id"]}
                    for group in selected
                ],
            }
        )

    return {
        "schema_version": "anarres.snowball-candidate-measurements.v1",
        "study_id": bank["study_id"],
        "probe_bank_id": bank["probe_bank_id"],
        "policy_id": bank["policy_id"],
        "policy_revision": bank["policy_revision"],
        "candidate_prompt_groups": candidate_size,
        "selection_seed": seed,
        "candidates": candidates,
        "boundary": (
            "Prediction-time measurements only; candidate-training outcomes remain unopened."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--probe-bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    contract = json.loads(arguments.contract.read_text(encoding="utf-8"))
    panel = json.loads(arguments.panel.read_text(encoding="utf-8"))
    bank = json.loads(arguments.probe_bank.read_text(encoding="utf-8"))
    bound = contract["bound_inputs"]
    if bound["candidate_panel_sha256"] != sha256(arguments.panel):
        raise ValueError("candidate panel differs from the derivation freeze")
    if bound["probe_bank_sha256"] != sha256(arguments.probe_bank):
        raise ValueError("probe bank differs from the derivation freeze")
    if bound["derivation_script_sha256"] != sha256(Path(__file__)):
        raise ValueError("candidate derivation implementation differs from the freeze")
    result = derive(contract, panel, bank)
    result["inputs"] = {
        "contract_sha256": sha256(arguments.contract),
        "candidate_panel_sha256": sha256(arguments.panel),
        "probe_bank_sha256": sha256(arguments.probe_bank),
    }
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
