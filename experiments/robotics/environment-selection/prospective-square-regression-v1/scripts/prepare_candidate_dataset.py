#!/usr/bin/env python3
"""Prepare and verify the frozen Square candidate masks without opening outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import h5py


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def demo_number(name: str) -> int:
    return int(name.rsplit("_", 1)[1])


def mask_key(candidate_id: str) -> str:
    return f"anarres_square_{candidate_id}"


def read_contract(candidates_path: Path, protocol_path: Path) -> tuple[dict, dict]:
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if candidates.get("study_id") != protocol.get("study_id"):
        raise ValueError("candidate artifact belongs to a different study")
    if candidates.get("status") != "CANDIDATES_AND_PREDICTIONS_FROZEN__CANDIDATE_OUTCOMES_UNOPENED":
        raise ValueError("candidate artifact is not a sealed freeze")
    if candidates.get("candidate_outcomes_opened") is not False:
        raise ValueError("candidate artifact reports opened outcomes")
    expected = {record["id"] for record in protocol["candidates"]}
    if set(candidates.get("candidates", {})) != expected:
        raise ValueError("candidate identities differ from the frozen protocol")
    for candidate_id, record in candidates["candidates"].items():
        members = record["members"]
        payload = "\n".join(sorted(members, key=demo_number)) + "\n"
        if len(members) != record["count"] or len(set(members)) != len(members):
            raise ValueError(f"invalid membership count for {candidate_id}")
        if hashlib.sha256(payload.encode()).hexdigest() != record["membership_sha256"]:
            raise ValueError(f"membership hash mismatch for {candidate_id}")
    return candidates, protocol


def validate_prepared(
    dataset_path: Path, candidates_path: Path, protocol_path: Path
) -> dict[str, str]:
    candidates, protocol = read_contract(candidates_path, protocol_path)
    with h5py.File(dataset_path, "r") as dataset:
        if (
            dataset.attrs.get("anarres_square_source_sha256")
            != protocol["source"]["dataset_sha256"]
        ):
            raise ValueError("prepared dataset source identity mismatch")
        if dataset.attrs.get("anarres_square_candidates_sha256") != sha256(candidates_path):
            raise ValueError("prepared dataset candidate identity mismatch")
        known = set(dataset["data"].keys())
        for candidate_id, record in candidates["candidates"].items():
            if candidate_id == "all_data_reference":
                continue
            observed = [value.decode() for value in dataset["mask"][mask_key(candidate_id)][:]]
            expected = sorted(record["members"], key=demo_number)
            if observed != expected or set(observed) - known:
                raise ValueError(f"prepared mask mismatch for {candidate_id}")
    return {
        "dataset_sha256": sha256(dataset_path),
        "candidates_sha256": sha256(candidates_path),
    }


def prepare(source: Path, output: Path, candidates_path: Path, protocol_path: Path) -> dict:
    candidates, protocol = read_contract(candidates_path, protocol_path)
    if source.resolve() == output.resolve():
        raise ValueError("prepared dataset cannot overwrite the source")
    if output.exists():
        raise FileExistsError(output)
    if sha256(source) != protocol["source"]["dataset_sha256"]:
        raise ValueError("source dataset differs from the frozen protocol")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    try:
        with h5py.File(output, "a") as dataset:
            known = set(dataset["data"].keys())
            masks = dataset.require_group("mask")
            for candidate_id, record in candidates["candidates"].items():
                if candidate_id == "all_data_reference":
                    continue
                members = sorted(record["members"], key=demo_number)
                if set(members) - known:
                    raise ValueError(f"{candidate_id} contains unknown demonstrations")
                key = mask_key(candidate_id)
                if key in masks:
                    del masks[key]
                masks.create_dataset(key, data=[member.encode() for member in members])
            dataset.attrs["anarres_square_source_sha256"] = protocol["source"]["dataset_sha256"]
            dataset.attrs["anarres_square_candidates_sha256"] = sha256(candidates_path)
            dataset.attrs["anarres_square_protocol_sha256"] = sha256(protocol_path)
        report = validate_prepared(output, candidates_path, protocol_path)
        output.chmod(0o444)
        return {
            "status": "prepared",
            "candidate_outcomes_opened": False,
            **report,
        }
    except Exception:
        output.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "validate"))
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        if args.output is None:
            parser.error("prepare requires --output")
        result = prepare(args.dataset, args.output, args.candidates, args.protocol)
    else:
        result = validate_prepared(args.dataset, args.candidates, args.protocol)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
