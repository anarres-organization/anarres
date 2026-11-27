#!/usr/bin/env python3
"""Build separated model inputs and labels for the domain-centered corpus."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("base_model_views", HERE / "build_model_views.py")
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

CORPUS = HERE / "DOMAIN_SURROGATE_RECORDS.jsonl"
INPUTS = HERE / "DOMAIN_MODEL_INPUTS.jsonl"
LABELS = HERE / "DOMAIN_MODEL_LABELS.jsonl"
MANIFEST = HERE / "DOMAIN_MODEL_VIEWS.json"


def build() -> dict[Path, bytes]:
    records = [json.loads(line) for line in CORPUS.read_text().splitlines() if line]
    inputs, labels = BASE.render(records)
    manifest = BASE.build_manifest(records, inputs, labels)
    manifest.update(
        {
            "artifact": "anarres_domain_surrogate_model_views_v1",
            "status": "development model views; no prospective result",
        }
    )
    manifest["source"]["path"] = CORPUS.name
    manifest["source"]["sha256"] = BASE.sha256_bytes(CORPUS.read_bytes())
    manifest["inputs"]["path"] = INPUTS.name
    manifest["labels"]["path"] = LABELS.name
    return {
        INPUTS: inputs,
        LABELS: labels,
        MANIFEST: (json.dumps(manifest, indent=2) + "\n").encode(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        stale = [path for path, content in expected.items() if path.read_bytes() != content]
        if stale:
            raise SystemExit("stale domain model views: " + ", ".join(map(str, stale)))
        return
    for path, content in expected.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
