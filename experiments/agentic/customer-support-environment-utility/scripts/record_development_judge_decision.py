#!/usr/bin/env python3
"""Record a human-reviewed decision about a development judge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--decision", choices=["accept", "abstain"], required=True)
    parser.add_argument("--confirm-reviewed-all-disagreements", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    report_path = arguments.report.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("automatic_qualification") is not False:
        raise SystemExit("calibration report has an invalid qualification marker")
    if arguments.decision == "accept":
        if report.get("status") != "MEETS_QUANTITATIVE_GATE__MANUAL_AUDIT_REQUIRED":
            raise SystemExit("cannot accept a judge that missed the quantitative gate")
        if not arguments.confirm_reviewed_all_disagreements:
            raise SystemExit("acceptance requires review of every disagreement")

    decision = {
        "schema_version": 1,
        "status": (
            "ACCEPTED_FOR_TRAIN_SIDE_DEVELOPMENT"
            if arguments.decision == "accept"
            else "DEVELOPMENT_JUDGE_ABSTAIN"
        ),
        "official_state_bench_compatible": False,
        "calibration_report_sha256": sha256(report_path),
        "panel_sha256": report["panel_sha256"],
        "judge_contract_sha256": report["judge_contract_sha256"],
        "reviewed_all_disagreements": bool(arguments.confirm_reviewed_all_disagreements),
        "disagreement_count": len(report["disagreements"]),
    }
    serialized = json.dumps(decision, indent=2, sort_keys=True) + "\n"
    if arguments.output.exists() and arguments.output.read_text(encoding="utf-8") != serialized:
        raise SystemExit(f"refusing to replace a different decision: {arguments.output}")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
