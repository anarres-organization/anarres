#!/usr/bin/env python3
"""Fit matched text baselines on the balanced domain panel sample."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DOMAIN = load(
    "build_domain_record_conditioned_replay", HERE / "build_domain_record_conditioned_replay.py"
)
BASE = load("base_matched_text_baselines", HERE / "run_matched_text_baselines.py")

BASE.replay = SimpleNamespace(
    aggregate=DOMAIN.selected_aggregate,
    environment=DOMAIN.environment,
    intervention=DOMAIN.intervention,
)
BASE.CONTRACT = HERE / "DOMAIN_RECORD_CONDITIONED_CONTRACT.json"
BASE.OUTPUT = HERE / "DOMAIN_MATCHED_TEXT_BASELINE_RESULTS.json"


def fixed_parameter(_rows, _measurements, family, _parameters):
    contract = json.loads(BASE.CONTRACT.read_text())
    settings = contract["matched_text_baselines"]
    return (
        float(settings["tfidf_ridge_alpha"])
        if family == "ridge"
        else float(settings["tfidf_knn_neighbors"])
    )


BASE.select_parameter = fixed_parameter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        raise SystemExit("Pass --run to fit and score the frozen text baselines.")
    result = BASE.run()
    result["artifact"] = "anarres_domain_matched_text_baselines_v1"
    result["claim_boundary"] = (
        "Retrospective development baselines on the outcome-blind balanced panel sample. "
        "They are not prospective evidence."
    )
    BASE.OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
