#!/usr/bin/env python3
"""Instantiate the frozen 14B forecast after, and only after, Stage D passes."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path


SHORT = {
    "high_mixed_high_adm": "HH", "high_mixed_low_adm": "HL",
    "low_mixed_high_adm": "LH", "low_mixed_low_adm": "LL",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def predict(freeze: dict, cell: dict, tokens: int) -> float:
    f = freeze["formula"]
    b0, bn, bs, bt, ba = f["coefficients"]
    x = f["x_scale_14b"]
    s = tokens / (tokens + f["budget_reference_tokens"])
    st = f["standardizers"]
    zt = (math.log(cell["mean_tokens"]) - st["log_mean_tokens"]["mean"]) / st["log_mean_tokens"]["sd"]
    za = (cell["admissibility"] - st["p_admissible"]["mean"]) / st["p_admissible"]["sd"]
    return b0 + bn*x + bs*s + bt*s*zt + ba*s*za


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictor-freeze", required=True, type=Path)
    ap.add_argument("--stage-d-decision", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    freeze = json.loads(args.predictor_freeze.read_text())
    decision = json.loads(args.stage_d_decision.read_text())
    if freeze["status"] != "FROZEN_BEFORE_14B_MEASUREMENT_AND_RL":
        raise RuntimeError("predictor family is not frozen")
    if decision.get("status") != "PROMOTE" or not decision.get("rl_launch_permitted"):
        raise RuntimeError("14B Stage D did not promote")
    cells = {SHORT[x["cell"]]: x for x in decision["cells"]}
    if set(cells) != {"HH", "HL", "LH", "LL"}:
        raise RuntimeError("unexpected Stage-D cell set")
    if not all(x.get("integrity_pass") for x in cells.values()):
        raise RuntimeError("Stage-D integrity did not pass")

    half = freeze["primary_uncertainty"]["half_width_pp"] / 100.0
    predictions = []
    rankings = []
    pairwise = []
    for tokens in freeze["forecast_grid_generated_action_tokens"]:
        values = {cell: predict(freeze, payload, tokens) for cell,payload in cells.items()}
        ranking = sorted(values, key=lambda cell: (-values[cell], cell))
        rankings.append({"generated_action_tokens": tokens, "best_to_worst": ranking,
                         "predicted_best": ranking[0]})
        for cell in sorted(values):
            predictions.append({
                "cell": cell, "generated_action_tokens": tokens,
                "predicted_utility_fraction": values[cell],
                "predicted_utility_pp": 100*values[cell],
                "primary_curve_envelope_pp": [100*(values[cell]-half), 100*(values[cell]+half)],
            })
        for left,right in itertools.combinations(sorted(values),2):
            pairwise.append({"generated_action_tokens": tokens, "left": left, "right": right,
                             "predicted_left_minus_right_pp": 100*(values[left]-values[right])})

    result = {
        "schema": "paper1-14b-v4-numerical-forecast-v1",
        "status": "FROZEN_BEFORE_14B_RL",
        "uses_14b_rl_outcomes": False,
        "predictor_family": {"path": str(args.predictor_freeze), "sha256": sha256(args.predictor_freeze)},
        "confirmed_prerl_stage_d": {"path": str(args.stage_d_decision), "sha256": sha256(args.stage_d_decision)},
        "confirmed_prerl_cells": cells,
        "predictions": predictions,
        "rankings": rankings,
        "pairwise_predictions": pairwise,
        "primary_uncertainty": freeze["primary_uncertainty"],
        "prospective_scoring": freeze["prospective_scoring"],
        "interpretation_lock": "Score this artifact before any post-14B refit. Seeds are replicates; checkpoints are repeated budget observations.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output),
                      "sha256": sha256(args.output), "predicted_best": rankings}, indent=2))


if __name__ == "__main__":
    main()
