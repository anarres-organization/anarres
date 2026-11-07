#!/usr/bin/env python3
"""Audit a pinned public OSS Verify release without executing its proofs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

KNOWN_STATUSES = {
    "open",
    "proved",
    "refuted",
    "counterexample",
    "witnessed-false",
    "suspected-false",
    "model-gap",
    "withheld",
    "withdrawn",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AuditError(ValueError):
    """Raised when the pinned release contract is violated."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise AuditError(f"{path.name} is missing columns: {sorted(missing)}")
        return list(reader)


def top_scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*'?([^'\n]+)'?\s*$", text)
    if not match:
        raise AuditError(f"release.yaml is missing {key}")
    return match.group(1).strip()


def nested_scalar(text: str, section: str, key: str) -> str:
    pattern = rf"(?ms)^{re.escape(section)}:\s*$.*?^  {re.escape(key)}:\s*'?([^'\n]+)'?\s*$"
    match = re.search(pattern, text)
    if not match:
        raise AuditError(f"release.yaml is missing {section}.{key}")
    return match.group(1).strip()


def ensure_unique(rows: list[dict[str, str]], keys: tuple[str, ...], label: str) -> None:
    identities = [tuple(row[key] for key in keys) for row in rows]
    if len(identities) != len(set(identities)):
        raise AuditError(f"{label} contains duplicate identities")


def verify_artifacts(source: Path, pin: dict[str, Any]) -> list[dict[str, Any]]:
    verified = []
    for artifact in pin["artifacts"]:
        required_metadata = {
            "path",
            "uri",
            "bytes",
            "sha256",
            "media_type",
            "license",
            "producing_run_or_upstream_release",
        }
        missing_metadata = required_metadata - set(artifact)
        if missing_metadata:
            raise AuditError(f"pinned artifact is missing metadata: {sorted(missing_metadata)}")
        path = source / artifact["path"]
        if not path.is_file():
            raise AuditError(f"missing pinned artifact: {artifact['path']}")
        size = path.stat().st_size
        digest = file_sha256(path)
        if size != artifact["bytes"]:
            raise AuditError(f"size mismatch for {artifact['path']}: {size}")
        if digest != artifact["sha256"]:
            raise AuditError(f"SHA-256 mismatch for {artifact['path']}: {digest}")
        verified.append(
            {
                "path": artifact["path"],
                "bytes": size,
                "sha256": digest,
                "media_type": artifact["media_type"],
                "uri": artifact["uri"],
                "license": artifact["license"],
                "producing_run_or_upstream_release": artifact["producing_run_or_upstream_release"],
            }
        )
    return verified


def verify_revision(source: Path, pin: dict[str, Any]) -> str | None:
    expected = pin.get("commit")
    if expected is None:
        return None
    if not (source / ".git").exists():
        raise AuditError("the pinned source must be a Git checkout to verify its revision")
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    observed = result.stdout.strip()
    if observed != expected:
        raise AuditError(f"Git revision mismatch: expected {expected}, observed {observed}")
    return observed


def audit(source: Path, pin: dict[str, Any]) -> dict[str, Any]:
    revision = verify_revision(source, pin)
    verified = verify_artifacts(source, pin)
    release_text = (source / "release.yaml").read_text(encoding="utf-8")
    observed_release = {
        "release": top_scalar(release_text, "release"),
        "date": top_scalar(release_text, "date"),
        "semantics_commit": nested_scalar(release_text, "semantics", "commit"),
        "rocq_version": nested_scalar(release_text, "rocq", "version"),
        "checker_image": nested_scalar(release_text, "images", "checker"),
        "runner_image": nested_scalar(release_text, "images", "runner"),
    }
    expected_release = {
        "release": pin["release"],
        "date": pin["release_date"],
        "semantics_commit": pin["semantics"]["commit"],
        "rocq_version": pin["rocq"]["version"],
        "checker_image": pin["images"]["checker"],
        "runner_image": pin["images"]["runner"],
    }
    if observed_release != expected_release:
        raise AuditError(
            f"release metadata mismatch: expected {expected_release}, observed {observed_release}"
        )

    projects = load_rows(source / "index/projects.tsv", {"project"})
    harnesses = load_rows(source / "index/harnesses.tsv", {"project", "harness"})
    binaries = load_rows(
        source / "index/binaries.tsv",
        {"project", "harness", "build", "status", "bytes", "sha256"},
    )
    statements = load_rows(
        source / "index/statements.tsv",
        {"id", "kind", "status", "revision", "fingerprint", "proof"},
    )
    proofs = load_rows(
        source / "index/proofs.tsv",
        {"library", "entry_point", "statement", "kind", "proof", "statement_file"},
    )

    ensure_unique(projects, ("project",), "projects.tsv")
    ensure_unique(harnesses, ("project", "harness"), "harnesses.tsv")
    ensure_unique(binaries, ("project", "harness", "build"), "binaries.tsv")
    ensure_unique(statements, ("id",), "statements.tsv")
    ensure_unique(proofs, ("library", "entry_point", "statement"), "proofs.tsv")

    project_ids = {row["project"] for row in projects}
    entry_points = {(row["project"], row["harness"]) for row in harnesses}
    for row in harnesses:
        if row["project"] not in project_ids:
            raise AuditError(f"entry point refers to unknown project: {row}")
    for row in binaries:
        identity = (row["project"], row["harness"])
        if identity not in entry_points:
            raise AuditError(f"binary refers to unknown entry point: {row}")
        if row["status"] == "published":
            if not row["bytes"].isdigit() or int(row["bytes"]) <= 0:
                raise AuditError(f"published binary has invalid byte count: {row}")
            if not SHA256.fullmatch(row["sha256"]):
                raise AuditError(f"published binary has invalid SHA-256: {row}")

    statement_by_id: dict[str, dict[str, str]] = {}
    status_counts: Counter[str] = Counter()
    for row in statements:
        parts = row["id"].split("/")
        if len(parts) != 3 or (parts[0], parts[1]) not in entry_points:
            raise AuditError(f"statement has invalid entry-point identity: {row['id']}")
        if row["status"] not in KNOWN_STATUSES:
            raise AuditError(f"statement has unknown status: {row['status']}")
        if row["fingerprint"] != "-" and not SHA256.fullmatch(row["fingerprint"]):
            raise AuditError(f"statement has invalid fingerprint: {row['id']}")
        if not row["revision"].isdigit() or int(row["revision"]) < 1:
            raise AuditError(f"statement has invalid revision: {row['id']}")
        statement_by_id[row["id"]] = row
        status_counts[row["status"]] += 1

    proved_ids = set()
    proved_libraries = set()
    proved_entry_points = set()
    for row in proofs:
        identity = f"{row['library']}/{row['entry_point']}/{row['statement']}"
        statement = statement_by_id.get(identity)
        if statement is None:
            raise AuditError(f"proof refers to unknown statement: {identity}")
        if statement["status"] != "proved":
            raise AuditError(f"proof refers to non-proved statement: {identity}")
        proved_ids.add(identity)
        proved_libraries.add(row["library"])
        proved_entry_points.add((row["library"], row["entry_point"]))

    indexed_proved = {
        identity for identity, row in statement_by_id.items() if row["status"] == "proved"
    }
    if proved_ids != indexed_proved:
        raise AuditError("proofs.tsv and proved statement statuses disagree")

    counts = {
        "projects": len(projects),
        "entry_points": len(harnesses),
        "binaries": len(binaries),
        "statements": len(statements),
        "proofs": len(proofs),
        "proved_entry_points": len(proved_entry_points),
        "proved_libraries": len(proved_libraries),
        "statement_statuses": dict(sorted(status_counts.items())),
    }
    if counts != pin["expected_counts"]:
        raise AuditError(f"release counts differ from the pin: {counts}")

    pin_digest = hashlib.sha256(
        json.dumps(pin, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": "anarres.formal-verification-source-audit.v1",
        "source_id": pin["source_id"],
        "git_revision": revision,
        "source_pin_sha256": pin_digest,
        "release_metadata": observed_release,
        "counts": counts,
        "verified_artifacts": verified,
        "checks": {
            "artifact_identity": "pass",
            "git_revision": "pass" if revision else "not_pinned",
            "release_metadata": "pass",
            "index_schema": "pass",
            "referential_integrity": "pass",
            "proof_statement_consistency": "pass",
        },
        "qualification_state": "source_indexes_qualified",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    report = audit(args.source, pin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"qualified {report['counts']['statements']} statements and "
        f"{report['counts']['proofs']} proofs from {report['source_id']}"
    )


if __name__ == "__main__":
    main()
