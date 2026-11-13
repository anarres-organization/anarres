from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "FROZEN_CONTRACT.json"
SOURCES_PATH = ROOT / "SOURCES.json"


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def contract_hashes() -> dict[str, str]:
    return {
        "frozen_contract_sha256": sha256_path(CONTRACT_PATH),
        "sources_sha256": sha256_path(SOURCES_PATH),
    }


def source_record(dataset: str) -> dict[str, Any]:
    records = load_json(SOURCES_PATH)["dataset"]["files"]
    matches = [record for record in records if record["dataset"] == dataset]
    if len(matches) != 1:
        raise ValueError(f"unknown dataset: {dataset}")
    return matches[0]


def verify_source(source_dir: Path, dataset: str) -> Path:
    record = source_record(dataset)
    path = source_dir / record["filename"]
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != record["bytes"]:
        raise ValueError(f"source byte mismatch: {path}")
    if sha256_path(path) != record["sha256"]:
        raise ValueError(f"source hash mismatch: {path}")
    return path


def load_dataset(path: Path) -> tuple[list[str], list[float]]:
    sequences: list[str] = []
    targets: list[float] = []
    with gzip.open(path, "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"sequence", "target", "set", "validation"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"missing required columns in {path}")
        for row in reader:
            sequence = row["sequence"].strip()
            target = row["target"].strip()
            if not sequence or not target:
                raise ValueError(f"incomplete dataset row in {path}")
            sequences.append(sequence)
            targets.append(float(target))
    return sequences, targets


def deterministic_cap(
    dataset: str,
    sequences: list[str],
    targets: list[float],
    cap: int,
) -> tuple[list[str], list[float], str]:
    ranked = sorted(
        range(len(sequences)),
        key=lambda index: hashlib.sha256(f"{dataset}|{sequences[index]}|{index}".encode()).digest(),
    )[:cap]
    ranked.sort()
    membership = hashlib.sha256(",".join(map(str, ranked)).encode()).hexdigest()
    return [sequences[index] for index in ranked], [targets[index] for index in ranked], membership


def unit_name(dataset: str, strategy: str, seed: int) -> str:
    return f"{dataset}__{strategy}__seed{seed}.json"
