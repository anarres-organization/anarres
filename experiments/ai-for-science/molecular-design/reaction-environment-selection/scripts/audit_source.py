#!/usr/bin/env python3
"""Audit training-visible files in pinned RxnFlow and MolGenBench checkouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(repository: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def verify_files(repository: Path, expected: dict[str, str]) -> dict[str, str]:
    missing = [relative for relative in expected if not (repository / relative).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing qualified files: {missing}")
    observed = {relative: sha256(repository / relative) for relative in expected}
    mismatches = {
        relative: {"expected": expected[relative], "observed": observed[relative]}
        for relative in expected
        if observed[relative] != expected[relative]
    }
    if mismatches:
        raise ValueError(f"Qualified file hashes differ: {mismatches}")
    return observed


def count_reactions(path: Path, group: str) -> int:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"^{re.escape(group)}:\n(?P<body>.*?)(?=^[A-Za-z][A-Za-z]+Reaction:|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError(f"Missing reaction group: {group}")
    return sum(
        1
        for line in match.group("body").splitlines()
        if re.match(r"^  [a-zA-Z0-9_]+:\s*(?:#.*)?$", line)
    )


def audit_rxnflow(repository: Path, source: dict[str, object]) -> dict[str, object]:
    observed_commit = git_commit(repository)
    if observed_commit != source["commit"]:
        raise ValueError(
            f"RxnFlow commit differs: expected {source['commit']}, got {observed_commit}"
        )
    observed_hashes = verify_files(repository, source["qualified_files"])
    building_blocks = repository / "data/building_blocks/example_5k.smi"
    rows = [line.split("\t") for line in building_blocks.read_text().splitlines()]
    if len(rows) != 5000 or any(len(row) != 2 for row in rows):
        raise ValueError("RxnFlow example catalog must contain 5,000 two-field rows")
    identifiers = [row[1] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("RxnFlow example building-block identifiers are not unique")

    reaction_path = repository / "data/templates/explore/reaction.yaml"
    synthon_path = repository / "data/templates/explore/synthon.yaml"
    reaction_counts = {
        "unimolecular": count_reactions(reaction_path, "UniReaction"),
        "bimolecular": count_reactions(reaction_path, "BiReaction"),
    }
    synthon_types = sum(
        line.startswith("- type:") for line in synthon_path.read_text(encoding="utf-8").splitlines()
    )
    expected_counts = {"unimolecular": 4, "bimolecular": 26}
    if reaction_counts != expected_counts or synthon_types != 28:
        raise ValueError(
            f"Unexpected reaction fixture counts: {reaction_counts}, synthons={synthon_types}"
        )
    return {
        "commit": observed_commit,
        "qualified_file_sha256": observed_hashes,
        "inventory": {
            "building_blocks": len(rows),
            "unique_building_block_ids": len(set(identifiers)),
            "unimolecular_reactions": reaction_counts["unimolecular"],
            "bimolecular_reactions": reaction_counts["bimolecular"],
            "synthon_types": synthon_types,
        },
        "qualification": "pass",
    }


def audit_molgenbench(repository: Path, source: dict[str, object]) -> dict[str, object]:
    observed_commit = git_commit(repository)
    if observed_commit != source["commit"]:
        raise ValueError(
            f"MolGenBench commit differs: expected {source['commit']}, got {observed_commit}"
        )
    observed_hashes = verify_files(repository, source["qualified_files"])
    fixture_targets = sorted(
        path.name for path in (repository / "TestSamples").iterdir() if path.is_dir()
    )
    if fixture_targets != ["O14757", "Q92769"]:
        raise ValueError(f"Unexpected MolGenBench test targets: {fixture_targets}")
    return {
        "commit": observed_commit,
        "qualified_file_sha256": observed_hashes,
        "test_fixture_targets": fixture_targets,
        "dataset_archive_inspected": False,
        "evaluation_outcomes_inspected": False,
        "qualification": "code_pass_dataset_open",
    }


def audit(rxnflow_repo: Path, molgenbench_repo: Path, sources: Path) -> dict[str, object]:
    registry = json.loads(sources.read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0",
        "study": registry["study"],
        "scope": "training-visible source code and public construction fixtures",
        "training_or_evaluation_outcomes_inspected": False,
        "rxnflow": audit_rxnflow(rxnflow_repo, registry["rxnflow"]),
        "molgenbench": audit_molgenbench(molgenbench_repo, registry["molgenbench"]),
        "open_gates": [
            "MolGenBench Version4 archive checksum and license",
            "target fixture and oracle qualification",
            "target reward adapter",
            "common warm-start checkpoint",
        ],
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--rxnflow-repo", type=Path, required=True)
    parser.add_argument("--molgenbench-repo", type=Path, required=True)
    parser.add_argument("--sources", type=Path, default=root / "SOURCES.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit(args.rxnflow_repo, args.molgenbench_repo, args.sources)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
