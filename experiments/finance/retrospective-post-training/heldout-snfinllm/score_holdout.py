#!/usr/bin/env python3
"""Score the frozen SNFinLLM predictions against extracted outcomes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREDICTIONS = HERE / "PREDICTIONS.json"
OUTCOMES = HERE / "OUTCOMES.json"
OUTPUT = HERE / "SCORE.json"


def method_metrics(method: str, predictions: dict, panels: list[dict]) -> dict:
    pair_credit = 0.0
    pair_count = 0
    top_credit = 0.0
    native_regret = 0.0
    normalized_regret = 0.0

    for panel in panels:
        observed = panel["scores"]
        arms = sorted(observed)
        predicted = {arm: predictions[arm][method] for arm in arms}
        for i, left in enumerate(arms):
            for right in arms[i + 1 :]:
                pred_delta = predicted[left] - predicted[right]
                obs_delta = observed[left] - observed[right]
                if pred_delta == 0 or obs_delta == 0:
                    pair_credit += 0.5
                elif (pred_delta > 0) == (obs_delta > 0):
                    pair_credit += 1.0
                pair_count += 1

        predicted_best = [arm for arm in arms if predicted[arm] == max(predicted.values())]
        observed_best = [arm for arm in arms if observed[arm] == max(observed.values())]
        top_credit += sum(arm in observed_best for arm in predicted_best) / len(predicted_best)
        chosen_value = sum(observed[arm] for arm in predicted_best) / len(predicted_best)
        regret = max(observed.values()) - chosen_value
        native_regret += regret
        spread = max(observed.values()) - min(observed.values())
        normalized_regret += regret / spread if spread else 0.0

    panel_count = len(panels)
    return {
        "pairwise_ordering_credit": pair_credit / pair_count,
        "pairwise_correct_credit": pair_credit,
        "pairwise_comparisons": pair_count,
        "top_choice_credit": top_credit / panel_count,
        "mean_native_regret_percentage_points": native_regret / panel_count,
        "mean_normalized_regret": normalized_regret / panel_count,
        "panels": panel_count,
    }


def adjacent_stage_audit(panels: list[dict]) -> dict:
    comparisons = [
        ("continued_pretraining_over_base", "snfinllm_base_cpt", "original_general_base"),
        ("sft_over_continued_pretraining", "snfinllm_chat_sft", "snfinllm_base_cpt"),
        ("dpo_over_sft", "snfinllm_dpo", "snfinllm_chat_sft"),
    ]
    result = {}
    for label, later, earlier in comparisons:
        eligible = [p for p in panels if later in p["scores"] and earlier in p["scores"]]
        wins = sum(p["scores"][later] > p["scores"][earlier] for p in eligible)
        losses = sum(p["scores"][later] < p["scores"][earlier] for p in eligible)
        ties = len(eligible) - wins - losses
        result[label] = {
            "reported_targets": len(eligible),
            "later_stage_wins": wins,
            "later_stage_losses": losses,
            "ties": ties,
        }
    return result


def main() -> None:
    prediction_bytes = PREDICTIONS.read_bytes()
    predictions = json.loads(prediction_bytes)
    outcomes = json.loads(OUTCOMES.read_text())
    expected_hash = outcomes["extraction"]["prediction_sha256"]
    observed_hash = hashlib.sha256(prediction_bytes).hexdigest()
    if observed_hash != expected_hash:
        raise RuntimeError("prediction artifact changed after the recorded freeze")

    methods = ("practical_rule", "full_ridge", "compact_ridge", "more_data")
    output = {
        "schema_version": 1,
        "status": "SCORED_SOURCE_LEVEL_HOLDOUT",
        "source": outcomes["source"],
        "prediction_sha256": observed_hash,
        "metrics": {
            method: method_metrics(method, predictions["predictions"], outcomes["panels"])
            for method in methods
        },
        "adjacent_stage_audit": adjacent_stage_audit(outcomes["panels"]),
        "interpretation": (
            "The representation transfers to continued financial pretraining but does not "
            "predict the target-specific effects of later SFT and DPO stages. Generic preference "
            "optimization should not receive data-quality credit without evidence that its "
            "feedback objective aligns with the scored target."
        ),
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
