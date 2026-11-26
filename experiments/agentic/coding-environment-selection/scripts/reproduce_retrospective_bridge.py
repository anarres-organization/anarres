#!/usr/bin/env python3
"""Recompute the cross-source agentic-coding evidence bridge."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "data" / "panels.json"
EXTERNAL = ROOT / "data" / "external-forecast-panels.json"
ADDITIONS = ROOT / "data" / "bridge-additions.json"
EXPECTED = ROOT / "results" / "retrospective-bridge-summary.json"


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def normalize_panel(panel: dict[str, object]) -> dict[str, object]:
    candidates = panel["candidates"]
    outcomes = {str(row["id"]): float(row["score"]) for row in candidates}
    measurements = {str(row["id"]): float(row["measurement_score"]) for row in candidates}
    return {
        "panel_id": panel["panel_id"],
        "source_id": panel["source_id"],
        "decision_id": panel.get("decision_id", panel["panel_id"]),
        "outcomes": outcomes,
        "measurements": measurements,
    }


def primary_panels(data: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for panel in data["panels"]:
        measurements = {}
        for candidate in panel["candidates"]:
            readiness = float(candidate["readiness"])
            measurements[str(candidate["id"])] = (
                float(candidate["reward_information"]) / float(candidate["cost"])
                if 0.10 <= readiness <= 0.85
                else -1.0
            )
        for endpoint, outcomes in panel["outcomes"].items():
            rows.append(
                {
                    "panel_id": f"{panel['panel_id']}__{endpoint}",
                    "source_id": panel["panel_id"].split("_")[0],
                    "decision_id": panel["panel_id"],
                    "outcomes": {key: 100 * float(value) for key, value in outcomes.items()},
                    "measurements": measurements,
                }
            )
    return rows


def external_panels(data: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for panel in data["panels"]:
        rows.append(
            {
                "panel_id": panel["panel_id"],
                "source_id": panel["source_id"],
                "decision_id": panel["panel_id"],
                "outcomes": {
                    str(candidate["id"]): float(candidate["score"])
                    for candidate in panel["candidates"]
                },
                "measurements": {
                    str(candidate["id"]): float(candidate["policy_aligned_progression"])
                    for candidate in panel["candidates"]
                },
            }
        )
    return rows


def pair_credit(predicted: float, observed: float) -> float:
    if observed == 0 or predicted == 0:
        return 0.5
    return float((predicted > 0) == (observed > 0))


def compute() -> dict[str, object]:
    panels = primary_panels(json.loads(PRIMARY.read_text()))
    panels.extend(external_panels(json.loads(EXTERNAL.read_text())))
    additions = json.loads(ADDITIONS.read_text())
    panels.extend(normalize_panel(panel) for panel in additions["panels"])

    pairwise = []
    regrets = []
    top_credits = []
    source_rows: dict[str, list[dict[str, float]]] = {}
    arm_rows = 0
    for panel in panels:
        outcomes = panel["outcomes"]
        measurements = panel["measurements"]
        arm_rows += len(outcomes)
        high_measurement = max(measurements.values())
        selected = [key for key, value in measurements.items() if value == high_measurement]
        best = max(outcomes.values())
        worst = min(outcomes.values())
        selected_outcome = sum(outcomes[key] for key in selected) / len(selected)
        normalized_regret = 0.0 if best == worst else (best - selected_outcome) / (best - worst)
        observed_best = {key for key, value in outcomes.items() if value == best}
        top_credit = len(observed_best.intersection(selected)) / len(selected)
        panel_pairs = []
        for left, right in itertools.combinations(outcomes, 2):
            credit = pair_credit(
                measurements[left] - measurements[right], outcomes[left] - outcomes[right]
            )
            pairwise.append(credit)
            panel_pairs.append(credit)
        regrets.append(normalized_regret)
        top_credits.append(top_credit)
        source_rows.setdefault(panel["source_id"], []).append(
            {
                "pairwise": sum(panel_pairs) / len(panel_pairs),
                "regret": normalized_regret,
                "top_credit": top_credit,
            }
        )

    by_source = {}
    for source, values in sorted(source_rows.items()):
        by_source[source] = {
            "endpoint_panels": len(values),
            "pairwise_ordering": round(sum(row["pairwise"] for row in values) / len(values), 6),
            "mean_normalized_regret": round(sum(row["regret"] for row in values) / len(values), 6),
            "top_choice_credit": round(sum(row["top_credit"] for row in values) / len(values), 6),
        }
    decision_ids = {(panel["source_id"], panel["decision_id"]) for panel in panels}
    return {
        "artifact": "agentic_coding_retrospective_bridge_summary_v1",
        "chronology": "retrospective bridge with one previously frozen RLVE block",
        "sources": len(source_rows),
        "independent_training_decisions": len(decision_ids),
        "endpoint_panels": len(panels),
        "candidate_endpoint_rows": arm_rows,
        "practical_measurement_rule": {
            "pairwise_ordering": round(sum(pairwise) / len(pairwise), 6),
            "mean_normalized_regret": round(sum(regrets) / len(regrets), 6),
            "top_choice_credit": round(sum(top_credits) / len(top_credits), 6),
        },
        "uninformed_tie": {
            "pairwise_ordering": 0.5,
            "mean_normalized_regret": round(
                sum(
                    (
                        max(panel["outcomes"].values())
                        - sum(panel["outcomes"].values()) / len(panel["outcomes"])
                    )
                    / (max(panel["outcomes"].values()) - min(panel["outcomes"].values()))
                    if max(panel["outcomes"].values()) != min(panel["outcomes"].values())
                    else 0.0
                    for panel in panels
                )
                / len(panels),
                6,
            ),
            "top_choice_credit": round(
                sum(
                    sum(
                        value == max(panel["outcomes"].values())
                        for value in panel["outcomes"].values()
                    )
                    / len(panel["outcomes"])
                    for panel in panels
                )
                / len(panels),
                6,
            ),
        },
        "by_source": by_source,
        "boundary": [
            "source-native measurements are mapped by meaning and outcomes are normalized "
            "only within panel",
            "nested endpoints do not become independent training decisions",
            "the bridge is primarily retrospective and does not qualify a universal coding "
            "selector",
        ],
    }


def main() -> None:
    actual = compute()
    if EXPECTED.exists() and actual != json.loads(EXPECTED.read_text()):
        raise SystemExit("recomputed bridge does not match released summary")
    print(canonical(actual), end="")


if __name__ == "__main__":
    main()
