#!/usr/bin/env python3
"""Construct and independently qualify the two frozen prospective banks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from construct_development_banks import construct, eligible_records, normalized_representation
from qualify_development_banks import file_sha256, jaccard, summarize_bank


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def round_robin_unique(
    rankings: list[list[dict[str, Any]]],
    fallback: list[dict[str, Any]],
    size: int,
) -> list[dict[str, Any]]:
    """Interleave frozen rankings without allowing one record to occupy two slots."""

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    cursors = [0] * len(rankings)
    while len(selected) < size:
        progressed = False
        for index, ranking in enumerate(rankings):
            while cursors[index] < len(ranking):
                row = ranking[cursors[index]]
                cursors[index] += 1
                if row["record_id"] in selected_ids:
                    continue
                selected.append(row)
                selected_ids.add(row["record_id"])
                progressed = True
                break
            if len(selected) == size:
                return selected
        if not progressed:
            break
    for row in fallback:
        if row["record_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["record_id"])
            if len(selected) == size:
                return selected
    raise ValueError(f"eligible pool cannot fill a {size}-record prospective bank")


def construct_hybrids(
    records: list[dict[str, Any]], contract: dict[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    size = int(contract["bank_size"])
    pool = eligible_records(records)
    development = construct(records, size)
    fallback = development["hash_uniform"] + [
        row for row in pool if row not in development["hash_uniform"]
    ]
    banks = {}
    for name in contract["prospective_bank_order"]:
        streams = contract["construction"][name]["rank_streams"]
        banks[name] = round_robin_unique(
            [development[stream] for stream in streams], fallback, size
        )
    return banks, pool


def apply_checks(
    summaries: dict[str, dict[str, float]], checks: list[dict[str, str]]
) -> dict[str, bool]:
    results = {}
    for check in checks:
        candidate = summaries[check["bank"]][check["coordinate"]]
        reference = summaries[check["reference_bank"]][check["coordinate"]]
        if check["direction"] == "higher":
            passed = candidate > reference
        elif check["direction"] == "lower":
            passed = candidate < reference
        else:
            raise ValueError(f"unsupported direction: {check['direction']}")
        results[check["check_id"]] = bool(passed)
    return results


def qualify(
    records_by_view: list[list[dict[str, Any]]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    if len(records_by_view) != 2:
        raise ValueError("prospective qualification requires exactly two independent views")
    banks_by_view = []
    summaries_by_view = []
    for records in records_by_view:
        banks, pool = construct_hybrids(records, contract)
        representation = normalized_representation(pool)
        development = construct(records, int(contract["bank_size"]))
        summaries = {
            name: summarize_bank(members, pool, representation)
            for name, members in {**development, **banks}.items()
        }
        banks_by_view.append(banks)
        summaries_by_view.append(summaries)
    checks_by_view = [
        apply_checks(summaries, contract["qualification"]["checks"])
        for summaries in summaries_by_view
    ]
    aggregate_checks = {
        check["check_id"]: all(view[check["check_id"]] for view in checks_by_view)
        for check in contract["qualification"]["checks"]
    }
    names = contract["prospective_bank_order"]
    construction_sets = {
        name: {row["record_id"] for row in banks_by_view[0][name]} for name in names
    }
    membership_jaccard = jaccard(construction_sets[names[0]], construction_sets[names[1]])
    distinct = membership_jaccard < 1.0
    passed = all(aggregate_checks.values()) and distinct
    return {
        "schema_version": "anarres.molecular-prospective-banks.v1",
        "study": contract["study"],
        "qualification": "pass" if passed else "fail",
        "outcomes_opened": False,
        "view_seeds": [
            int(contract["construction_view_seed"]),
            int(contract["confirmation_view_seed"]),
        ],
        "banks": {
            name: {
                "members": [row["record_id"] for row in banks_by_view[0][name]],
                "coordinates": summaries_by_view[0][name],
            }
            for name in names
        },
        "confirmation_reconstruction": {
            name: {
                "members": [row["record_id"] for row in banks_by_view[1][name]],
                "coordinates": summaries_by_view[1][name],
            }
            for name in names
        },
        "checks_by_view": checks_by_view,
        "aggregate_checks": aggregate_checks,
        "construction_membership_jaccard": membership_jaccard,
        "distinct_construction_memberships": distinct,
    }


def validate_inputs(
    records_paths: list[Path],
    manifest_paths: list[Path],
    measurement_contract: dict[str, Any],
    bank_contract: dict[str, Any],
    prospective_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    if len(records_paths) != 2 or len(manifest_paths) != 2:
        raise ValueError("supply exactly two records files and two manifests")
    manifests = [read_json(path) for path in manifest_paths]
    expected = [
        int(prospective_contract["construction_view_seed"]),
        int(prospective_contract["confirmation_view_seed"]),
    ]
    if [int(manifest["view_seed"]) for manifest in manifests] != expected:
        raise ValueError("view seeds do not match the prospective bank contract")
    if expected[0] != int(measurement_contract["sampling"]["construction_view_seed"]):
        raise ValueError("construction view differs from the measurement contract")
    bank_rule = bank_contract["confirmation_rule"]
    bank_expected = [
        int(bank_rule["construction_view_seed"]),
        int(bank_rule["confirmation_view_seed"]),
    ]
    if expected != bank_expected:
        raise ValueError("view seeds differ from the frozen bank contract")
    for records_path, manifest in zip(records_paths, manifests, strict=True):
        if file_sha256(records_path) != manifest["output_sha256"]:
            raise ValueError(f"records digest mismatch: {records_path}")
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement-contract", type=Path, required=True)
    parser.add_argument("--bank-contract", type=Path, required=True)
    parser.add_argument("--prospective-contract", type=Path, required=True)
    parser.add_argument("--records", type=Path, action="append", required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measurement = read_json(args.measurement_contract)
    bank_contract = read_json(args.bank_contract)
    contract = read_json(args.prospective_contract)
    manifests = validate_inputs(args.records, args.manifest, measurement, bank_contract, contract)
    result = qualify([read_jsonl(path) for path in args.records], contract)
    result["inputs"] = {
        "measurement_contract_sha256": file_sha256(args.measurement_contract),
        "bank_contract_sha256": file_sha256(args.bank_contract),
        "prospective_contract_sha256": file_sha256(args.prospective_contract),
        "records_sha256": {path.name: file_sha256(path) for path in args.records},
        "manifests_sha256": {path.name: file_sha256(path) for path in args.manifest},
        "source_samples_sha256": {
            str(manifest["view_seed"]): manifest["samples_sha256"] for manifest in manifests
        },
        "source_scores_sha256": {
            str(manifest["view_seed"]): manifest["scores_sha256"] for manifest in manifests
        },
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"qualification": result["qualification"]}, sort_keys=True))


if __name__ == "__main__":
    main()
