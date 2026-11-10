#!/usr/bin/env python3
"""Render the retrospective finance decision audit as a deterministic SVG."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "summary.json"
OUTPUT = ROOT / "figures" / "retrospective_decision_audit.svg"

MODELS = [
    ("quality_rule", "Quality-aware rule", "#16836B"),
    ("ridge", "LOSO ridge", "#3569A8"),
    ("more_training", "More training", "#9AA4B2"),
]


def svg_text(x: float, y: float, value: str, **attrs: object) -> str:
    attributes = " ".join(
        f'{("class" if key == "class_" else key.replace("_", "-"))}="{html.escape(str(val))}"'
        for key, val in attrs.items()
    )
    return f'<text x="{x}" y="{y}" {attributes}>{html.escape(value)}</text>'


def svg_rect(x: float, y: float, width: float, fill: str) -> str:
    return f'<rect x="{x}" y="{y}" width="{width:.2f}" height="24" rx="5" fill="{fill}"/>'


def main() -> None:
    summary = json.loads(SUMMARY.read_text())
    models = summary["models"]
    width, height = 1040, 500
    left_x, right_x = 70, 555
    bar_x_offset = 180
    bar_width = 265
    rows_y = [205, 275, 345]
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">'
        ),
        '<title id="title">Retrospective finance environment-selection audit</title>',
        (
            '<desc id="description">The quality-aware rule chooses ten of twelve reported '
            "winners with low regret. Leave-one-study-out ridge chooses eight, while selecting "
            "the arm with more training chooses six.</desc>"
        ),
        '<rect width="1040" height="500" fill="#FFFFFF"/>',
        "<style>text{font-family:Inter,Arial,sans-serif;fill:#172033}.title{font-size:28px;font-weight:700}.subtitle{font-size:17px;fill:#586174}.panel{font-size:19px;font-weight:700}.label{font-size:16px}.value{font-size:16px;font-weight:700}.axis{font-size:13px;fill:#687184}.note{font-size:14px;fill:#586174}</style>",
        svg_text(70, 58, "Published finance evidence favors quality over volume", class_="title"),
        svg_text(
            70,
            88,
            "Retrospective grouped audit · 12 decision panels · 4 independent studies",
            class_="subtitle",
        ),
        '<line x1="70" y1="112" x2="970" y2="112" stroke="#D9DEE7" stroke-width="1"/>',
        svg_text(left_x, 150, "Reported winner selected", class_="panel"),
        svg_text(right_x, 150, "Mean normalized regret", class_="panel"),
        svg_text(left_x + bar_x_offset, 176, "0", class_="axis", text_anchor="middle"),
        svg_text(
            left_x + bar_x_offset + bar_width, 176, "100%", class_="axis", text_anchor="middle"
        ),
        svg_text(right_x + bar_x_offset, 176, "0", class_="axis", text_anchor="middle"),
        svg_text(
            right_x + bar_x_offset + bar_width, 176, "0.30", class_="axis", text_anchor="middle"
        ),
    ]

    for (key, label, color), y in zip(MODELS, rows_y, strict=True):
        accuracy = float(models[key]["top_choice_accuracy"])
        regret = float(models[key]["mean_normalized_regret"])
        accuracy_width = bar_width * accuracy
        regret_width = bar_width * regret / 0.30
        parts.extend(
            [
                svg_text(left_x, y + 5, label, class_="label"),
                svg_rect(left_x + bar_x_offset, y - 15, bar_width, "#EEF1F5"),
                svg_rect(left_x + bar_x_offset, y - 15, accuracy_width, color),
                svg_text(
                    left_x + bar_x_offset + accuracy_width + 9,
                    y + 4,
                    f"{round(accuracy * 12)}/12",
                    class_="value",
                ),
                svg_text(right_x, y + 5, label, class_="label"),
                svg_rect(right_x + bar_x_offset, y - 15, bar_width, "#EEF1F5"),
                svg_rect(right_x + bar_x_offset, y - 15, regret_width, color),
                svg_text(
                    right_x + bar_x_offset + regret_width + 9,
                    y + 4,
                    f"{regret:.3f}",
                    class_="value",
                ),
            ]
        )

    parts.extend(
        [
            '<line x1="70" y1="392" x2="970" y2="392" stroke="#D9DEE7" stroke-width="1"/>',
            svg_text(
                70,
                426,
                (
                    "Quality-aware rule: data quality, retention, verifier alignment, "
                    "and policy-relative difficulty."
                ),
                class_="note",
            ),
            svg_text(
                70,
                454,
                (
                    "Exploratory evidence: all outcomes were public before the feature "
                    "schema was assembled."
                ),
                class_="note",
            ),
            "</svg>",
        ]
    )
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(parts) + "\n")


if __name__ == "__main__":
    main()
