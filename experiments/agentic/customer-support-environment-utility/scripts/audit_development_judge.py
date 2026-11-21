#!/usr/bin/env python3
"""Compare local development scores with a frozen official-score panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def summarize(pairs: list[tuple[int, int]]) -> dict[str, Any]:
    names = {
        (0, 0): "official_fail_local_fail",
        (0, 1): "official_fail_local_pass",
        (1, 0): "official_pass_local_fail",
        (1, 1): "official_pass_local_pass",
    }
    counts = {name: 0 for name in names.values()}
    for official, local in pairs:
        counts[names[(official, local)]] += 1
    agreement = counts["official_fail_local_fail"] + counts["official_pass_local_pass"]
    official_failures = counts["official_fail_local_fail"] + counts["official_fail_local_pass"]
    return {
        "n": len(pairs),
        "agreement": rate(agreement, len(pairs)),
        "false_pass_rate": rate(counts["official_fail_local_pass"], official_failures),
        "confusion": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--official-results-dir", type=Path, required=True)
    parser.add_argument("--development-scores-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    panel_path = arguments.panel.resolve()
    official_root = arguments.official_results_dir.resolve()
    local_root = arguments.development_scores_dir.resolve()
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    if panel.get("status") != "DEVELOPMENT_JUDGE_CALIBRATION_FROZEN":
        raise SystemExit("panel is not frozen")
    claimed_panel_digest = panel.get("panel_sha256")
    unhashed_panel = {key: value for key, value in panel.items() if key != "panel_sha256"}
    if claimed_panel_digest != canonical_digest(unhashed_panel):
        raise SystemExit("frozen panel digest does not match its contents")

    pairs = []
    by_type: dict[str, list[tuple[int, int]]] = defaultdict(list)
    disagreements = []
    contract_hashes = set()
    for entry in panel["entries"]:
        relative = Path(entry["trajectory_relative_path"])
        official_path = official_root / relative
        local_path = local_root / relative
        if not official_path.is_file() or not local_path.is_file():
            raise SystemExit(f"missing calibration evidence for {relative}")
        if sha256(official_path) != entry["trajectory_sha256"]:
            raise SystemExit(f"official trajectory changed after panel freeze: {relative}")
        official_record = json.loads(official_path.read_text(encoding="utf-8"))
        local_record = json.loads(local_path.read_text(encoding="utf-8"))
        if local_record.get("official_state_bench_compatible") is not False:
            raise SystemExit(f"local score has an invalid scope marker: {relative}")
        if local_record.get("task_id") != entry["task_id"]:
            raise SystemExit(f"local task identity mismatch: {relative}")
        if local_record.get("trajectory", {}).get("sha256") != entry["trajectory_sha256"]:
            raise SystemExit(f"local score is bound to different evidence: {relative}")
        if local_record.get("task_definition_sha256") != entry["task_definition_sha256"]:
            raise SystemExit(f"local score is bound to a different task definition: {relative}")
        if local_record.get("source_revision") != panel["source_revision"]:
            raise SystemExit(f"local score uses a different source revision: {relative}")
        contract_hashes.add(local_record["judge_contract"]["contract_sha256"])
        official = official_record.get("task_requirements_met")
        local = local_record.get("scores", {}).get("task_requirements_met")
        if official not in {0, 1} or local not in {0, 1}:
            raise SystemExit(f"non-binary calibration score: {relative}")
        pair = (official, local)
        pairs.append(pair)
        by_type[entry["task_type"]].append(pair)
        if official != local:
            disagreements.append(
                {
                    "run_index": entry["run_index"],
                    "task_id": entry["task_id"],
                    "task_type": entry["task_type"],
                    "official_task_requirements_met": official,
                    "local_task_requirements_met": local,
                    "official_details": official_record.get("task_requirements_details"),
                    "local_details": local_record["scores"].get("task_requirements_details"),
                }
            )
    if len(contract_hashes) != 1:
        raise SystemExit("calibration sidecars use multiple judge contracts")

    overall = summarize(pairs)
    gate = panel["acceptance_gate"]
    quantitative = (
        overall["agreement"] is not None
        and overall["agreement"] >= gate["task_requirement_agreement_minimum"]
        and overall["false_pass_rate"] is not None
        and overall["false_pass_rate"] <= gate["false_pass_rate_maximum"]
    )
    report = {
        "schema_version": 1,
        "status": (
            "MEETS_QUANTITATIVE_GATE__MANUAL_AUDIT_REQUIRED"
            if quantitative
            else "DEVELOPMENT_JUDGE_ABSTAIN"
        ),
        "automatic_qualification": False,
        "panel_sha256": panel["panel_sha256"],
        "judge_contract_sha256": next(iter(contract_hashes)),
        "overall": overall,
        "by_task_type": {name: summarize(values) for name, values in sorted(by_type.items())},
        "disagreements": disagreements,
        "acceptance_gate": gate,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
