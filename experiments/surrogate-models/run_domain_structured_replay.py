#!/usr/bin/env python3
"""Run structured baselines on the domain-centered development suites."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "base_structured_replay", HERE / "run_structured_replay.py"
)
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

BASE.INPUTS = HERE / "DOMAIN_MODEL_INPUTS.jsonl"
BASE.LABELS = HERE / "DOMAIN_MODEL_LABELS.jsonl"
BASE.VIEWS = HERE / "DOMAIN_MODEL_VIEWS.json"
BASE.SPLITS = HERE / "DOMAIN_SURROGATE_SPLITS.json"
BASE.PREDICTIONS = HERE / "DOMAIN_STRUCTURED_PREDICTIONS.jsonl"
BASE.FITS = HERE / "DOMAIN_STRUCTURED_FITS.json"
BASE.RESULTS = HERE / "DOMAIN_STRUCTURED_RESULTS.json"
BASE.PRIMARY_SUITES = {
    "controlled_leave_one_study_out",
    "coding_leave_one_decision_out",
    "materials_leave_one_study_out",
    "finance_leave_one_study_out",
}


def mark_domain_result(result: dict[str, object]) -> dict[str, object]:
    result["artifact"] = "anarres_domain_structured_surrogate_replay_v1"
    result["evidence_tier"] = "retrospective domain-centered development replay"
    result["claim_boundary"] = (
        "Development replay only. Mathematics is excluded from headline suites, localized "
        "regression models are scored separately, and this result cannot authorize a "
        "prospective deployment by itself."
    )
    BASE.RESULTS.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--predict", action="store_true")
    actions.add_argument("--score", action="store_true")
    actions.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.predict:
        print(json.dumps(BASE.predict(), indent=2, sort_keys=True))
    elif args.score:
        print(json.dumps(mark_domain_result(BASE.score()), indent=2, sort_keys=True))
    else:
        receipt = BASE.predict()
        print(json.dumps(mark_domain_result(BASE.score(receipt)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
