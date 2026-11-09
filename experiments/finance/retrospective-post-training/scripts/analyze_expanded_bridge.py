#!/usr/bin/env python3
"""Evaluate the source-recovered finance bridge under grouped holdouts."""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INITIAL = ROOT / "data" / "panels.json"
RECOVERED = ROOT / "data" / "recovered_panels.json"
OUT = ROOT / "results" / "expanded_summary.json"
MANIFEST = ROOT / "results" / "EXPANDED_MANIFEST.sha256.json"

FEATURES = [
    "target_alignment",
    "data_volume",
    "source_diversity",
    "human_labeled_fraction",
    "quality_control",
    "retention_control",
    "verifier_alignment",
    "policy_relative_selection",
    "domain_specific_selection",
    "transcript_refinement",
    "qa_refinement",
    "feedback_locality",
    "efficient_rollout",
    "curriculum_progression",
]

COMPACT_GROUPS = {
    "target_fit": ["target_alignment"],
    "curation": [
        "quality_control",
        "human_labeled_fraction",
        "domain_specific_selection",
        "transcript_refinement",
        "qa_refinement",
    ],
    "retention": ["retention_control", "feedback_locality"],
    "verification": ["verifier_alignment", "policy_relative_selection", "curriculum_progression"],
    "breadth": ["source_diversity"],
    "volume": ["data_volume"],
    "rollout_efficiency": ["efficient_rollout"],
}


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    aug = [matrix[i][:] + [vector[i]] for i in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(aug[row][column]))
        if abs(aug[pivot][column]) < 1e-12:
            raise ValueError("singular system")
        aug[column], aug[pivot] = aug[pivot], aug[column]
        scale = aug[column][column]
        aug[column] = [value / scale for value in aug[column]]
        for row in range(n):
            if row == column:
                continue
            factor = aug[row][column]
            aug[row] = [aug[row][j] - factor * aug[column][j] for j in range(n + 1)]
    return [aug[i][-1] for i in range(n)]


def ridge_fit(xs: list[list[float]], ys: list[float], penalty: float = 4.0) -> list[float]:
    width = len(xs[0]) + 1
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for x, y in zip(xs, ys, strict=True):
        row = [1.0] + x
        for i in range(width):
            rhs[i] += row[i] * y
            for j in range(width):
                gram[i][j] += row[i] * row[j]
    for i in range(1, width):
        gram[i][i] += penalty
    return solve(gram, rhs)


def predict(coef: list[float], x: list[float]) -> float:
    return coef[0] + sum(a * b for a, b in zip(coef[1:], x, strict=True))


def rank(values: list[float]) -> list[float]:
    if len(set(values)) == 1:
        return [0.0] * len(values)
    order = {
        value: index / (len(set(values)) - 1) for index, value in enumerate(sorted(set(values)))
    }
    return [order[value] for value in values]


def observed_feature(values: dict[str, float], name: str, value: float) -> None:
    values[name] = float(value)
    values[f"{name}__observed"] = 1.0


def empty_features() -> dict[str, float]:
    return {name: 0.0 for feature in FEATURES for name in (feature, f"{feature}__observed")}


def initial_rows(document: dict) -> list[dict]:
    old_names = document["feature_names"]
    rows = []
    for panel in document["panels"]:
        scores = [arm["score"] for arm in panel["arms"]]
        low, high = min(scores), max(scores)
        for arm in panel["arms"]:
            old = dict(zip(old_names, arm["features"], strict=True))
            values = empty_features()
            observed_feature(values, "quality_control", old["quality_control"])
            observed_feature(values, "retention_control", old["retention_control"])
            observed_feature(values, "verifier_alignment", old["verifier_alignment"])
            observed_feature(values, "policy_relative_selection", old["policy_relative_difficulty"])
            observed_feature(values, "target_alignment", 1.0 - old["out_of_domain_mix"])
            observed_feature(values, "data_volume", old["data_fraction"])
            rows.append(
                make_row(
                    panel["study_id"],
                    panel["panel_id"],
                    arm["id"],
                    "unreported",
                    "unreported",
                    arm["score"],
                    low,
                    high,
                    values,
                )
            )
    return rows


def mapped_recovered_panel(panel: dict) -> list[dict]:
    arms = panel["arms"]
    sample_counts = [arm["treatment"].get("sample_count") for arm in arms]
    sample_rank = {}
    reported_samples = [value for value in sample_counts if value is not None]
    if reported_samples:
        ranked = rank([float(value) for value in reported_samples])
        sample_rank = dict(zip([float(value) for value in reported_samples], ranked, strict=True))
    diversity_values = [arm["treatment"].get("source_diversity") for arm in arms]
    reported_diversity = [value for value in diversity_values if value is not None]
    diversity_rank = {}
    if reported_diversity:
        ranked = rank([float(value) for value in reported_diversity])
        diversity_rank = dict(
            zip([float(value) for value in reported_diversity], ranked, strict=True)
        )
    scores = [arm["score"] for arm in arms]
    low, high = min(scores), max(scores)
    output = []
    for arm in arms:
        treatment = arm["treatment"]
        values = empty_features()
        if "target_fraction" in treatment:
            observed_feature(values, "target_alignment", treatment["target_fraction"])
        if "sample_count" in treatment:
            observed_feature(values, "data_volume", sample_rank[float(treatment["sample_count"])])
        if "source_diversity" in treatment:
            observed_feature(
                values, "source_diversity", diversity_rank[float(treatment["source_diversity"])]
            )
        real_fraction = treatment.get("real_fraction")
        if real_fraction is None and "synthetic_fraction" in treatment:
            real_fraction = 1.0 - float(treatment["synthetic_fraction"])
        if real_fraction is not None:
            observed_feature(values, "human_labeled_fraction", real_fraction)

        selection = treatment.get("selection")
        if selection is not None:
            quality = {
                "farthest_from_real": -1.0,
                "random": 0.0,
                "none": 0.0,
                "closest_to_real": 1.0,
                "math_prm": 0.5,
                "finance_prm": 1.0,
            }[selection]
            observed_feature(values, "quality_control", quality)
            observed_feature(
                values, "domain_specific_selection", 1.0 if selection == "finance_prm" else 0.0
            )
        if "domain_specific" in treatment:
            observed_feature(
                values, "domain_specific_selection", float(treatment["domain_specific"])
            )
        if "verifier_alignment" in treatment:
            observed_feature(values, "verifier_alignment", float(treatment["verifier_alignment"]))
        for feature in (
            "target_alignment",
            "quality_control",
            "retention_control",
            "policy_relative_selection",
            "feedback_locality",
            "efficient_rollout",
        ):
            if feature in treatment:
                observed_feature(values, feature, float(treatment[feature]))

        method = treatment.get("method")
        if method is not None:
            observed_feature(values, "retention_control", 1.0 if "distillation" in method else 0.0)
            observed_feature(
                values, "feedback_locality", 1.0 if method == "localized_self_distillation" else 0.0
            )
        if "hint_writer" in treatment:
            observed_feature(
                values, "retention_control", 1.0 if treatment["hint_writer"] == "self" else 0.5
            )
        if "rollout_cap" in treatment:
            observed_feature(
                values, "efficient_rollout", 1.0 if treatment["rollout_cap"] <= 100 else 0.0
            )
        if "transcript_refinement" in treatment:
            observed_feature(
                values, "transcript_refinement", float(treatment["transcript_refinement"])
            )
        if "qa_refinement" in treatment:
            observed_feature(values, "qa_refinement", float(treatment["qa_refinement"]))
        if "context_sources" in treatment:
            observed_feature(values, "source_diversity", float(treatment["context_sources"]))
        if "curriculum_progression" in treatment:
            observed_feature(
                values, "curriculum_progression", float(treatment["curriculum_progression"])
            )
        if "difficulty_filtering" in treatment:
            observed_feature(
                values, "policy_relative_selection", float(treatment["difficulty_filtering"])
            )

        output.append(
            make_row(
                panel["source_id"],
                panel["panel_id"],
                arm["id"],
                panel["model"],
                panel["target"],
                arm["score"],
                low,
                high,
                values,
            )
        )
    return output


def make_row(
    source: str,
    panel: str,
    arm: str,
    model: str,
    target: str,
    score: float,
    low: float,
    high: float,
    values: dict[str, float],
) -> dict:
    utility = 0.5 if high == low else (score - low) / (high - low)
    names = [name for feature in FEATURES for name in (feature, f"{feature}__observed")]
    return {
        "source": source,
        "panel": panel,
        "arm": arm,
        "model": model,
        "target": target,
        "utility": utility,
        "x": [values[name] for name in names],
        "feature_values": values,
    }


def all_rows() -> list[dict]:
    initial = json.loads(INITIAL.read_text())
    recovered = json.loads(RECOVERED.read_text())
    rows = initial_rows(initial)
    for panel in recovered["panels"]:
        rows.extend(mapped_recovered_panel(panel))
    return rows


def compact_x(row: dict) -> list[float]:
    values = row["feature_values"]
    output = []
    for names in COMPACT_GROUPS.values():
        observed = [values[name] for name in names if values[f"{name}__observed"]]
        output.append(sum(observed) / len(observed) if observed else 0.0)
    return output


def grouped_predictions(rows: list[dict], group_key: str) -> dict[str, dict[str, float]]:
    predictions = {
        "ridge": {},
        "compact_ridge": {},
        "practical_rule": {},
        "more_data": {},
        "uninformed": {},
        "random_fingerprint": {},
    }
    groups = sorted(
        {
            (row["source"], row[group_key]) if group_key != "source" else row["source"]
            for row in rows
        }
    )
    for held_out in groups:

        def group(row: dict):
            return (row["source"], row[group_key]) if group_key != "source" else row["source"]

        train = [row for row in rows if group(row) != held_out]
        test = [row for row in rows if group(row) == held_out]
        coef = ridge_fit([row["x"] for row in train], [row["utility"] for row in train])
        compact_coef = ridge_fit(
            [compact_x(row) for row in train], [row["utility"] for row in train]
        )
        for row in test:
            key = f"{row['source']}::{row['panel']}::{row['arm']}"
            f = row["feature_values"]
            predictions["ridge"][key] = predict(coef, row["x"])
            predictions["compact_ridge"][key] = predict(compact_coef, compact_x(row))
            predictions["practical_rule"][key] = (
                f["target_alignment"]
                + 0.5 * f["quality_control"]
                + 0.5 * f["retention_control"]
                + 0.5 * f["verifier_alignment"]
                + 0.5 * f["policy_relative_selection"]
                + 0.25 * f["source_diversity"]
                + 0.25 * f["human_labeled_fraction"]
                + 0.25 * f["domain_specific_selection"]
                + 0.25 * f["transcript_refinement"]
                + 0.25 * f["qa_refinement"]
                + 0.25 * f["feedback_locality"]
                + 0.1 * f["efficient_rollout"]
                + 0.5 * f["curriculum_progression"]
            )
            predictions["more_data"][key] = f["data_volume"]
            predictions["uninformed"][key] = 0.0
            digest = hashlib.sha256(key.encode()).digest()
            predictions["random_fingerprint"][key] = int.from_bytes(digest[:8], "big") / 2**64
    return predictions


def score_core(rows: list[dict], predictions: dict[str, float]) -> dict:
    panels: dict[str, list[dict]] = {}
    for row in rows:
        panels.setdefault(f"{row['source']}::{row['panel']}", []).append(row)
    pair_correct = pair_total = 0
    regrets = []
    top_credit = []
    squared = []
    for panel_rows in panels.values():
        for row in panel_rows:
            key = f"{row['source']}::{row['panel']}::{row['arm']}"
            squared.append((predictions[key] - row["utility"]) ** 2)
        for i, left in enumerate(panel_rows):
            for right in panel_rows[i + 1 :]:
                lk = f"{left['source']}::{left['panel']}::{left['arm']}"
                rk = f"{right['source']}::{right['panel']}::{right['arm']}"
                observed = left["utility"] - right["utility"]
                estimated = predictions[lk] - predictions[rk]
                pair_total += 1
                if observed == 0 or estimated == 0:
                    pair_correct += 0.5
                elif observed * estimated > 0:
                    pair_correct += 1
        best = max(row["utility"] for row in panel_rows)
        predicted_best = max(
            predictions[f"{row['source']}::{row['panel']}::{row['arm']}"] for row in panel_rows
        )
        chosen = [
            row
            for row in panel_rows
            if predictions[f"{row['source']}::{row['panel']}::{row['arm']}"] == predicted_best
        ]
        chosen_utility = sum(row["utility"] for row in chosen) / len(chosen)
        regrets.append(best - chosen_utility)
        top_credit.append(sum(row["utility"] == best for row in chosen) / len(chosen))
    return {
        "normalized_rmse": round(math.sqrt(sum(squared) / len(squared)), 6),
        "pairwise_ordering": round(pair_correct / pair_total, 6),
        "mean_normalized_regret": round(sum(regrets) / len(regrets), 6),
        "top_choice_credit": round(sum(top_credit) / len(top_credit), 6),
    }


def score(rows: list[dict], predictions: dict[str, float]) -> dict:
    result = score_core(rows, predictions)
    per_source = {
        source: score_core([row for row in rows if row["source"] == source], predictions)
        for source in sorted({row["source"] for row in rows})
    }
    metric_names = list(result)
    result["source_macro"] = {
        name: round(sum(values[name] for values in per_source.values()) / len(per_source), 6)
        for name in metric_names
    }
    result["per_source"] = per_source
    return result


def rank_normalized_rows(rows: list[dict]) -> list[dict]:
    output = [dict(row) for row in rows]
    by_panel: dict[str, list[int]] = {}
    for index, row in enumerate(output):
        by_panel.setdefault(f"{row['source']}::{row['panel']}", []).append(index)
    for indices in by_panel.values():
        utilities = [output[index]["utility"] for index in indices]
        normalized = rank(utilities)
        for index, value in zip(indices, normalized, strict=True):
            output[index]["utility"] = value
    return output


def paired_source_comparison(result: dict, left: str, right: str) -> dict:
    left_sources = result[left]["per_source"]
    right_sources = result[right]["per_source"]
    differences = {
        source: round(
            right_sources[source]["mean_normalized_regret"]
            - left_sources[source]["mean_normalized_regret"],
            6,
        )
        for source in left_sources
    }
    wins = sum(value > 0 for value in differences.values())
    losses = sum(value < 0 for value in differences.values())
    ties = sum(value == 0 for value in differences.values())
    n = wins + losses
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2**n) if n else 1.0
    return {
        "left": left,
        "right": right,
        "positive_means_left_has_lower_regret": differences,
        "study_wins": wins,
        "study_losses": losses,
        "study_ties": ties,
        "two_sided_exact_sign_p": round(min(1.0, 2 * tail), 6),
    }


def shuffled_control(rows: list[dict], repeats: int = 200) -> dict:
    rng = random.Random(20261109)
    values = []
    for _ in range(repeats):
        shuffled = [dict(row) for row in rows]
        by_panel: dict[str, list[int]] = {}
        for index, row in enumerate(shuffled):
            by_panel.setdefault(f"{row['source']}::{row['panel']}", []).append(index)
        for indices in by_panel.values():
            utilities = [shuffled[index]["utility"] for index in indices]
            rng.shuffle(utilities)
            for index, utility in zip(indices, utilities, strict=True):
                shuffled[index]["utility"] = utility
        predictions = grouped_predictions(shuffled, "source")["ridge"]
        values.append(score(shuffled, predictions)["mean_normalized_regret"])
    values.sort()
    return {
        "repeats": repeats,
        "median_regret": values[len(values) // 2],
        "p05_regret": values[int(0.05 * len(values))],
        "p95_regret": values[int(0.95 * len(values)) - 1],
    }


def main() -> None:
    rows = all_rows()
    evaluations = {}
    for group_key in ["source", "model", "target"]:
        predictions = grouped_predictions(rows, group_key)
        evaluations[f"leave_one_{group_key}_out"] = {
            name: score(rows, values) for name, values in predictions.items()
        }
    rank_rows = rank_normalized_rows(rows)
    rank_predictions = grouped_predictions(rank_rows, "source")
    rank_sensitivity = {name: score(rank_rows, values) for name, values in rank_predictions.items()}
    panels_per_source: dict[str, set[str]] = {}
    for row in rows:
        panels_per_source.setdefault(row["source"], set()).add(row["panel"])
    multi_panel_rows = [row for row in rows if len(panels_per_source[row["source"]]) >= 2]
    multi_panel_predictions = grouped_predictions(multi_panel_rows, "source")
    multi_panel_sensitivity = {
        "support": {
            "sources": len({row["source"] for row in multi_panel_rows}),
            "panels": len({(row["source"], row["panel"]) for row in multi_panel_rows}),
            "arms": len(multi_panel_rows),
        },
        "evaluations": {
            name: score(multi_panel_rows, values)
            for name, values in multi_panel_predictions.items()
        },
    }
    multi_panel_sensitivity["paired_source_comparison"] = paired_source_comparison(
        multi_panel_sensitivity["evaluations"], "practical_rule", "more_data"
    )
    source_result = evaluations["leave_one_source_out"]
    output = {
        "status": "retrospective_source_recovered",
        "support": {
            "sources": len({row["source"] for row in rows}),
            "panels": len({(row["source"], row["panel"]) for row in rows}),
            "arms": len(rows),
        },
        "normalization": "zero-to-one utility within each source-native decision panel",
        "features": FEATURES,
        "compact_feature_groups": COMPACT_GROUPS,
        "evaluations": evaluations,
        "rank_utility_sensitivity": rank_sensitivity,
        "multi_panel_source_sensitivity": multi_panel_sensitivity,
        "paired_source_comparison": paired_source_comparison(
            source_result, "practical_rule", "more_data"
        ),
        "shuffled_pairing_control": shuffled_control(rows),
        "guardrails": [
            "all outcomes were public before this retrospective mapping",
            "source-native panels remain the unit of normalization and regret",
            "model and target holdouts are nested within sources and are sensitivity analyses",
            "the result cannot replace a frozen prospective finance decision",
        ],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    manifest_paths = [
        ROOT / "FEATURE_MAPPING.md",
        ROOT / "SOURCES.json",
        INITIAL,
        RECOVERED,
        ROOT / "scripts" / "build_recovered_panels.py",
        Path(__file__),
        OUT,
    ]
    manifest = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in manifest_paths
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output["support"], sort_keys=True))


if __name__ == "__main__":
    main()
