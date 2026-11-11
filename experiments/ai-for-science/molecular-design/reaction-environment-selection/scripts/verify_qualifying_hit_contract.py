#!/usr/bin/env python3
"""Verify the compact Q07820 qualifying-hit contract and threshold record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "QUALIFYING_HIT_CONTRACT_V1.json"
THRESHOLDS = ROOT / "Q07820_REFERENCE_THRESHOLDS_V1.json"
ENDPOINT_CONTRACT = ROOT / "STARTING_POLICY_ENDPOINT_QUALIFICATION_CONTRACT_V2.json"
ENDPOINT_RESULT = ROOT / "STARTING_POLICY_ENDPOINT_QUALIFICATION_RESULT_V2.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_artifact(record: dict[str, Any]) -> None:
    required = {
        "uri",
        "path",
        "sha256",
        "size_bytes",
        "media_type",
        "license",
        "producing_run",
    }
    missing = required - set(record)
    if missing:
        raise ValueError(f"artifact reference is missing {sorted(missing)}")
    if len(record["sha256"]) != 64 or record["size_bytes"] <= 0:
        raise ValueError("artifact hash or size is invalid")


def verify() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text())
    result = json.loads(THRESHOLDS.read_text())
    if contract["contract"] != "q07820-qualifying-hit-v1":
        raise ValueError("unexpected endpoint contract")
    if result["contract"] != contract["contract"] or result["target_id"] != "Q07820":
        raise ValueError("threshold identity does not match the endpoint contract")
    if result["candidate_or_trained_policy_outcomes_read"] is not False:
        raise ValueError("threshold record crosses the sealed outcome boundary")

    for artifact in result["inputs"].values():
        require_artifact(artifact)
    contract_input = result["inputs"]["contract"]
    if contract_input["sha256"] != sha256_file(CONTRACT):
        raise ValueError("endpoint contract hash does not match the threshold record")
    if contract_input["size_bytes"] != CONTRACT.stat().st_size:
        raise ValueError("endpoint contract size does not match the threshold record")

    summaries = result["reference_summaries"]
    thresholds = result["instantiated_thresholds"]
    expected = {
        "vina_affinity_maximum": summaries["vina_affinity"]["median"],
        "strain_energy_maximum": summaries["strain_energy"]["p75"],
        "clash_score_maximum": summaries["clash_score"]["p75"],
        "interaction_score_minimum": summaries["interaction_score"]["median"],
    }
    for name, value in expected.items():
        if thresholds[name] != value:
            raise ValueError(f"{name} is not derived from its frozen reference summary")
    for name in ("vina_affinity", "strain_energy", "clash_score", "interaction_score"):
        summary = summaries[name]
        if not 0 < summary["finite"] <= summary["rows"]:
            raise ValueError(f"invalid finite support for {name}")

    endpoint_contract = json.loads(ENDPOINT_CONTRACT.read_text())
    endpoint_result = json.loads(ENDPOINT_RESULT.read_text())
    if endpoint_result.get("contract") != endpoint_contract.get("contract"):
        raise ValueError("starting-policy endpoint result uses the wrong contract")
    if endpoint_result.get("inputs", {}).get(
        "starting_policy_endpoint_contract_sha256"
    ) != sha256_file(ENDPOINT_CONTRACT):
        raise ValueError("starting-policy endpoint contract hash does not match")
    if endpoint_result.get("attempts") != endpoint_contract["sample"]["attempts"]:
        raise ValueError("starting-policy endpoint attempt count does not match")
    if (
        endpoint_result.get("status") != "passed"
        or endpoint_result.get("authorizes_matched_training") is not True
    ):
        raise ValueError("starting-policy endpoint did not pass")
    if not all(endpoint_result.get("checks", {}).values()):
        raise ValueError("starting-policy endpoint contains a failed gate check")

    return {
        "schema_version": "1.0",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "verified",
        "target_id": result["target_id"],
        "contract_sha256": sha256_file(CONTRACT),
        "thresholds_sha256": sha256_file(THRESHOLDS),
        "starting_policy_endpoint_result_sha256": sha256_file(ENDPOINT_RESULT),
        "starting_policy_endpoint_qualifying_attempts": endpoint_result["qualifying_attempts"],
        "starting_policy_endpoint_unique_qualifying_molecules": endpoint_result[
            "unique_qualifying_molecules"
        ],
        "reference_pose_rows": summaries["strain_energy"]["rows"],
        "candidate_or_trained_policy_outcomes_read": False,
    }


def main() -> None:
    print(json.dumps(verify(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
