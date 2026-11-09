#!/usr/bin/env python3
"""Reconstruct matched active-learning panels from Li et al. (2023).

The script reads the authors' released in-distribution CSV files. It preserves
the native metrics and adds panel-local normalization only after matching the
property, database, downstream model, and training fraction.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


SOURCE_ID = "li_2023_redundancy"
DEFAULT_BUDGETS = (0.02, 0.10, 0.20)
ACTIVE_METHODS = ("QBC", "rfMaxUncertainty", "xgbMaxUncertainty")


def _as_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "").strip()
    return None if not value else float(value)


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _budget_value(row: dict[str, str], *, active: bool) -> float:
    if active:
        return float(row["train_ratio"])
    for key in ("train_size", ""):
        if key in row and row[key].strip():
            return float(row[key])
    raise ValueError(f"random-sampling row has no budget column: {row}")


def _nearest_row(
    rows: list[dict[str, str]], budget: float, *, active: bool, tolerance: float = 0.001
) -> tuple[dict[str, str], float]:
    candidates = [(_budget_value(row, active=active), row) for row in rows]
    actual, selected = min(candidates, key=lambda item: abs(item[0] - budget))
    if abs(actual - budget) > tolerance:
        raise ValueError(f"no row within {tolerance} of budget {budget}; nearest={actual}")
    return selected, actual


def _parse_active_stem(stem: str) -> tuple[str, str, str, str]:
    target, database, downstream_model, method = stem.rsplit("_", 3)
    if method not in ACTIVE_METHODS:
        raise ValueError(f"unexpected active-learning method in {stem}")
    return target, database, downstream_model, method


def _method_coordinates(method: str, downstream_model: str) -> dict[str, object]:
    if method == "random":
        return {
            "uses_model_relative_signal": 0,
            "uses_committee_disagreement": 0,
            "uses_predictive_uncertainty": 0,
            "acquisition_model_match": None,
            "acquisition_model_match_missing": 1,
        }
    if method == "QBC":
        return {
            "uses_model_relative_signal": 1,
            "uses_committee_disagreement": 1,
            "uses_predictive_uncertainty": 0,
            "acquisition_model_match": None,
            "acquisition_model_match_missing": 1,
        }
    acquisition_model = "rf" if method == "rfMaxUncertainty" else "xgb"
    return {
        "uses_model_relative_signal": 1,
        "uses_committee_disagreement": 0,
        "uses_predictive_uncertainty": 1,
        "acquisition_model_match": int(acquisition_model == downstream_model),
        "acquisition_model_match_missing": 0,
    }


def reconstruct(source_root: Path, budgets: tuple[float, ...] = DEFAULT_BUDGETS) -> dict:
    id_root = source_root / "performance_on_ID_data"
    active_root = id_root / "active_learning"
    random_root = id_root / "random_sampling"
    if not active_root.is_dir() or not random_root.is_dir():
        raise FileNotFoundError("expected performance_on_ID_data active_learning and random_sampling")

    arms: list[dict] = []
    random_cache: dict[Path, list[dict[str, str]]] = {}
    seen_random: set[tuple[str, float]] = set()

    for active_path in sorted(active_root.glob("*.csv")):
        target, database, downstream_model, method = _parse_active_stem(active_path.stem)
        random_path = random_root / f"{target}_{database}_{downstream_model}_rand.csv"
        if not random_path.is_file():
            raise FileNotFoundError(f"missing matched random baseline: {random_path.name}")
        active_rows = _load_rows(active_path)
        random_rows = random_cache.setdefault(random_path, _load_rows(random_path))

        for budget in budgets:
            panel_id = f"{SOURCE_ID}:{target}:{database}:{downstream_model}:b{budget:.2f}"
            row, actual = _nearest_row(active_rows, budget, active=True)
            arms.append(
                _arm_record(
                    panel_id=panel_id,
                    target=target,
                    database=database,
                    downstream_model=downstream_model,
                    requested_budget=budget,
                    actual_budget=actual,
                    method=method,
                    row=row,
                    source_file=active_path.name,
                    random=False,
                )
            )

            random_key = (panel_id, budget)
            if random_key not in seen_random:
                random_row, random_actual = _nearest_row(random_rows, budget, active=False)
                arms.append(
                    _arm_record(
                        panel_id=panel_id,
                        target=target,
                        database=database,
                        downstream_model=downstream_model,
                        requested_budget=budget,
                        actual_budget=random_actual,
                        method="random",
                        row=random_row,
                        source_file=random_path.name,
                        random=True,
                    )
                )
                seen_random.add(random_key)

    panels: dict[str, list[dict]] = defaultdict(list)
    for arm in arms:
        panels[arm["panel_id"]].append(arm)
    for panel_arms in panels.values():
        errors = [arm["outcome"]["rmse"] for arm in panel_arms]
        best, worst = min(errors), max(errors)
        span = worst - best
        for arm in panel_arms:
            error = arm["outcome"]["rmse"]
            arm["derived"] = {
                "native_utility": -error,
                "panel_normalized_utility": 1.0 if span == 0 else (worst - error) / span,
                "panel_normalized_regret": 0.0 if span == 0 else (error - best) / span,
            }

    ordered_arms = sorted(arms, key=lambda arm: (arm["panel_id"], arm["method"]))
    return {
        "artifact": "li_2023_active_learning_panels_v1",
        "source_id": SOURCE_ID,
        "outcome_scope": "in-distribution test split",
        "primary_outcome": "rmse",
        "budgets": list(budgets),
        "normalization": "within matched panel; best RMSE maps to 1 and worst to 0",
        "panel_count": len(panels),
        "arm_count": len(ordered_arms),
        "arms": ordered_arms,
    }


def _arm_record(
    *,
    panel_id: str,
    target: str,
    database: str,
    downstream_model: str,
    requested_budget: float,
    actual_budget: float,
    method: str,
    row: dict[str, str],
    source_file: str,
    random: bool,
) -> dict:
    return {
        "source_id": SOURCE_ID,
        "panel_id": panel_id,
        "target_property": target,
        "database": database,
        "downstream_model": downstream_model,
        "requested_pool_fraction": requested_budget,
        "actual_pool_fraction": actual_budget,
        "method": method,
        "method_coordinates": _method_coordinates(method, downstream_model),
        "outcome": {
            "mae": float(row["maes"]),
            "rmse": float(row["rmse"]),
            "r2": float(row["r2"]),
            "mae_std": _as_float(row, "maes_std") if random else None,
            "rmse_std": _as_float(row, "rmse_std") if random else None,
            "r2_std": _as_float(row, "r2_std") if random else None,
        },
        "replication": {
            "released_dispersion_available": int(random),
            "active_learning_single_released_trajectory": int(not random),
        },
        "provenance": {"source_file": source_file},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = reconstruct(args.source_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
