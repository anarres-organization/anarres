"""Export one environment-profile input per (subject, candidate environment) from saved scores."""
# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF_URI = "https://github.com/anarres-organization/anarres/blob/health-mental-health-20261116/docs/conventions/health-mental-support-checkability-v1.md"
SUBJECTS = {
    "grok": {
        "id": "grok-4.7",
        "kind": "assistant-model",
        "harness": "plan router, personal-grok native read-only job",
    },
    "claude": {
        "id": "claude-sonnet-5-5",
        "kind": "assistant-model",
        "harness": "Claude Code subagent",
    },
}


def coordinate(
    name: str, role: str, value: float, unit: str, direction: str, estimator: str, count: int
) -> dict:
    return {
        "name": name,
        "definition": {"uri": f"{DEF_URI}#{name}", "revision": "v1-development"},
        "role": role,
        "value": round(value, 6),
        "unit": unit,
        "direction": direction,
        "estimator": estimator,
        "sample_count": count,
    }


def build(policy: str, panel: str, scores: dict, instrument_words: float | None) -> dict:
    s = scores[policy]
    if panel == "instrument":
        block = s["instrument"]
        deterministic, words, kind = 1.0, instrument_words, "exact"
        check = {
            "check_id": "verifier-controls",
            "category": "verifier",
            "status": "pass",
            "severity": "error",
            "summary": "Exact scorer accepted 24 of 24 gold answers and rejected 24 of 24 corrupted copies.",
        }
    else:
        block = s["safety_all"]
        deterministic, words, kind = 0.0, s["mean_reply_words"], "lexical"
        check = {
            "check_id": "verifier-validity",
            "category": "verifier",
            "status": "unknown",
            "severity": "warning",
            "summary": "Lexical proxy. It matched 20 of 24 construction labels on fictional replies and is not an exact verifier.",
        }
    invalid = block["n"] - block["valid"]
    return {
        "schema_version": "anarres.environment-profile-input.v1",
        "environment_id": f"mh-{panel}-{policy}",
        "domain": "health-mental-support",
        "subject": {
            "kind": SUBJECTS[policy]["kind"],
            "id": SUBJECTS[policy]["id"],
            "revision": "2026-11-16",
        },
        "producer": {
            "kind": "study-script",
            "id": "mental-health-checkability-v1",
            "revision": "v1",
        },
        "source": {
            "uri": "fixture://health/mental-health-checkability-v1",
            "revision": "v1",
            "license": "CC0-1.0",
        },
        "measurement_contract": {
            "kind": "mental-support-rule-verifier-probe",
            "id": "mental-health-checkability-v1",
            "revision": "v1",
            "repetitions": 1,
            "cost_unit": "response_words",
        },
        "qualification_checks": [
            check,
            {
                "check_id": "missingness-audited",
                "category": "measurement",
                "status": "pass",
                "severity": "error",
                "summary": f"{invalid} of {block['n']} attempts were unparseable and are reported as missing, not as failures.",
            },
        ],
        "coordinates": [
            coordinate(
                "verifier_pass_fraction",
                "signal",
                block["pass"] / block["valid"],
                "fraction",
                "contextual",
                f"passes divided by valid attempts under the {kind} verifier",
                block["valid"],
            ),
            coordinate(
                "deterministic_criteria_fraction",
                "coverage",
                deterministic,
                "fraction",
                "higher",
                "fraction of rubric criteria checked by an exact verifier",
                block["n"],
            ),
            coordinate(
                "mean_response_words",
                "cost",
                words,
                "response_words",
                "lower",
                "arithmetic mean over valid responses",
                block["valid"],
            ),
            coordinate(
                "missingness_rate",
                "reliability",
                invalid / block["n"],
                "fraction",
                "lower",
                "unparseable attempts divided by attempts",
                block["n"],
            ),
        ],
        "attributes": {
            "synthetic_fixture": True,
            "evidence_tier": "exploratory",
            "panel": panel,
            "verifier_kind": kind,
        },
    }


def build_split(policy: str, risk: str, scores: dict) -> dict:
    """Two safety candidate environments share one verifier, so their coordinates are comparable."""
    from score_runs import RAW, jsonl_text

    block = scores[policy]["safety_crisis" if risk == "crisis_cue" else "safety_control"]
    prefix = "B-CRISIS" if risk == "crisis_cue" else "B-CONTROL"
    replies = {}
    for part in ("1", "2"):
        replies.update(jsonl_text(RAW / f"{policy}_policy_safety_{part}.jsonl"))
    words = [len(r["reply"].split()) for k, r in replies.items() if k.startswith(prefix)]
    doc = build(
        policy,
        "safety",
        {
            policy: {
                **scores[policy],
                "safety_all": block,
                "mean_reply_words": sum(words) / len(words),
            }
        },
        None,
    )
    doc["environment_id"] = f"mh-safety-{'crisis' if risk == 'crisis_cue' else 'control'}-{policy}"
    doc["attributes"]["panel"] = f"safety-{risk}"
    return doc


def main() -> None:
    scores = json.loads((ROOT / "results" / "e2_policy_scores.json").read_text())
    out = ROOT / "results" / "profile-inputs"
    out.mkdir(exist_ok=True)
    for policy in SUBJECTS:
        # Instrument answers are short JSON lines, so words are the JSON text length in words.
        raw = (
            (ROOT / "results" / "raw" / f"{policy}_policy_instrument.jsonl")
            .read_text()
            .splitlines()
        )
        words = sum(len(line.split()) for line in raw if line.startswith("{")) / max(
            1, sum(line.startswith("{") for line in raw)
        )
        for panel in ("instrument", "safety"):
            doc = build(policy, panel, scores, words)
            (out / f"{panel}-{policy}.profile-input.json").write_text(
                json.dumps(doc, indent=2) + "\n"
            )
        for risk in ("crisis_cue", "no_risk"):
            doc = build_split(policy, risk, scores)
            (out / f"{doc['environment_id'].replace('mh-', '')}.profile-input.json").write_text(
                json.dumps(doc, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
