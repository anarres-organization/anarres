#!/usr/bin/env python3
"""Audit the training-visible portion of the pinned PhononScore release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

EXPECTED_ROLES = {
    "gradient_train": 7809,
    "checkpoint_validation": 411,
    "unused_rounding": 1,
}
SEALED_DIRECTORIES = ("validation_mp20", "test_mp20", "test_dft_pbe")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    index = round(probability * (len(values) - 1))
    return values[index]


def formula_elements(formula: str) -> set[str]:
    return set(re.findall(r"[A-Z][a-z]?", formula))


def load_labels(path: Path) -> dict[str, float]:
    labels: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) != 2:
                raise ValueError(f"Malformed label row: {row!r}")
            identity, value = row
            if identity in labels:
                raise ValueError(f"Duplicate label identity: {identity}")
            labels[identity] = float(value)
    return labels


def audit(data_root: Path) -> dict[str, object]:
    stage = data_root / "dft_posttrain"
    manifest_path = stage / "manifest.json"
    labels_path = stage / "id_prop.csv"
    split_audit_path = data_root / "splits" / "split_audit.json"
    required = (manifest_path, labels_path, split_audit_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    labels = load_labels(labels_path)
    upstream_audit = json.loads(split_audit_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise TypeError("DFT post-training manifest must be a list")

    record_ids = [row["record_id"] for row in manifest]
    cif_ids = [row["id"] for row in manifest]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("record_id values are not unique")
    if len(cif_ids) != len(set(cif_ids)):
        raise ValueError("CIF identities are not unique")
    if set(cif_ids) != set(labels):
        raise ValueError("Manifest and label-file CIF identities differ")

    label_mismatches = 0
    missing_cifs: list[str] = []
    for row in manifest:
        if not math.isclose(
            float(row["min_frequency"]), labels[row["id"]], rel_tol=0.0, abs_tol=1e-9
        ):
            label_mismatches += 1
        if not (stage / row["cif_path"]).is_file():
            missing_cifs.append(row["record_id"])
    if label_mismatches:
        raise ValueError(f"Found {label_mismatches} manifest/label mismatches")
    if missing_cifs:
        raise FileNotFoundError(f"Missing {len(missing_cifs)} CIF files")

    roles = Counter(row["role"] for row in manifest)
    if dict(roles) != EXPECTED_ROLES:
        raise ValueError(f"Unexpected role counts: {dict(roles)}")
    training = [row for row in manifest if row["role"] == "gradient_train"]
    frequencies = sorted(float(row["min_frequency"]) for row in training)
    formulas = Counter(row["formula_reduced"] for row in training)
    elements: Counter[str] = Counter()
    for row in training:
        elements.update(formula_elements(row["formula_reduced"]))

    extracted_sealed = [name for name in SEALED_DIRECTORIES if (data_root / name).exists()]
    observed_manifest_sha = sha256(manifest_path)
    declared_manifest_sha = upstream_audit["source_hashes"]["dft_posttrain"]["manifest_sha256"]
    return {
        "schema_version": "1.0",
        "scope": "training-visible PhononScore DFT post-training source",
        "external_test_labels_inspected": False,
        "source_files": {
            "manifest_sha256": observed_manifest_sha,
            "labels_sha256": sha256(labels_path),
            "config_sha256": sha256(stage / "config_min_phonon.json"),
            "upstream_declared_manifest_sha256": declared_manifest_sha,
            "upstream_manifest_digest_matches": observed_manifest_sha == declared_manifest_sha,
        },
        "inventory": {
            "records": len(manifest),
            "cifs": len(cif_ids),
            "labels": len(labels),
            "roles": dict(sorted(roles.items())),
            "missing_cifs": len(missing_cifs),
            "label_mismatches": label_mismatches,
        },
        "gradient_training_pool": {
            "records": len(training),
            "unique_reduced_formulas": len(formulas),
            "duplicate_formula_rows": sum(count - 1 for count in formulas.values()),
            "unique_elements": len(elements),
            "stable_at_minus0p1": sum(bool(row["stable_at_minus0p1"]) for row in training),
            "unstable_at_minus0p1": sum(not bool(row["stable_at_minus0p1"]) for row in training),
            "minimum_frequency_quantiles": {
                str(probability): quantile(frequencies, probability)
                for probability in (0.0, 0.01, 0.05, 0.1, 0.5, 0.9, 0.99, 1.0)
            },
        },
        "sealed_boundary": {
            "expected_directories": list(SEALED_DIRECTORIES),
            "extracted_directories": extracted_sealed,
            "passes": not extracted_sealed,
        },
        "qualification": {
            "content_integrity": "pass",
            "sealed_boundary": "pass" if not extracted_sealed else "fail",
            "upstream_manifest_digest": (
                "pass" if observed_manifest_sha == declared_manifest_sha else "open"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit(args.data_root)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
