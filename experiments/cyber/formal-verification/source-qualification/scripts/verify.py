#!/usr/bin/env python3
"""Validate the formal-verification source-qualification records.

The script checks record structure, cross-file consistency, the decision rule,
and the selection rule, then recomputes the committed summary byte for byte.
It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("SOURCES.json", "QUALIFICATION.json", "CANDIDATE_MATRIX.json")
SUMMARY = ROOT / "results" / "summary.json"

SOURCES_SCHEMA = "anarres.formal-verification-source-qualification-sources.v1"
QUALIFICATION_SCHEMA = "anarres.formal-verification-source-qualification.v1"
MATRIX_SCHEMA = "anarres.formal-verification-candidate-matrix.v1"

STATUSES = ("pass", "unresolved", "fail")
STATUS_RANK = {status: rank for rank, status in enumerate(STATUSES)}
BASES = ("confirmed", "inferred", "unknown")
DECISIONS = ("proceed", "reserve", "reject")
TIERS = ("source_selection", "panel_freeze", "record")
ENDPOINTS = (
    "proof_only",
    "code_and_proof",
    "specification_construction",
    "specification_faithfulness",
)
COST_BASES = ("measured", "published", "estimate")
SURVEY_CALLS = ("selected", "reserve", "reject", "merged")
CRITERIA = tuple(f"C{number}" for number in range(1, 9))
REVISION = re.compile(r"^[0-9a-f]{40}$")
ARXIV = re.compile(r"^\d{4}\.\d{4,5}$")
VERSION = re.compile(r"^v\d+$")

# Bracketed characters keep each pattern from matching its own source text.
FORBIDDEN_CONTENT = {
    "host home path": re.compile(r"/(?:Use[r]s|hom[e])/[A-Za-z0-9._-]+"),
    "temporary or scratch path": re.compile(r"/privat[e]/|/tm[p]/|scratchpa[d]"),
    "machine-specific storage path": re.compile(r"/(?:af[s]|df[s]|lf[s])/"),
    "cluster hostname": re.compile(r"\b(?:skamper[e]|hyperturin[g])[0-9]*\b", re.IGNORECASE),
    "Kerberos runtime configuration": re.compile(r"\bKRB5CCNAM[E]\b"),
    "private key": re.compile(r"BEGIN [A-Z ]*PRIVAT[E] KEY"),
    "API token": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})"),
    "credential assignment": re.compile(r"(?i)\b(?:api[_-]?key|secret|password)\s*[:=]\s*\S"),
}
SCANNED_SUFFIXES = {".json", ".md", ".py", ".txt"}


def canonical_json(value: Any) -> str:
    """Serialize one released artifact in its byte-stable form."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def load_records(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load the three qualification records."""
    loaded = [json.loads((root / name).read_text(encoding="utf-8")) for name in INPUTS]
    return loaded[0], loaded[1], loaded[2]


def input_digests(root: Path = ROOT) -> dict[str, str]:
    """Hash the exact input bytes that the summary depends on."""
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in INPUTS}


def worst(statuses: list[str]) -> str:
    """Return the most severe status in a non-empty list."""
    return max(statuses, key=STATUS_RANK.__getitem__)


def gate_tiers(qualification: dict[str, Any]) -> dict[str, str]:
    return {check["id"]: check["tier"] for check in qualification["gate"]}


def criterion_statuses(qualification: dict[str, Any], source: dict[str, Any]) -> dict[str, str]:
    """Apply the selection-rule mapping from gate checks to criteria."""
    return {
        criterion["id"]: worst([source["checks"][check]["status"] for check in criterion["checks"]])
        for criterion in qualification["selection_rule"]["criteria"]
    }


def open_checks(qualification: dict[str, Any], source: dict[str, Any], tier: str) -> list[str]:
    """List checks of one tier whose status is not pass."""
    tiers = gate_tiers(qualification)
    return sorted(
        check_id
        for check_id, check in source["checks"].items()
        if tiers.get(check_id) == tier and check["status"] != "pass"
    )


def derive_decision(qualification: dict[str, Any], source: dict[str, Any]) -> str:
    """Derive proceed, reserve, or reject from the source_selection checks."""
    tiers = gate_tiers(qualification)
    required = [
        check
        for check_id, check in source["checks"].items()
        if tiers.get(check_id) == "source_selection"
    ]
    if any(check["status"] == "fail" and not check.get("remediation") for check in required):
        return "reject"
    if any(check["status"] != "pass" for check in required):
        return "reserve"
    return "proceed"


def reserve_key(qualification: dict[str, Any], source: dict[str, Any]) -> tuple[Any, ...]:
    """Order reserve sources by failed criteria, open required checks, then open criteria."""
    criteria = criterion_statuses(qualification, source)
    return (
        sum(status == "fail" for status in criteria.values()),
        len(open_checks(qualification, source, "source_selection")),
        sum(status == "unresolved" for status in criteria.values()),
        source["source_id"],
    )


def compute_recommendation(qualification: dict[str, Any]) -> dict[str, Any]:
    """Apply the selection rule to the derived decisions."""
    decisions = {
        source["source_id"]: derive_decision(qualification, source)
        for source in qualification["sources"]
    }
    by_id = {source["source_id"]: source for source in qualification["sources"]}
    proceed = sorted(
        (
            len(open_checks(qualification, by_id[source_id], "panel_freeze")),
            source_id,
        )
        for source_id, decision in decisions.items()
        if decision == "proceed"
    )
    reserve = sorted(
        (source_id for source_id, decision in decisions.items() if decision == "reserve"),
        key=lambda source_id: reserve_key(qualification, by_id[source_id]),
    )
    selected = proceed[0][1] if proceed else None
    smoke_test_sources = [
        source_id
        for source_id in reserve
        if by_id[source_id]["checks"]["verifier_reproduced"]["status"] != "pass"
        and by_id[source_id]["checks"]["smoke_test_identified"]["status"] == "pass"
    ][:2]
    return {
        "outcome": "select" if proceed else "abstain",
        "selected_source": selected,
        "leading_candidate": selected or (reserve[0] if reserve else None),
        "reserve_ranking": reserve,
        "smoke_test_sources": smoke_test_sources,
    }


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def require_fields(record: dict[str, Any], fields: tuple[str, ...], where: str) -> list[str]:
    return [f"{where}: missing field {field}" for field in fields if field not in record]


def validate_basis(item: Any, where: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{where}: expected an object")
        return
    require(item.get("basis") in BASES, f"{where}: basis must be one of {BASES}", errors)


def validate_sources(sources: dict[str, Any], errors: list[str]) -> list[str]:
    require(sources.get("schema_version") == SOURCES_SCHEMA, "SOURCES: schema_version", errors)
    ids: list[str] = []
    for index, source in enumerate(sources.get("sources", [])):
        where = f"SOURCES[{source.get('source_id', index)}]"
        fields = (
            "source_id",
            "name",
            "setting",
            "papers",
            "repositories",
            "datasets",
            "checkpoints",
            "toolchains",
            "verifier",
            "training_code",
        )
        missing = require_fields(source, fields, where)
        errors.extend(missing)
        if missing:
            continue
        ids.append(source["source_id"])
        for group in ("papers", "repositories", "datasets", "checkpoints", "toolchains"):
            require(bool(source[group]), f"{where}: {group} must be non-empty", errors)
            for position, item in enumerate(source[group]):
                validate_basis(item, f"{where}.{group}[{position}]", errors)
        for paper in source["papers"]:
            if paper.get("arxiv") is not None:
                require(bool(ARXIV.match(paper["arxiv"])), f"{where}: arXiv id", errors)
                require(bool(VERSION.match(paper.get("version", ""))), f"{where}: version", errors)
                require(
                    paper.get("uri", "").endswith(f"{paper['arxiv']}{paper.get('version', '')}"),
                    f"{where}: paper URI must name the arXiv version",
                    errors,
                )
        for repository in source["repositories"]:
            require(
                bool(REVISION.match(repository.get("revision", ""))),
                f"{where}: repository revision must be a full commit hash",
                errors,
            )
            require(bool(repository.get("license")), f"{where}: repository license", errors)
        for key in ("identity", "entrypoint", "success_semantics"):
            require(bool(source["verifier"].get(key)), f"{where}: verifier {key}", errors)
        validate_basis(source["verifier"], f"{where}.verifier", errors)
        validate_basis(source["training_code"], f"{where}.training_code", errors)
    for finding in sources.get("findings", []):
        errors.extend(require_fields(finding, ("id", "summary", "action"), "SOURCES finding"))
        validate_basis(finding, f"SOURCES finding {finding.get('id')}", errors)
    require(len(ids) == len(set(ids)), "SOURCES: duplicate source_id", errors)
    return ids


def validate_source_qualification(
    qualification: dict[str, Any], source: dict[str, Any], errors: list[str]
) -> None:
    source_id = source.get("source_id")
    where = f"QUALIFICATION[{source_id}]"
    tiers = gate_tiers(qualification)
    start = len(errors)
    decision = source.get("decision")
    require(decision in DECISIONS, f"{where}: unknown decision {decision!r}", errors)
    require(bool(source.get("decision_reasons")), f"{where}: decision_reasons", errors)

    endpoints = source.get("endpoints", {})
    require(set(endpoints) == set(ENDPOINTS), f"{where}: endpoints must be {ENDPOINTS}", errors)
    for name, endpoint in endpoints.items():
        require(isinstance(endpoint.get("supported"), bool), f"{where}: endpoint {name}", errors)

    checks = source.get("checks", {})
    require(set(checks) == set(tiers), f"{where}: checks must cover every gate check", errors)
    for check_id, check in checks.items():
        require(check.get("status") in STATUSES, f"{where}.{check_id}: status", errors)
        evidence = check.get("evidence")
        require(bool(evidence), f"{where}.{check_id}: evidence", errors)
        for position, claim in enumerate(evidence or []):
            require(bool(claim.get("claim")), f"{where}.{check_id}[{position}]: claim", errors)
            validate_basis(claim, f"{where}.{check_id}[{position}]", errors)
    if len(errors) > start:
        return

    for check_id, check in checks.items():
        if check["status"] == "pass":
            require(
                any(claim.get("basis") == "confirmed" for claim in check["evidence"]),
                f"{where}.{check_id}: a pass needs at least one confirmed evidence claim",
                errors,
            )

    unresolved = source.get("unresolved_checks", [])
    entry_ids = [entry.get("id") for entry in unresolved]
    require(len(entry_ids) == len(set(entry_ids)), f"{where}: duplicate unresolved id", errors)
    for entry in unresolved:
        label = f"{where} unresolved {entry.get('id')}"
        check_id = entry.get("check")
        require(check_id in tiers, f"{label}: unknown check", errors)
        require(bool(entry.get("text")), f"{label}: text", errors)
        validate_basis(entry, label, errors)
        if check_id in tiers:
            require(
                entry.get("blocks") == tiers[check_id],
                f"{label}: blocks {entry.get('blocks')!r} but {check_id} is {tiers[check_id]}",
                errors,
            )
            require(
                checks[check_id]["status"] != "pass",
                f"{label}: {check_id} cannot pass while this entry is open",
                errors,
            )
    if len(errors) > start:
        return

    derived = derive_decision(qualification, source)
    require(
        derived == decision,
        f"{where}: recorded decision {decision!r} differs from derived decision {derived!r}",
        errors,
    )
    listed = {entry["check"] for entry in unresolved}
    for check_id in open_checks(qualification, source, "panel_freeze"):
        require(
            check_id in listed,
            f"{where}: open panel_freeze check {check_id} has no unresolved entry",
            errors,
        )
    if decision == "proceed":
        failed = [
            check_id
            for check_id, check in checks.items()
            if tiers[check_id] == "source_selection" and check["status"] == "fail"
        ]
        require(not failed, f"{where}: proceed with failed required gates {failed}", errors)
    else:
        require(bool(unresolved), f"{where}: {decision} requires unresolved_checks", errors)
        covered = {entry["check"] for entry in unresolved if entry["blocks"] == "source_selection"}
        for check_id in open_checks(qualification, source, "source_selection"):
            require(
                check_id in covered,
                f"{where}: open source_selection check {check_id} has no unresolved entry",
                errors,
            )


def validate_qualification(qualification: dict[str, Any], errors: list[str]) -> list[str]:
    start = len(errors)
    require(
        qualification.get("schema_version") == QUALIFICATION_SCHEMA,
        "QUALIFICATION: schema_version",
        errors,
    )
    require(
        qualification.get("endpoint_pooling_allowed") is False,
        "QUALIFICATION: endpoints must never be pooled",
        errors,
    )
    gate_ids = [check.get("id") for check in qualification.get("gate", [])]
    require(len(gate_ids) == len(set(gate_ids)), "QUALIFICATION: duplicate gate id", errors)
    for check in qualification.get("gate", []):
        require(check.get("tier") in TIERS, f"QUALIFICATION gate {check.get('id')}: tier", errors)
        require(bool(check.get("question")), f"QUALIFICATION gate {check.get('id')}", errors)
    criteria = qualification.get("selection_rule", {}).get("criteria", [])
    require(
        tuple(criterion.get("id") for criterion in criteria) == CRITERIA,
        "QUALIFICATION: selection rule must list criteria C1 to C8 in order",
        errors,
    )
    for criterion in criteria:
        for check in criterion.get("checks", []):
            require(
                gate_ids.count(check) == 1,
                f"QUALIFICATION {criterion.get('id')}: unknown check {check}",
                errors,
            )
            tier = gate_tiers(qualification).get(check)
            require(
                tier == "source_selection",
                f"QUALIFICATION {criterion.get('id')}: {check} must be source_selection",
                errors,
            )
    if len(errors) > start:
        return []

    ids: list[str] = []
    for source in qualification.get("sources", []):
        ids.append(source.get("source_id"))
        validate_source_qualification(qualification, source, errors)
    require(len(ids) == len(set(ids)), "QUALIFICATION: duplicate source_id", errors)
    if len(errors) > start:
        return ids

    recorded = qualification.get("recommendation", {})
    computed = compute_recommendation(qualification)
    for key, value in computed.items():
        require(
            recorded.get(key) == value,
            f"QUALIFICATION recommendation {key}: recorded {recorded.get(key)!r}, "
            f"rule gives {value!r}",
            errors,
        )
    by_id = {source["source_id"]: source for source in qualification["sources"]}
    smoke_tests = recorded.get("smoke_tests", [])
    require(
        [test.get("source_id") for test in smoke_tests] == computed["smoke_test_sources"],
        "QUALIFICATION: smoke tests must follow the smoke-test rule",
        errors,
    )
    require(1 <= len(smoke_tests) <= 2, "QUALIFICATION: recommend one or two smoke tests", errors)
    pilots = recorded.get("policy_pilots", [])
    leading = by_id.get(computed["leading_candidate"])
    needs_pilot = leading is not None and leading["checks"]["policy_headroom"]["status"] != "pass"
    require(
        [pilot.get("source_id") for pilot in pilots]
        == ([computed["leading_candidate"]] if needs_pilot else []),
        "QUALIFICATION: policy pilots must follow the policy-pilot rule",
        errors,
    )
    for pilot in pilots:
        require(
            "policy_headroom" in pilot.get("resolves", []),
            f"QUALIFICATION policy pilot {pilot.get('id')}: must resolve policy_headroom",
            errors,
        )
        require(pilot.get("opens_outcomes") is False, "QUALIFICATION: pilot opens outcomes", errors)
    for test in smoke_tests:
        label = f"QUALIFICATION smoke test {test.get('id')}"
        source = by_id.get(test.get("source_id"))
        require(source is not None, f"{label}: unknown source", errors)
        require(bool(test.get("resolves")), f"{label}: resolves", errors)
        require(bool(test.get("steps")), f"{label}: steps", errors)
        require(test.get("opens_outcomes") is False, f"{label}: must not open outcomes", errors)
        for check_id in test.get("resolves", []):
            status = (source or {}).get("checks", {}).get(check_id, {}).get("status")
            require(
                status in ("unresolved", "fail"),
                f"{label}: {check_id} is not an open check for its source",
                errors,
            )

    survey = qualification.get("fifth_source_survey", {}).get("entries", [])
    require(bool(survey), "QUALIFICATION: fifth_source_survey entries", errors)
    for entry in survey:
        label = f"QUALIFICATION survey {entry.get('name')}"
        require(entry.get("call") in SURVEY_CALLS, f"{label}: call", errors)
        require(bool(entry.get("reason")), f"{label}: reason", errors)
        if entry.get("conflict_of_interest"):
            require(entry["call"] != "selected", f"{label}: conflicted source selected", errors)
        if entry.get("call") == "merged":
            require(entry.get("merged_into") in ids, f"{label}: merged_into", errors)
    require(
        sum(entry.get("call") == "selected" for entry in survey) == 1,
        "QUALIFICATION: the survey selects exactly one fifth source",
        errors,
    )
    return ids


def validate_matrix(
    matrix: dict[str, Any], qualification: dict[str, Any], errors: list[str]
) -> list[str]:
    require(matrix.get("schema_version") == MATRIX_SCHEMA, "CANDIDATE_MATRIX: schema", errors)
    supported = {
        source.get("source_id"): {
            name
            for name, endpoint in source.get("endpoints", {}).items()
            if endpoint.get("supported") is True
        }
        for source in qualification.get("sources", [])
    }
    ids: list[str] = []
    for source in matrix.get("sources", []):
        source_id = source.get("source_id")
        where = f"CANDIDATE_MATRIX[{source_id}]"
        fields = (
            "native_unit",
            "independent_unit",
            "grouping_keys",
            "candidates",
            "simple_baseline",
            "held_out_boundary",
            "evidence_diversity_beyond_vero",
            "cost_estimates",
            "visible_published_outcomes",
            "proposed_held_out_decision",
        )
        missing = require_fields(source, fields, where)
        errors.extend(missing)
        if missing:
            continue
        ids.append(source_id)
        candidates = source["candidates"]
        candidate_ids = [candidate.get("id") for candidate in candidates]
        require(len(candidates) >= 3, f"{where}: at least three candidates", errors)
        require(len(candidate_ids) == len(set(candidate_ids)), f"{where}: duplicate id", errors)
        for candidate in candidates:
            validate_basis(candidate, f"{where} candidate {candidate.get('id')}", errors)
            panels = set(candidate.get("endpoint_panels", []))
            require(
                bool(panels) and panels <= supported.get(source_id, set()),
                f"{where} candidate {candidate.get('id')}: endpoint panels must be supported",
                errors,
            )
        baseline = source["simple_baseline"]
        require(
            bool(baseline and baseline.get("id") and baseline.get("definition")),
            f"{where}: simple baseline",
            errors,
        )
        require(
            isinstance(source["held_out_boundary"].get("official_split"), bool),
            f"{where}: held_out_boundary.official_split",
            errors,
        )
        require(bool(source["cost_estimates"]), f"{where}: cost estimates", errors)
        for cost in source["cost_estimates"]:
            require(cost.get("basis") in COST_BASES, f"{where}: cost basis", errors)
            require(bool(cost.get("item") and cost.get("value")), f"{where}: cost item", errors)
        require(bool(source["visible_published_outcomes"]), f"{where}: published outcomes", errors)
        for outcome in source["visible_published_outcomes"]:
            validate_basis(outcome, f"{where} published outcome", errors)
            require(bool(outcome.get("reference")), f"{where}: outcome reference", errors)
        decision = source["proposed_held_out_decision"]
        require(decision.get("status") == "proposed", f"{where}: decision status", errors)
        require(decision.get("outcome_opened") is False, f"{where}: outcome opened", errors)
    require(len(ids) == len(set(ids)), "CANDIDATE_MATRIX: duplicate source_id", errors)
    return ids


def scan_texts(texts: dict[str, str]) -> list[str]:
    """Report host paths, hostnames, and credentials in named texts."""
    problems = []
    for name, text in sorted(texts.items()):
        for description, pattern in FORBIDDEN_CONTENT.items():
            if pattern.search(text):
                problems.append(f"{description}: {name}")
    return problems


def scan_directory(root: Path = ROOT) -> list[str]:
    """Scan the released directory for machine-specific or secret content."""
    texts = {
        str(path.relative_to(root)): path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix in SCANNED_SUFFIXES
        and "__pycache__" not in path.relative_to(root).parts
    }
    return scan_texts(texts)


def validate(
    sources: dict[str, Any], qualification: dict[str, Any], matrix: dict[str, Any]
) -> list[str]:
    """Return every validation error across the three records."""
    errors: list[str] = []
    try:
        source_ids = validate_sources(sources, errors)
        qualification_ids = validate_qualification(qualification, errors)
        matrix_ids = validate_matrix(matrix, qualification, errors)
    except (AttributeError, KeyError, TypeError) as error:
        return [*errors, f"malformed record: {type(error).__name__}: {error}"]
    expected = set(source_ids)
    require(len(expected) in (4, 5), "evaluate four or five sources", errors)
    for name, ids in (("QUALIFICATION", qualification_ids), ("CANDIDATE_MATRIX", matrix_ids)):
        require(
            set(ids) == expected,
            f"{name} sources {sorted(set(ids))} differ from SOURCES {sorted(expected)}",
            errors,
        )
    return errors


def compute_summary(
    sources: dict[str, Any],
    qualification: dict[str, Any],
    matrix: dict[str, Any],
    digests: dict[str, str],
) -> dict[str, Any]:
    """Compute the compact released summary."""
    candidates = {source["source_id"]: len(source["candidates"]) for source in matrix["sources"]}
    names = {source["source_id"]: source["name"] for source in sources["sources"]}
    summary_sources = {}
    for source in qualification["sources"]:
        source_id = source["source_id"]
        criteria = criterion_statuses(qualification, source)
        statuses = [check["status"] for check in source["checks"].values()]
        bases = [
            claim["basis"] for check in source["checks"].values() for claim in check["evidence"]
        ]
        summary_sources[source_id] = {
            "name": names[source_id],
            "decision": derive_decision(qualification, source),
            "criteria": criteria,
            "failed_criteria": sum(status == "fail" for status in criteria.values()),
            "unresolved_criteria": sum(status == "unresolved" for status in criteria.values()),
            "open_source_selection_checks": open_checks(qualification, source, "source_selection"),
            "open_panel_freeze_checks": open_checks(qualification, source, "panel_freeze"),
            "check_status_counts": {status: statuses.count(status) for status in STATUSES},
            "evidence_basis_counts": {basis: bases.count(basis) for basis in BASES},
            "supported_endpoints": sorted(
                name for name, endpoint in source["endpoints"].items() if endpoint["supported"]
            ),
            "candidates": candidates[source_id],
            "unresolved_check_count": len(source["unresolved_checks"]),
        }
    survey = qualification["fifth_source_survey"]["entries"]
    return {
        "artifact": "formal_verification_source_qualification_summary_v1",
        "audit_date": qualification["audit_date"],
        "inputs_sha256": digests,
        "recommendation": compute_recommendation(qualification),
        "smoke_tests": [test["id"] for test in qualification["recommendation"]["smoke_tests"]],
        "sources": summary_sources,
        "survey_calls": {
            call: sum(entry["call"] == call for entry in survey) for call in SURVEY_CALLS
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite results/summary.json")
    arguments = parser.parse_args(argv)

    sources, qualification, matrix = load_records()
    errors = validate(sources, qualification, matrix) + scan_directory()
    if errors:
        print("source qualification records failed validation:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    serialized = canonical_json(compute_summary(sources, qualification, matrix, input_digests()))
    if arguments.write:
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(serialized, encoding="utf-8")
    elif not SUMMARY.exists() or SUMMARY.read_text(encoding="utf-8") != serialized:
        print("recomputed summary does not byte-match results/summary.json", file=sys.stderr)
        return 1
    recommendation = qualification["recommendation"]
    print(
        f"source qualification verified: {len(sources['sources'])} sources, "
        f"outcome {recommendation['outcome']}, "
        f"leading candidate {recommendation['leading_candidate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
