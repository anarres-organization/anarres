#!/usr/bin/env python3
"""Test shared materials-environment coordinates under leave-one-source-out.

The source papers expose different native measurements. This audit maps only
pre-outcome quantities into a small set of scientific concepts, normalizes
those quantities within source without using outcomes, and holds out every
source in turn. It is intentionally exploratory; the sealed phonon study is
the prospective test.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

FILES = {
    "li_2023_redundancy": "li_2023_active_learning_panels.json",
    "haenseroth_2026_generators": "haenseroth_2026_generator_panels.json",
    "kulichenko_2023_udd": "kulichenko_2023_udd_cross_test_panels.json",
    "dale_2026_active_learning_failure": "dale_2026_active_learning_panels.json",
    "bi_elena_2026_budget_crossover": "bi_elena_2026_budget_crossover_panels.json",
    "wong_yang_2026_umlip_bias": "wong_yang_2026_umlip_bias_panels.json",
    "baghishov_2026_application_specific_mlip": "baghishov_2026_leverage_panels.json",
    "qi_2024_direct_sampling": "qi_2024_direct_panels.json",
    "zaverkin_2024_uncertainty_biased_md": "zaverkin_2024_uncertainty_biased_md_panels.json",
    "zhang_2023_etal": "zhang_2023_etal_panels.json",
    "espinosa_castaneda_2026_diversity": "espinosa_castaneda_2026_diversity_panels.json",
    "wang_2026_dataset_aware_entropy": "wang_2026_entropy_panels.json",
    "varga_umbrich_2026_pretrained_acquisition": "varga_umbrich_2026_transfer_panels.json",
    "kim_2026_density_diversity": "kim_2026_density_diversity_panels.json",
    "liu_2026_heterogeneous_uq": "liu_2026_tungsten_label_panels.json",
    "haenseroth_dressler_2026_data_efficiency": (
        "haenseroth_dressler_2026_trajectory_stride_panels.json"
    ),
}
COORDINATES = (
    "model_relative_signal",
    "structural_coverage",
    "target_relevance",
    "measurement_accessibility",
    "exposure",
)
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)


def semantic_coordinates(source: str, arm: dict) -> dict[str, float | None]:
    """Map native, pre-outcome measurements to common oriented concepts."""
    if source == "li_2023_redundancy":
        native = arm["method_coordinates"]
        match = native["acquisition_model_match"]
        return {
            "model_relative_signal": float(
                native["uses_model_relative_signal"]
                + native["uses_committee_disagreement"]
                + native["uses_predictive_uncertainty"]
            ),
            "structural_coverage": None,
            "target_relevance": None if match is None else float(match),
            "measurement_accessibility": None,
            "exposure": float(arm["actual_pool_fraction"]),
        }
    if source == "haenseroth_2026_generators":
        error = arm["pre_outcome_measurements"]["generator_zero_shot_force_mae_eV_per_A"]
        return {
            "model_relative_signal": None,
            "structural_coverage": None,
            "target_relevance": -float(error),
            "measurement_accessibility": 1.0,
            "exposure": float(arm["dft_label_budget"]),
        }
    if source == "kulichenko_2023_udd":
        native = arm["pre_outcome_measurements"]
        coverage = -(
            float(native["temperature_gap_to_target_K"]) / 1000.0
            + float(native["high_energy_count_gap_to_target"]) / 400.0
        )
        return {
            "model_relative_signal": float(native["uses_uncertainty_bias"]),
            "structural_coverage": coverage,
            "target_relevance": float(native["uncertainty_bias_matches_target"]),
            "measurement_accessibility": 1.0,
            "exposure": float(arm["training_configuration_count"]),
        }
    if source == "dale_2026_active_learning_failure":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(native["selects_by_uncertainty"]),
            "structural_coverage": None,
            "target_relevance": None,
            "measurement_accessibility": -float(native["calibration_complexity"]),
            "exposure": float(native["acquisition_budget_fraction"]),
        }
    if source == "bi_elena_2026_budget_crossover":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(native["uses_response_disagreement"]),
            "structural_coverage": float(
                native["uses_structural_coverage"] + native["uses_learned_embedding"]
            ),
            "target_relevance": float(native["uses_response_disagreement"]),
            "measurement_accessibility": 1.0 - float(native["requires_full_data_reference"]),
            "exposure": float(native["retained_budget_fraction"]),
        }
    if source == "wong_yang_2026_umlip_bias":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": -float(native["starting_energy_rmse_meV_per_atom"]),
            "structural_coverage": float(native["effective_configuration_coverage_energy_error"]),
            "target_relevance": -float(native["starting_energy_mae_meV_per_atom"]),
            "measurement_accessibility": 1.0,
            "exposure": float(native["configuration_count"]),
        }
    if source == "baghishov_2026_application_specific_mlip":
        native = arm["pre_outcome_measurements"]
        target_match = (
            native["uses_energy_leverage"]
            if arm["endpoint"] == "testing_energy_rmse"
            else native["uses_force_block_leverage"]
        )
        return {
            "model_relative_signal": None,
            "structural_coverage": float(native["uses_descriptor_coverage"]),
            "target_relevance": float(target_match),
            "measurement_accessibility": 1.0,
            "exposure": float(native["training_pool_fraction"]),
        }
    if source == "qi_2024_direct_sampling":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": None,
            "structural_coverage": float(native["structural_coverage"]),
            "target_relevance": float(native["target_distribution_match"]),
            "measurement_accessibility": 1.0,
            "exposure": float(native["training_configuration_count"]),
        }
    if source == "zaverkin_2024_uncertainty_biased_md":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(
                native["uses_uncertainty_selection"] + native["uses_uncertainty_bias"]
            ),
            "structural_coverage": (
                None
                if native["structural_coverage"] is None
                else float(native["structural_coverage"])
            ),
            "target_relevance": -float(native["temperature_gap_to_test_K"]),
            "measurement_accessibility": 1.0 - float(native["adaptive_acquisition"]),
            "exposure": float(native["training_configuration_count"]),
        }
    if source == "zhang_2023_etal":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(native["uses_entropy_targeting"]),
            "structural_coverage": float(native["targets_underrepresented_structure_space"]),
            "target_relevance": float(native["targets_underrepresented_structure_space"]),
            "measurement_accessibility": 1.0 - float(native["adaptive_acquisition"]),
            "exposure": float(native["final_training_count"]),
        }
    if source == "espinosa_castaneda_2026_diversity":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(native["uses_model_disagreement"]),
            "structural_coverage": float(
                native["uses_outcome_disagreement_diversity"]
                + native["uses_feature_space_diversity"]
            ),
            "target_relevance": float(native["targets_evaluation_property"]),
            "measurement_accessibility": 1.0 - float(native["adaptive_acquisition"]),
            "exposure": float(native["final_training_fraction"]),
        }
    if source == "wang_2026_dataset_aware_entropy":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": None,
            "structural_coverage": float(native["uses_structural_coverage_selection"]),
            "target_relevance": float(native["target_distribution_match"]),
            "measurement_accessibility": 1.0 - float(native["adaptive_acquisition"]),
            "exposure": float(native["training_configuration_count"]),
        }
    if source == "varga_umbrich_2026_pretrained_acquisition":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(native["uses_model_relative_signal"]),
            "structural_coverage": float(native["uses_lcmd_structural_coverage"]),
            "target_relevance": float(native["acquisition_signal_matches_energy_endpoint"]),
            "measurement_accessibility": -float(
                native["forward_passes_per_candidate"]
                + native["backward_passes_per_candidate"]
                + native["models_maintained"]
                - 1
            ),
            "exposure": float(native["maximum_label_count"]),
        }
    if source == "kim_2026_density_diversity":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": None,
            "structural_coverage": float(native["training_density_span_g_cm3"]),
            "target_relevance": -float(
                native["closest_density_gap_g_cm3"] + native["closest_temperature_gap_K"] / 600.0
            ),
            "measurement_accessibility": 1.0,
            "exposure": float(native["training_configuration_count"]),
        }
    if source == "liu_2026_heterogeneous_uq":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": float(
                native["uses_model_relative_uncertainty_partition"]
                + native["matches_independently_validated_uc1_threshold"]
            ),
            "structural_coverage": None,
            "target_relevance": float(native["matches_independently_validated_uc1_threshold"]),
            "measurement_accessibility": float(native["umlip_atomic_environment_fraction"]),
            "exposure": float(native["training_configuration_count"]),
        }
    if source == "haenseroth_dressler_2026_data_efficiency":
        native = arm["pre_outcome_measurements"]
        return {
            "model_relative_signal": None,
            "structural_coverage": float(np.log10(native["relative_trajectory_span"])),
            "target_relevance": None,
            "measurement_accessibility": None,
            "exposure": float(native["training_configuration_count"]),
        }
    raise KeyError(source)


def utility(arm: dict) -> float:
    derived = arm["derived"]
    for key in (
        "panel_normalized_utility",
        "panel_normalized_joint_utility",
    ):
        if key in derived:
            return float(derived[key])
    raise KeyError("normalized utility")


def load_rows(data: Path) -> list[dict]:
    rows = []
    for source, filename in FILES.items():
        payload = json.loads((data / filename).read_text(encoding="utf-8"))
        source_rows = []
        for arm in payload["arms"]:
            coordinates = semantic_coordinates(source, arm)
            source_rows.append(
                {
                    "source": source,
                    "panel": arm["panel_id"],
                    "utility": utility(arm),
                    "native": coordinates,
                }
            )

        # Coordinate units differ by paper. Standardization is source-local and
        # uses candidate measurements only, never downstream outcomes.
        for coordinate in COORDINATES:
            observed = [
                row["native"][coordinate]
                for row in source_rows
                if row["native"][coordinate] is not None
            ]
            center = float(np.mean(observed)) if observed else 0.0
            scale = float(np.std(observed)) if observed else 1.0
            if np.isclose(scale, 0.0):
                scale = 1.0
            for row in source_rows:
                value = row["native"][coordinate]
                row.setdefault("features", []).append(
                    0.0 if value is None else (float(value) - center) / scale
                )
                row["features"].append(float(value is None))
        rows.extend(source_rows)
    return rows


def ridge_predict(train: list[dict], test: list[dict], alpha: float) -> np.ndarray:
    x_train = np.asarray([row["features"] for row in train], dtype=float)
    x_test = np.asarray([row["features"] for row in test], dtype=float)
    y = np.asarray([row["utility"] for row in train], dtype=float)
    center = x_train.mean(axis=0)
    x_train = x_train - center
    x_test = x_test - center
    beta = np.linalg.solve(
        x_train.T @ x_train + alpha * np.eye(x_train.shape[1]),
        x_train.T @ (y - y.mean()),
    )
    return y.mean() + x_test @ beta


def choose_alpha(train: list[dict]) -> float:
    sources = sorted({row["source"] for row in train})
    losses = {}
    for alpha in ALPHAS:
        errors = []
        for source in sources:
            inner_train = [row for row in train if row["source"] != source]
            inner_test = [row for row in train if row["source"] == source]
            predictions = ridge_predict(inner_train, inner_test, alpha)
            errors.extend(
                (prediction - row["utility"]) ** 2
                for prediction, row in zip(predictions, inner_test, strict=True)
            )
        losses[alpha] = float(np.mean(errors))
    return min(ALPHAS, key=lambda value: (losses[value], value))


def panel_metrics(rows: list[dict], predictions: list[float]) -> dict:
    panels: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        panels[row["panel"]].append(index)
    pair_credit, regrets, top_credit = [], [], []
    for indices in panels.values():
        for offset, left in enumerate(indices):
            for right in indices[offset + 1 :]:
                observed = rows[left]["utility"] - rows[right]["utility"]
                predicted = predictions[left] - predictions[right]
                if np.isclose(observed, 0.0) or np.isclose(predicted, 0.0):
                    pair_credit.append(0.5)
                else:
                    pair_credit.append(float(np.sign(observed) == np.sign(predicted)))
        highest = max(predictions[index] for index in indices)
        selected = [index for index in indices if np.isclose(predictions[index], highest)]
        best_utility = max(rows[index]["utility"] for index in indices)
        selected_utility = float(np.mean([rows[index]["utility"] for index in selected]))
        regrets.append(best_utility - selected_utility)
        top_credit.append(
            float(np.mean([np.isclose(rows[index]["utility"], best_utility) for index in selected]))
        )
    return {
        "panels": len(panels),
        "arms": len(rows),
        "pairwise_ordering": float(np.mean(pair_credit)),
        "mean_normalized_regret": float(np.mean(regrets)),
        "top_choice_credit": float(np.mean(top_credit)),
    }


def analyze(data: Path) -> dict:
    rows = load_rows(data)
    predictions = {"uninformed_tie": [], "semantic_mean": [], "ridge": []}
    ordered_rows = []
    alphas = {}
    sources = sorted(FILES)
    for source in sources:
        train = [row for row in rows if row["source"] != source]
        test = [row for row in rows if row["source"] == source]
        ordered_rows.extend(test)
        predictions["uninformed_tie"].extend([0.0] * len(test))
        # Equal weight over the five oriented coordinates; missingness columns
        # do not enter the rule.
        predictions["semantic_mean"].extend(float(np.mean(row["features"][0::2])) for row in test)
        alpha = choose_alpha(train)
        alphas[source] = alpha
        predictions["ridge"].extend(ridge_predict(train, test, alpha))

    per_source = {}
    for source in sources:
        indices = [index for index, row in enumerate(ordered_rows) if row["source"] == source]
        source_rows = [ordered_rows[index] for index in indices]
        per_source[source] = {
            rule: panel_metrics(source_rows, [values[index] for index in indices])
            for rule, values in predictions.items()
        }
    overall = {rule: panel_metrics(ordered_rows, values) for rule, values in predictions.items()}
    macro = {}
    for rule in predictions:
        macro[rule] = {
            metric: float(np.mean([per_source[source][rule][metric] for source in sources]))
            for metric in ("pairwise_ordering", "mean_normalized_regret", "top_choice_credit")
        }
    source_win_counts = {}
    for rule in ("semantic_mean", "ridge"):
        source_win_counts[rule] = {}
        for metric, higher_is_better in (
            ("pairwise_ordering", True),
            ("mean_normalized_regret", False),
            ("top_choice_credit", True),
        ):
            improved = tied = worsened = 0
            for source in sources:
                value = per_source[source][rule][metric]
                baseline = per_source[source]["uninformed_tie"][metric]
                if np.isclose(value, baseline):
                    tied += 1
                elif (value > baseline) == higher_is_better:
                    improved += 1
                else:
                    worsened += 1
            source_win_counts[rule][metric] = {
                "improved": improved,
                "tied": tied,
                "worsened": worsened,
            }
    return {
        "artifact": "materials_pooled_semantic_loso_v1",
        "design": (
            "nested leave-one-source-out ridge with source-local, outcome-blind "
            "coordinate normalization"
        ),
        "support": {
            "sources": len(sources),
            "panels": len({row["panel"] for row in rows}),
            "arms": len(rows),
        },
        "coordinates": list(COORDINATES),
        "fold_alphas": alphas,
        "panel_weighted_metrics": overall,
        "source_macro_metrics": macro,
        "source_win_counts_vs_uninformed_tie": source_win_counts,
        "per_source_metrics": per_source,
        "interpretation_boundary": [
            "Outcomes are normalized only within matched decision panels.",
            "Native measurements are mapped to oriented scientific concepts and "
            "standardized within source without using outcomes.",
            "No source, dataset, material, method, or environment identity is a "
            "predictive feature.",
            "The sixteen studies differ in target, downstream model, candidate "
            "construction, and available measurements.",
            "This retrospective audit tests whether broad concepts recur; it does "
            "not establish a universal coefficient vector.",
            "The sealed PhononScore candidate set remains the prospective test.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "pooled_semantic_analysis.json",
    )
    args = parser.parse_args()
    result = analyze(args.data)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["support"], sort_keys=True))


if __name__ == "__main__":
    main()
