from __future__ import annotations

import csv
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


def source_record(assay: str) -> dict[str, Any]:
    records = load_json(SOURCES_PATH)["dataset"]["files"]
    matches = [record for record in records if record["assay"] == assay]
    if len(matches) != 1:
        raise ValueError(f"unknown assay: {assay}")
    return matches[0]


def verify_source(source_dir: Path, assay: str) -> Path:
    record = source_record(assay)
    path = source_dir / record["filename"]
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != record["bytes"]:
        raise ValueError(f"source byte mismatch: {path}")
    if sha256_path(path) != record["sha256"]:
        raise ValueError(f"source hash mismatch: {path}")
    return path


def load_assay(path: Path) -> tuple[list[str], list[float]]:
    sequences: list[str] = []
    outcomes: list[float] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"heavy_chain_seq", "light_chain_seq", "binding_score"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"missing required columns in {path}")
        for row in reader:
            heavy = row["heavy_chain_seq"].strip()
            light = row["light_chain_seq"].strip()
            score_text = row["binding_score"].strip()
            if not heavy or not light or not score_text:
                raise ValueError(f"incomplete assay row in {path}")
            sequences.append(f"{heavy}|{light}")
            outcomes.append(float(score_text))
    return sequences, outcomes


def unit_name(assay: str, strategy: str, seed: int) -> str:
    return f"{assay}__{strategy}__seed{seed}.json"
