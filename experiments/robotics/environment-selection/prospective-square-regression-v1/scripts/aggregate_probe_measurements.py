#!/usr/bin/env python3
"""Qualify three all-data probe policies and freeze their failure map."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate(blobs: list[dict], protocol: dict) -> dict:
    expected_states = int(protocol["state_bank"]["states"])
    expected_replicates = int(protocol["state_bank"]["policy_rollout_replicates_per_state"])
    expected_pairs = {
        (state_id, replicate)
        for state_id in range(expected_states)
        for replicate in range(expected_replicates)
    }
    state_rows = [
        {"state_id": state_id, "stratum": None, "trials": 0, "failures": 0}
        for state_id in range(expected_states)
    ]
    checkpoint_hashes = set()
    total_successes = 0
    total_failures = 0
    total_exceptions = 0
    for blob in blobs:
        if blob.get("study_id") != protocol["study_id"]:
            raise ValueError("probe evaluation belongs to a different study")
        if blob.get("policy_id") != "all_data_probe":
            raise ValueError("probe evaluation has the wrong policy identity")
        pairs = {(row["state_id"], row["replicate"]) for row in blob["records"]}
        if pairs != expected_pairs or len(blob["records"]) != len(expected_pairs):
            raise ValueError("probe evaluation does not cover the frozen state-replicate matrix")
        checkpoint_hashes.add(blob["checkpoint_sha256"])
        for row in blob["records"]:
            record = state_rows[row["state_id"]]
            if record["stratum"] is None:
                record["stratum"] = row["stratum"]
            elif record["stratum"] != row["stratum"]:
                raise ValueError("state stratum changed across probe policies")
            record["trials"] += 1
            record["failures"] += int(not row["success"])
            total_successes += int(row["success"])
            total_failures += int(not row["success"])
            total_exceptions += int(row["exception"] is not None)
    if len(checkpoint_hashes) != len(blobs):
        raise ValueError("probe policies must use distinct checkpoints")

    thresholds = protocol["measurement"]["qualification"]
    populated_strata = len({row["stratum"] for row in state_rows})
    qualified = (
        total_successes >= thresholds["minimum_total_successes"]
        and total_failures >= thresholds["minimum_total_failures"]
        and populated_strata >= thresholds["minimum_populated_strata"]
        and total_exceptions == 0
    )
    stratum_trials = Counter()
    stratum_failures = Counter()
    for row in state_rows:
        stratum_trials[row["stratum"]] += row["trials"]
        stratum_failures[row["stratum"]] += row["failures"]
    return {
        "schema_version": "anarres.robotics-square-probe-measurements.v1",
        "study_id": protocol["study_id"],
        "status": (
            "PROBE_MEASUREMENT_QUALIFIED__CANDIDATE_OUTCOMES_UNOPENED"
            if qualified
            else "PROBE_MEASUREMENT_FAILED__ABSTAIN"
        ),
        "candidate_outcomes_opened": False,
        "qualification_passed": qualified,
        "probe_policies": len(blobs),
        "episodes": total_successes + total_failures,
        "successes": total_successes,
        "failures": total_failures,
        "exceptions": total_exceptions,
        "populated_strata": populated_strata,
        "strata": {
            str(index): {
                "trials": stratum_trials[index],
                "failures": stratum_failures[index],
            }
            for index in sorted(stratum_trials)
        },
        "states": state_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluations", nargs=3, type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    blobs = [json.loads(path.read_text(encoding="utf-8")) for path in args.evaluations]
    result = aggregate(blobs, protocol)
    result["inputs"] = {path.name: sha256(path) for path in args.evaluations}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {key: result[key] for key in ("status", "episodes", "successes", "failures")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
