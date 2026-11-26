#!/usr/bin/env python3
"""Build prediction-time inputs and protected labels from the frozen corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "CORPUS_RECORDS.jsonl"
INPUTS = HERE / "MODEL_INPUTS.jsonl"
LABELS = HERE / "MODEL_LABELS.jsonl"
MANIFEST = HERE / "MODEL_VIEWS.json"

FORBIDDEN_FEATURE_KEYS = {
    "artifact",
    "candidate_id",
    "filename",
    "grouping",
    "lineage",
    "panel_id",
    "path",
    "record_id",
    "record_pointer",
    "seed",
    "source_id",
    "study_id",
    "training_run_id",
}
FORBIDDEN_KEY_FRAGMENTS = ("digest", "hash", "sha256")
NATIVE_DECISION_KEYS = {"frozen_prediction", "predicted_winner", "selected_candidate"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_line(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def join_key(record_id: str) -> str:
    return "record-" + sha256_bytes(record_id.encode())[:24]


def read_records() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line]


def forbidden_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in FORBIDDEN_FEATURE_KEYS
        or lowered in NATIVE_DECISION_KEYS
        or any(fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS)
    )


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize(child) for key, child in sorted(value.items()) if not forbidden_key(key)
        }
    if isinstance(value, list):
        return [sanitize(child) for child in value]
    return value


def model_input(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "join_key": join_key(record["record_id"]),
        "features": {
            "domain": record["domain"],
            "evidence_level": record["evidence_level"],
            "cost": sanitize(record["cost"]),
            "prediction_time": sanitize(record["prediction_time"]),
        },
    }


def model_label(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "join_key": join_key(record["record_id"]),
        "record_id": record["record_id"],
        "scoring": {
            "domain": record["domain"],
            "source_id": record["source_id"],
            "study_id": record["study_id"],
            "panel_id": record["panel_id"],
            "candidate_id": record["candidate_id"],
            "evidence_level": record["evidence_level"],
            "grouping": record["grouping"],
            "seed": record["seed"],
        },
        "outcome": record["outcome"],
        "cost": record["cost"],
    }


def render(records: list[dict[str, Any]]) -> tuple[bytes, bytes]:
    ordered = sorted(records, key=lambda row: row["record_id"])
    inputs = ("\n".join(canonical_line(model_input(row)) for row in ordered) + "\n").encode()
    labels = ("\n".join(canonical_line(model_label(row)) for row in ordered) + "\n").encode()
    return inputs, labels


def build_manifest(records: list[dict[str, Any]], inputs: bytes, labels: bytes) -> dict[str, Any]:
    return {
        "artifact": "anarres_surrogate_model_views_v1",
        "status": "released deterministic views; no trained cross-domain surrogate",
        "source": {
            "path": CORPUS.name,
            "sha256": sha256_bytes(CORPUS.read_bytes()),
        },
        "records": len(records),
        "records_by_domain": dict(sorted(Counter(row["domain"] for row in records).items())),
        "inputs": {
            "path": INPUTS.name,
            "sha256": sha256_bytes(inputs),
            "bytes": len(inputs),
            "model_views": ["metadata", "structured", "record_conditioned"],
        },
        "labels": {
            "path": LABELS.name,
            "sha256": sha256_bytes(labels),
            "bytes": len(labels),
            "access_rule": (
                "open training-fold labels for fitting; write held-out predictions before "
                "opening held-out labels for scoring"
            ),
        },
        "identity_rule": (
            "the opaque join_key is transport metadata only; resolvable identities and content "
            "hashes are absent from features"
        ),
        "outcome_rule": "native outcomes remain in the protected label view",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    records = read_records()
    inputs, labels = render(records)
    manifest = json.dumps(build_manifest(records, inputs, labels), indent=2) + "\n"
    expected = {INPUTS: inputs, LABELS: labels, MANIFEST: manifest.encode()}
    if args.check:
        stale = [
            path
            for path, content in expected.items()
            if not path.exists() or path.read_bytes() != content
        ]
        if stale:
            raise SystemExit("stale model views: " + ", ".join(str(path) for path in stale))
        return
    for path, content in expected.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
