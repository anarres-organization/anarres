#!/usr/bin/env python3
"""Recompute and validate the prospective Vero repetition design."""

from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path
from typing import Any


class RepetitionDesignError(ValueError):
    """Raised when the prospective repetition calculation is inconsistent."""


def probability_at_least(n: int, probability: float, threshold: int) -> float:
    return 1 - sum(
        comb(n, count) * probability**count * (1 - probability) ** (n - count)
        for count in range(threshold)
    )


def validate(design: dict[str, Any], panel: dict[str, Any]) -> None:
    specifications = sum(record["specifications"] for record in panel["repositories"])
    if specifications != design["specifications_per_mode"]:
        raise RepetitionDesignError("panel specification count disagrees with the design")
    if len(panel["repositories"]) != design["repositories"]:
        raise RepetitionDesignError("panel repository count disagrees with the design")
    probability = design["reference_strict_success_probability"]
    threshold = design["minimum_mixed_specification_groups"]
    candidates = design["candidate_attempt_counts"]
    expected_results: list[dict[str, Any]] = []
    for attempts in candidates:
        mixed = 1 - probability**attempts - (1 - probability) ** attempts
        expected_results.append(
            {
                "attempts": attempts,
                "mixed_probability_per_specification": mixed,
                "expected_mixed_specifications": specifications * mixed,
                "probability_at_least_eight_mixed": probability_at_least(
                    specifications, mixed, threshold
                ),
            }
        )
    for observed, expected in zip(design["candidate_results"], expected_results, strict=True):
        if observed["attempts"] != expected["attempts"]:
            raise RepetitionDesignError("candidate attempt count changed")
        for field in (
            "mixed_probability_per_specification",
            "expected_mixed_specifications",
            "probability_at_least_eight_mixed",
        ):
            if abs(observed[field] - expected[field]) > 1e-12:
                raise RepetitionDesignError(f"candidate calculation changed: {field}")
    eligible = [
        record["attempts"]
        for record in expected_results
        if record["probability_at_least_eight_mixed"] >= design["minimum_detection_probability"]
    ]
    if not eligible or min(eligible) != design["selected_attempts_per_repository_mode"]:
        raise RepetitionDesignError("selected repetition count violates the frozen rule")
    expected_total = (
        design["repositories"] * design["modes"] * design["selected_attempts_per_repository_mode"]
    )
    if design["total_attempts"] != expected_total:
        raise RepetitionDesignError("total attempt count is inconsistent")
    if design["maximum_model_tokens"] != expected_total * 50000:
        raise RepetitionDesignError("maximum token cost is inconsistent")
    if design["status"] != "frozen_before_model_attempts":
        raise RepetitionDesignError("repetition design is not frozen")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    args = parser.parse_args()
    validate(
        json.loads(args.design.read_text(encoding="utf-8")),
        json.loads(args.panel.read_text(encoding="utf-8")),
    )
    print("validated prospective Vero repetition and cost design")


if __name__ == "__main__":
    main()
