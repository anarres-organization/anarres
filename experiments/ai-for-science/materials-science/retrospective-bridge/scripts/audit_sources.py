#!/usr/bin/env python3
"""Validate the public materials retrospective source ledger."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "SOURCES.json"
ALLOWED = {
    "included",
    "pending_numerical_reconciliation",
    "pending_result_artifact",
    "pending_numerical_extraction",
    "excluded_unverified_release",
    "context_only",
}


def validate() -> dict:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert payload["artifact"] == "materials_retrospective_source_audit_v1"
    sources = payload["sources"]
    assert len(sources) >= 8
    ids = [source["id"] for source in sources]
    assert len(ids) == len(set(ids))
    for source in sources:
        assert source["title"].strip()
        assert source["status"] in ALLOWED
        if source["status"] == "included":
            assert source.get("use")
            assert source.get("license")
        else:
            assert source.get("reason")
    return payload


if __name__ == "__main__":
    ledger = validate()
    counts: dict[str, int] = {}
    for source in ledger["sources"]:
        counts[source["status"]] = counts.get(source["status"], 0) + 1
    print(json.dumps({"sources": len(ledger["sources"]), "status_counts": counts}, indent=2))
