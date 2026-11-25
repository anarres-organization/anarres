"""Verify and read the released formal-verification public evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

PUBLIC_EVIDENCE = Path("experiments/cyber/formal-verification/public-evidence")
MANIFEST = "MANIFEST.sha256"
SOURCES = "SOURCES.json"
SUMMARY = "results/summary.json"
REPRODUCER = "scripts/reproduce.py"
TRUSTED_MANIFEST_SHA256 = "89d404d5fb0435d37bd2d413213f82b9b50d47ef9310965ffbfb7da60e3c07be"
COVERED_FILES = (
    SOURCES,
    SUMMARY,
    REPRODUCER,
    "data/anthropic-oss-fuzz.json",
    "data/dafny-synth.json",
    "data/formal-disco.json",
    "data/policy-support.json",
    "data/reform.json",
    "data/vericoding.json",
    "data/verusyn.json",
)

EVIDENCE_TIMING = ("prospective", "retrospective")
EVIDENCE_KINDS = (
    "development_qualification",
    "falsification",
    "positive_result",
    "production_target",
    "supporting_measurement",
)

# One record per released summary section. The class of each record is assigned
# here and checked against the vocabulary below rather than inferred from the
# numbers, so a later edit cannot silently relabel a falsification as a positive.
RECORDS = (
    {
        "record_id": "anthropic-production-target",
        "summary_key": "anthropic_production_target",
        "timing": "retrospective",
        "kind": "production_target",
        "sources": (
            "Anthropic formal software verification study",
            "Theorem OSS verification proofs",
            "Rocq Linux process semantics",
        ),
    },
    {
        "record_id": "dafny-synth-augmentation",
        "summary_key": "dafny_synth",
        "timing": "retrospective",
        "kind": "positive_result",
        "sources": ("dafny-annotator and DafnySynth",),
    },
    {
        "record_id": "formal-disco-generation",
        "summary_key": "formal_disco",
        "timing": "retrospective",
        "kind": "positive_result",
        "sources": ("Formal Disco",),
    },
    {
        "record_id": "reform-reward-integrity",
        "summary_key": "reform",
        "timing": "retrospective",
        "kind": "falsification",
        "sources": ("Re:Form",),
    },
    {
        "record_id": "vericoding-policy-support",
        "summary_key": "vericoding",
        "timing": "retrospective",
        "kind": "supporting_measurement",
        "sources": ("Vericoding Benchmark",),
    },
    {
        "record_id": "repository-policy-support",
        "summary_key": "policy_support",
        "timing": "retrospective",
        "kind": "supporting_measurement",
        "sources": ("LeanLean", "Forall VeriSoftBench", "Vero"),
    },
    {
        "record_id": "verusyn-target-matching",
        "summary_key": "verusyn",
        "timing": "retrospective",
        "kind": "positive_result",
        "sources": ("VeruSyn",),
    },
)


class EvidenceReportError(ValueError):
    """Raised when the released public evidence cannot be verified."""


def canonical_json(value: Any) -> str:
    """Serialize one released artifact in its byte-stable form."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def release_digest(path: Path) -> str:
    """Hash one release file with line endings normalized to LF.

    The manifest covers tracked text files. A Windows checkout that sets
    `core.autocrlf` rewrites those files to CRLF without changing their content,
    so the recorded digest would otherwise fail on that platform alone.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def evidence_root(repository: Path) -> Path:
    """Resolve the released public-evidence directory inside a checkout."""
    root = repository / PUBLIC_EVIDENCE
    if not (root / MANIFEST).is_file():
        raise EvidenceReportError(f"public evidence not found: {root}")
    return root


def verify_manifest(root: Path) -> dict[str, Any]:
    """Check the trusted manifest and every release file it covers."""
    manifest_path = root / MANIFEST
    actual_manifest = release_digest(manifest_path)
    if actual_manifest != TRUSTED_MANIFEST_SHA256:
        raise EvidenceReportError(f"{MANIFEST} does not match the adapter's trusted release")
    listed: dict[str, str] = {}
    # A manifest supplied with a checkout is data, not a path authorization.
    # Never resolve or hash a file outside the released evidence directory.
    resolved_root = root.resolve()
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        recorded, separator, name = line.partition("  ")
        if not separator or re.fullmatch(r"[0-9a-f]{64}", recorded) is None or not name.strip():
            raise EvidenceReportError(f"unreadable {MANIFEST} line: {line!r}")
        relative = name.strip()
        path = Path(relative)
        resolved = (root / path).resolve()
        if path.is_absolute() or not resolved.is_relative_to(resolved_root):
            raise EvidenceReportError(f"{relative} escapes the {MANIFEST} root")
        normalized = path.as_posix()
        if normalized in listed:
            raise EvidenceReportError(f"duplicate manifest path: {normalized}")
        if not resolved.is_file():
            raise EvidenceReportError(f"{relative} is listed in {MANIFEST} and missing")
        actual = release_digest(resolved)
        if actual != recorded:
            raise EvidenceReportError(f"{relative} does not match {MANIFEST}")
        listed[normalized] = recorded
    absent = [relative for relative in COVERED_FILES if relative not in listed]
    if absent:
        raise EvidenceReportError(f"{MANIFEST} does not cover {absent}")
    return {
        "file": MANIFEST,
        "sha256": "sha256:" + actual_manifest,
        "files_verified": len(listed),
        "verification": "sha256_matched",
    }


def load_sources(root: Path) -> dict[str, dict[str, Any]]:
    """Load the pinned provenance of each released source."""
    document = json.loads((root / SOURCES).read_text(encoding="utf-8"))
    sources = {}
    for source in document.get("sources", []):
        name = source.get("name")
        if not isinstance(name, str) or not name.strip():
            raise EvidenceReportError(f"{SOURCES} has a source without a name")
        if name in sources:
            raise EvidenceReportError(f"duplicate source name in {SOURCES}: {name}")
        revision = source.get("revision")
        if revision is None and source.get("release_date") is None:
            raise EvidenceReportError(f"source '{name}' has neither a revision nor a release date")
        if revision is not None and (
            not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None
        ):
            raise EvidenceReportError(f"source '{name}' does not pin a 40-character revision")
        sources[name] = source
    if not sources:
        raise EvidenceReportError(f"{SOURCES} pins no sources")
    return sources


def load_summary(root: Path) -> tuple[dict[str, Any], str]:
    """Read the manifest-verified released summary without executing checkout code."""
    path = root / SUMMARY
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceReportError(f"cannot read {SUMMARY}: {error}") from error
    if not isinstance(summary, dict):
        raise EvidenceReportError(f"{SUMMARY} must contain a JSON object")
    return summary, "sha256:" + release_digest(path)


def source_record(name: str, source: dict[str, Any]) -> dict[str, Any]:
    """Preserve one published source's revision, references, and artifact digests."""
    artifacts = []
    for key in ("result_artifact", "result_artifacts"):
        value = source.get(key)
        if value is None:
            continue
        for artifact in value if isinstance(value, list) else (value,):
            artifacts.append(
                {
                    "path": artifact["path"],
                    "sha256": "sha256:" + artifact["sha256"],
                    "size_bytes": artifact.get("size_bytes"),
                }
            )
    references = {
        key: source[key]
        for key in ("uri", "paper", "repository")
        if isinstance(source.get(key), str)
    }
    return {
        "name": name,
        "references": references,
        "revision": source.get("revision"),
        "release_date": source.get("release_date"),
        "license": source.get("repository_license") or source.get("license"),
        "upstream_artifacts": artifacts,
        "redistribution": source.get("redistribution"),
    }


def build_records(
    summary: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Pair each released summary section with its class and its provenance."""
    records = []
    covered = set()
    for spec in RECORDS:
        key = spec["summary_key"]
        if key not in summary:
            raise EvidenceReportError(f"released summary has no section '{key}'")
        if spec["timing"] not in EVIDENCE_TIMING or spec["kind"] not in EVIDENCE_KINDS:
            raise EvidenceReportError(f"record '{spec['record_id']}' has an unlisted class")
        provenance = []
        for name in spec["sources"]:
            if name not in sources:
                raise EvidenceReportError(
                    f"record '{spec['record_id']}' cites unknown source '{name}'"
                )
            provenance.append(source_record(name, sources[name]))
            covered.add(name)
        records.append(
            {
                "record_id": spec["record_id"],
                "summary_key": key,
                "timing": spec["timing"],
                "kind": spec["kind"],
                "outcome": summary[key],
                "sources": provenance,
            }
        )
    uncovered = sorted(set(sources) - covered)
    if uncovered:
        raise EvidenceReportError(f"sources without a released record: {uncovered}")
    return records


def evidence_classes(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Report which labels this release uses and where the others are reported."""
    counts: dict[tuple[str, str], int] = {}
    for record in records:
        key = (record["timing"], record["kind"])
        counts[key] = counts.get(key, 0) + 1
    return {
        "timing": list(EVIDENCE_TIMING),
        "kind": list(EVIDENCE_KINDS),
        "present": [
            {"timing": timing, "kind": kind, "records": count}
            for (timing, kind), count in sorted(counts.items())
        ],
        "absent": [
            {
                "timing": "prospective",
                "records": 0,
                "reported_by": "no released prospective panel in this evidence release",
            },
            {
                "kind": "development_qualification",
                "records": 0,
                "reported_by": "anarres formal qualification --repository .",
            },
        ],
    }


def build_report(repository: Path) -> dict[str, Any]:
    """Verify the released public evidence and explain what each source establishes."""
    root = evidence_root(repository)
    manifest = verify_manifest(root)
    sources = load_sources(root)
    summary, summary_digest = load_summary(root)
    records = build_records(summary, sources)
    return {
        "artifact": "anarres.formal-verification-public-evidence-report.v1",
        "status": "verified",
        "role": "read_only_public_evidence",
        "evidence_classes": evidence_classes(records),
        "records": records,
        "summary": summary,
        "summary_digest": summary_digest,
        "summary_verified_by_manifest": True,
        "manifest": manifest,
        "sources_file": {
            "file": SOURCES,
            "sha256": digest(root / SOURCES),
            "sources": len(sources),
        },
        "boundaries": {
            "retrospective_and_external": True,
            "contains_prospective_forecast": False,
            "creates_environment_profile": False,
            "ranks_candidates": False,
            "authorizes_training": False,
            "pools_scores_across_sources": False,
            "reported_separately_from": [
                "source-qualification",
                "runtime-qualification",
                "qualification-report",
            ],
        },
    }
