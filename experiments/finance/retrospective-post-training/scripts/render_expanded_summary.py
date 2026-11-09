#!/usr/bin/env python3
"""Render the expanded finance evidence bridge as a deterministic SVG."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "expanded_summary.json"
OUTPUT = ROOT / "figures" / "expanded_evidence_bridge.svg"


def text(x: float, y: float, value: str, css: str, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" class="{css}" text-anchor="{anchor}">{html.escape(value)}</text>'


def bar(x: float, y: float, value: float, maximum: float, color: str) -> list[str]:
    width = 238
    active = max(0.0, min(width, width * value / maximum))
    return [
        f'<rect x="{x}" y="{y}" width="{width}" height="22" rx="5" fill="#EEF1F5"/>',
        f'<rect x="{x}" y="{y}" width="{active:.2f}" height="22" rx="5" fill="{color}"/>',
    ]


def main() -> None:
    summary = json.loads(SUMMARY.read_text())
    source = summary["evaluations"]["leave_one_source_out"]
    holdouts = [
        ("New study", source["ridge"]),
        ("New model", summary["evaluations"]["leave_one_model_out"]["ridge"]),
        ("New target", summary["evaluations"]["leave_one_target_out"]["ridge"]),
    ]
    rules = [
        ("Measurement rule", source["practical_rule"], "#16836B"),
        ("More data", source["more_data"], "#9AA4B2"),
        ("Random fingerprint", source["random_fingerprint"], "#C8CDD6"),
    ]
    support = summary["support"]
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="560" '
            'viewBox="0 0 1120 560" role="img" aria-labelledby="title desc">'
        ),
        '<title id="title">Expanded finance evidence bridge</title>',
        (
            '<desc id="desc">A fixed measurement rule outperforms choosing more data '
            "across held-out studies. Fitted transfer is stronger to a new model or target "
            "within a known study than to a wholly new study.</desc>"
        ),
        '<rect width="1120" height="560" fill="#FFFFFF"/>',
        "<style>text{font-family:Inter,Arial,sans-serif;fill:#172033}.title{font-size:28px;font-weight:700}.subtitle{font-size:16px;fill:#596275}.panel{font-size:19px;font-weight:700}.label{font-size:15px}.value{font-size:15px;font-weight:700}.axis{font-size:12px;fill:#697386}.note{font-size:14px;fill:#596275}</style>",
        text(
            60, 54, "Measurements beat volume, but transfer to a new study remains harder", "title"
        ),
        text(
            60,
            84,
            (
                f"Retrospective grouped audit · {support['panels']} decision panels · "
                f"{support['arms']} trained arms · {support['sources']} studies"
            ),
            "subtitle",
        ),
        '<line x1="60" y1="108" x2="1060" y2="108" stroke="#D9DEE7"/>',
        text(60, 145, "Held-out-study decision ordering", "panel"),
        text(595, 145, "Fitted transfer across holdouts", "panel"),
        text(235, 172, "pair ordering", "axis", "middle"),
        text(770, 172, "pair ordering", "axis", "middle"),
        text(998, 172, "regret", "axis", "middle"),
    ]
    y_values = [205, 270, 335]
    for (label, values, color), y in zip(rules, y_values, strict=True):
        values = values["source_macro"]
        ordering = values["pairwise_ordering"]
        regret = values["mean_normalized_regret"]
        parts.extend([text(60, y + 17, label, "label"), *bar(180, y, ordering, 1.0, color)])
        parts.append(text(430, y + 17, f"{ordering * 100:.1f}% · regret {regret:.3f}", "value"))

    for (label, values), y in zip(holdouts, y_values, strict=True):
        values = values["source_macro"]
        ordering = values["pairwise_ordering"]
        regret = values["mean_normalized_regret"]
        color = "#3569A8" if label == "New study" else "#16836B"
        parts.extend([text(595, y + 17, label, "label"), *bar(700, y, ordering, 1.0, color)])
        parts.append(text(950, y + 17, f"{ordering * 100:.1f}%", "value"))
        parts.append(text(1032, y + 17, f"{regret:.3f}", "value", "end"))

    parts.extend(
        [
            '<line x1="60" y1="398" x2="1060" y2="398" stroke="#D9DEE7"/>',
            text(
                60,
                434,
                (
                    "The measurement rule uses source-reported alignment, composition, "
                    "supervision, selection, and retention properties."
                ),
                "note",
            ),
            text(
                60,
                462,
                (
                    "Equal-study summaries prevent papers with many reported targets from "
                    "dominating the comparison."
                ),
                "note",
            ),
            text(
                60,
                490,
                (
                    "All outcomes were public before this retrospective mapping; the untouched "
                    "prospective panel remains the decisive test."
                ),
                "note",
            ),
            "</svg>",
        ]
    )
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(parts) + "\n")


if __name__ == "__main__":
    main()
