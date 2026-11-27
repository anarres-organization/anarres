#!/usr/bin/env python3
"""Run the frozen domain prompts through an OpenAI-compatible server."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "base_record_conditioned_model", HERE / "run_record_conditioned_model.py"
)
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

BASE.INPUTS = HERE / "DOMAIN_RECORD_CONDITIONED_INPUTS.jsonl"
BASE.CONTRACT = HERE / "DOMAIN_RECORD_CONDITIONED_CONTRACT.json"
BASE.DEFAULT_OUTPUT = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTIONS.jsonl"
BASE.DEFAULT_RECEIPT = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTION_RECEIPT.json"


if __name__ == "__main__":
    BASE.main()
