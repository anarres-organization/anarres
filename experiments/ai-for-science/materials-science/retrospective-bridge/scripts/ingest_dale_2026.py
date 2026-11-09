#!/usr/bin/env python3
"""Build matched active-learning panels from Dale et al. histories."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


SOURCE_ID = "dale_2026_active_learning_failure"
BUDGETS = {
    "0pt05": 0.05,
    "0pt10": 0.10,
    "0pt20": 0.20,
    "0pt50": 0.50,
    "0pt70": 0.70,
    "1pt00": 1.00,
}
METHODS = {
    "random": {
        "selects_by_uncertainty": 0,
        "ensemble_source": 0,
        "loss_landscape_source": 0,
        "calibration_complexity": 0,
    },
    "ensem_og": {
        "selects_by_uncertainty": 1,
        "ensemble_source": 1,
        "loss_landscape_source": 0,
        "calibration_complexity": 0,
    },
    "ensem_cf": {
        "selects_by_uncertainty": 1,
        "ensemble_source": 1,
        "loss_landscape_source": 0,
        "calibration_complexity": 1,
    },
    "ensem_cal": {
        "selects_by_uncertainty": 1,
        "ensemble_source": 1,
        "loss_landscape_source": 0,
        "calibration_complexity": 2,
    },
    "ll_og": {
        "selects_by_uncertainty": 1,
        "ensemble_source": 0,
        "loss_landscape_source": 1,
        "calibration_complexity": 0,
    },
    "ll_cf": {
        "selects_by_uncertainty": 1,
        "ensemble_source": 0,
        "loss_landscape_source": 1,
        "calibration_complexity": 1,
    },
    "ll_cal": {
        "selects_by_uncertainty": 1,
        "ensemble_source": 0,
        "loss_landscape_source": 1,
        "calibration_complexity": 2,
    },
}


def reconstruct(raw: Path) -> dict:
    by_panel: dict[str, list[dict]] = defaultdict(list)
    for history_path in sorted(raw.glob("*/*/*/*/history_test.json")):
        target, element, budget_key, method = history_path.parts[-5:-1]
        if budget_key not in BUDGETS or method not in METHODS:
            continue
        history = json.loads(history_path.read_text(encoding="utf-8"))
        if not all(history.get(metric) for metric in ("loss", "mae", "rmse")):
            raise ValueError(f"incomplete history: {history_path}")
        if len({len(history[metric]) for metric in ("loss", "mae", "rmse")}) != 1:
            raise ValueError(f"history length mismatch: {history_path}")
        panel_id = f"{SOURCE_ID}:{target}:omit_{element}:budget_{budget_key}"
        by_panel[panel_id].append(
            {
                "source_id": SOURCE_ID,
                "panel_id": panel_id,
                "target_property": target,
                "omitted_element": element,
                "acquisition_budget_fraction": BUDGETS[budget_key],
                "acquisition_method": method,
                "pre_outcome_measurements": METHODS[method]
                | {"acquisition_budget_fraction": BUDGETS[budget_key]},
                "outcome": {
                    "final_ood_test_mae": history["mae"][-1],
                    "final_ood_test_rmse": history["rmse"][-1],
                    "final_ood_test_loss": history["loss"][-1],
                },
                "replication": {
                    "exact_released_trajectories": 1,
                    "reported_paper_repetitions": 5,
                },
                "provenance": {
                    "relative_history_path": history_path.relative_to(raw).as_posix(),
                    "selected_epoch": len(history["mae"]) - 1,
                },
            }
        )

    complete = {panel: arms for panel, arms in by_panel.items() if len(arms) == len(METHODS)}
    incomplete = {
        panel: sorted(set(METHODS) - {arm["acquisition_method"] for arm in arms})
        for panel, arms in by_panel.items()
        if len(arms) != len(METHODS)
    }
    if len(complete) != 23 or len(incomplete) != 1:
        raise ValueError(
            f"expected 23 complete and one incomplete panel, got {len(complete)} and {len(incomplete)}"
        )

    arms = []
    for panel_id, panel_arms in complete.items():
        values = [arm["outcome"]["final_ood_test_mae"] for arm in panel_arms]
        best, worst = min(values), max(values)
        span = worst - best
        for arm in panel_arms:
            value = arm["outcome"]["final_ood_test_mae"]
            arm["derived"] = {
                "native_utility": -value,
                "panel_normalized_utility": 1.0 if span == 0 else (worst - value) / span,
                "panel_normalized_regret": 0.0 if span == 0 else (value - best) / span,
            }
            arms.append(arm)

    arms.sort(key=lambda arm: (arm["panel_id"], arm["acquisition_method"]))
    return {
        "artifact": "dale_2026_active_learning_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(complete),
        "arm_count": len(arms),
        "primary_outcome": "final_ood_test_mae",
        "normalization": "within target, omitted element, and acquisition budget; lower MAE maps to higher utility",
        "release_boundary": {
            "paper_reports_repetitions": 5,
            "exact_released_trajectory_count_per_arm": 1,
            "interpretation": "The fitted artifact uses the exact released trajectory and does not reconstruct plotted error bars.",
        },
        "excluded_incomplete_panels": incomplete,
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = reconstruct(args.raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
