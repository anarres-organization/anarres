#!/usr/bin/env python3
"""Freeze a composition-disjoint PBEsol panel without reading phonon outcomes."""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import re
import tarfile
from pathlib import Path
from zipfile import ZipFile

EXPECTED_SHARD_SHA256 = "7ecfe6261da217394c5db2985d925d7555e9ba19d28bd6143a4bbb1ba45c76dc"
EXPECTED_SHARD_RECORDS = 1530
SOURCE_SHARD_KEY = "mp_0860001-0880000.tar"
PANEL_SIZE = 1000
SELECTION_SALT = "anarres-pbesol-transfer-panel-v1"
PRIOR_PARTITIONS = ("dft_posttrain", "test_dft_pbe")
PRETRAIN_PARTITION = "pretrain"
POSCAR_SUFFIX = "/06_harmonic_phonons/POSCAR.gz"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reduced_key(counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
    divisor = 0
    for value in counts.values():
        divisor = math.gcd(divisor, int(value))
    if divisor <= 0:
        raise ValueError("Composition contains no atoms")
    return tuple(sorted((element, int(value) // divisor) for element, value in counts.items()))


def key_text(key: tuple[tuple[str, int], ...]) -> str:
    return " ".join(f"{element}:{count}" for element, count in key)


def parse_formula(formula: str) -> tuple[tuple[str, int], ...]:
    """Parse an integer chemical formula with nested parentheses."""
    tokens = re.findall(r"[A-Z][a-z]?|\(|\)|\d+", formula.replace(" ", ""))
    if "".join(tokens) != formula.replace(" ", ""):
        raise ValueError(f"Unsupported chemical formula: {formula}")
    stack: list[collections.Counter[str]] = [collections.Counter()]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "(":
            stack.append(collections.Counter())
            index += 1
        elif token == ")":
            if len(stack) == 1:
                raise ValueError(f"Unbalanced formula: {formula}")
            group = stack.pop()
            index += 1
            multiplier = (
                int(tokens[index]) if index < len(tokens) and tokens[index].isdigit() else 1
            )
            if multiplier != 1:
                index += 1
            for element, count in group.items():
                stack[-1][element] += count * multiplier
        elif re.fullmatch(r"[A-Z][a-z]?", token):
            index += 1
            multiplier = (
                int(tokens[index]) if index < len(tokens) and tokens[index].isdigit() else 1
            )
            if multiplier != 1:
                index += 1
            stack[-1][token] += multiplier
        else:
            raise ValueError(f"Unexpected token in formula: {formula}")
    if len(stack) != 1:
        raise ValueError(f"Unbalanced formula: {formula}")
    return reduced_key(dict(stack[0]))


def parse_poscar_composition(raw: bytes) -> tuple[tuple[str, int], ...]:
    lines = [line.strip() for line in gzip.decompress(raw).decode("utf-8").splitlines()]
    if len(lines) < 7:
        raise ValueError("POSCAR is too short")
    elements = lines[5].split()
    try:
        counts = [int(value) for value in lines[6].split()]
    except ValueError as error:
        raise ValueError("Expected VASP 5 element and count lines") from error
    if len(elements) != len(counts) or not all(re.fullmatch(r"[A-Z][a-z]?", x) for x in elements):
        raise ValueError("Expected VASP 5 element symbols in POSCAR")
    return reduced_key(dict(zip(elements, counts, strict=True)))


def rank_value(material_id: str) -> str:
    return hashlib.sha256(f"{SELECTION_SALT}|{material_id}".encode()).hexdigest()


def load_partition(zip_file: ZipFile, partition: str) -> list[dict]:
    member = f"phononscore_data_20261104/{partition}/manifest.json"
    return json.loads(zip_file.read(member))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbesol-shard", type=Path, required=True)
    parser.add_argument("--phononscore-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite frozen panel: {args.out}")
    shard_sha256 = sha256_path(args.pbesol_shard)
    if shard_sha256 != EXPECTED_SHARD_SHA256:
        raise ValueError("PBEsol shard does not match the qualified source digest")

    prior_ids: set[str] = set()
    prior_compositions: set[tuple[tuple[str, int], ...]] = set()
    pretrain_ids: set[str] = set()
    pretrain_compositions: set[tuple[tuple[str, int], ...]] = set()
    with ZipFile(args.phononscore_archive) as archive:
        for partition in PRIOR_PARTITIONS:
            for row in load_partition(archive, partition):
                if row.get("material_id"):
                    prior_ids.add(row["material_id"])
                if row.get("formula_reduced"):
                    prior_compositions.add(parse_formula(row["formula_reduced"]))
        for row in load_partition(archive, PRETRAIN_PARTITION):
            if row.get("material_id"):
                pretrain_ids.add(row["material_id"])
            if row.get("formula_reduced"):
                pretrain_compositions.add(parse_formula(row["formula_reduced"]))

    candidates = []
    with tarfile.open(args.pbesol_shard, "r") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith(POSCAR_SUFFIX):
                continue
            match = re.search(
                r"(?:^|/)(mp-\d+)(?:_[^/]*)?/06_harmonic_phonons/POSCAR.gz$",
                member.name,
            )
            if not match:
                raise ValueError(f"Cannot parse MP identity from {member.name}")
            compressed = archive.extractfile(member).read()
            composition = parse_poscar_composition(compressed)
            candidates.append(
                {
                    "material_id": match.group(1),
                    "poscar_member": member.name,
                    "poscar_gzip_sha256": sha256_bytes(compressed),
                    "reduced_composition": key_text(composition),
                    "composition_key": composition,
                    "rank_sha256": rank_value(match.group(1)),
                }
            )
    if len(candidates) != EXPECTED_SHARD_RECORDS:
        raise ValueError(f"Expected {EXPECTED_SHARD_RECORDS} structures, found {len(candidates)}")
    if len({row["material_id"] for row in candidates}) != len(candidates):
        raise ValueError("PBEsol shard contains duplicate material identities")

    eligible = [
        row
        for row in candidates
        if row["material_id"] not in prior_ids and row["composition_key"] not in prior_compositions
    ]
    by_composition: dict[tuple[tuple[str, int], ...], dict] = {}
    for row in eligible:
        key = row["composition_key"]
        if key not in by_composition or row["rank_sha256"] < by_composition[key]["rank_sha256"]:
            by_composition[key] = row
    unique_compositions = sorted(by_composition.values(), key=lambda row: row["rank_sha256"])
    if len(unique_compositions) < PANEL_SIZE:
        raise ValueError(
            f"Only {len(unique_compositions)} disjoint compositions remain; need {PANEL_SIZE}"
        )
    selected = [dict(row) for row in unique_compositions[:PANEL_SIZE]]
    for row in selected:
        row["starting_pretrain_id_overlap"] = row["material_id"] in pretrain_ids
        row["starting_pretrain_composition_overlap"] = (
            row["composition_key"] in pretrain_compositions
        )
        del row["composition_key"]

    payload = {
        "schema_version": "1.0",
        "study": "phononscore-pbesol-transfer-v1",
        "status": "frozen_before_pbesol_outcome_opening",
        "external_labels_read": False,
        "source": {
            "dataset_doi": "10.5281/zenodo.20196565",
            "shard": SOURCE_SHARD_KEY,
            "shard_sha256": shard_sha256,
            "records": len(candidates),
        },
        "exclusion": {
            "partitions": list(PRIOR_PARTITIONS),
            "excluded_exact_ids": sum(row["material_id"] in prior_ids for row in candidates),
            "excluded_composition_matches": sum(
                row["composition_key"] in prior_compositions for row in candidates
            ),
            "eligible_records_after_joint_exclusion": len(eligible),
            "eligible_unique_compositions": len(unique_compositions),
        },
        "selection": {
            "panel_size": PANEL_SIZE,
            "one_record_per_reduced_composition": True,
            "rule": "minimum SHA-256 rank after identity and composition exclusion",
            "salt": SELECTION_SALT,
        },
        "starting_pretrain_overlap": {
            "exact_ids_in_selected_panel": sum(
                row["starting_pretrain_id_overlap"] for row in selected
            ),
            "compositions_in_selected_panel": sum(
                row["starting_pretrain_composition_overlap"] for row in selected
            ),
            "interpretation": (
                "reported overlap with the fixed starting model; PBEsol outcomes remain new"
            ),
        },
        "frozen_prediction": {
            "source": "complete two-seed ordering on the earlier PBE panel",
            "best_by_budget": {"256": "coverage", "512": "coverage", "1024": "hash_uniform"},
            "complete_order_by_budget": {
                "256": ["coverage", "signal", "signal_coverage", "hash_uniform"],
                "512": ["coverage", "hash_uniform", "signal", "signal_coverage"],
                "1024": ["hash_uniform", "coverage", "signal_coverage", "signal"],
            },
        },
        "outcome_contract": {
            "functional": "PBEsol",
            "minimum_frequency_field": "summary.json.gz:min_frequency",
            "stability_threshold_thz": -0.1,
            "primary_decision_metric": "top_100_stable_rate_by_frozen_composite_score",
            "supporting_metrics": [
                "continuous_pairwise_concordance",
                "roc_auc_at_minus_0.1_thz",
                "brier_score_at_minus_0.1_thz",
                "minimum_frequency_mae_thz",
            ],
        },
        "records": selected,
    }
    payload["panel_freeze_sha256"] = canonical_digest(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"selected={len(selected)}")
    print(f"panel_freeze_sha256={payload['panel_freeze_sha256']}")


if __name__ == "__main__":
    main()
