"""Audit the frozen feasibility design; analyse one outcome per matched seed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "seed", "control_run_id", "treatment_run_id", "panel_sha256",
    "n_items", "correct_control", "correct_treatment",
}


def analyse(rows: list[dict[str, str]]) -> dict:
    """One difference per seed; never treat test items as training replicates."""
    if len(rows) != 9:
        raise ValueError("exactly nine matched training pairs required")
    seeds, runs, panels = set(), set(), set()
    differences = []
    for row in rows:
        if set(row) != FIELDS:
            raise ValueError("expected run-level columns only")
        seed = int(row["seed"])
        control = row["control_run_id"].strip()
        treatment = row["treatment_run_id"].strip()
        panel = row["panel_sha256"]
        if seed < 0 or seed in seeds:
            raise ValueError("training seed must be unique")
        if not control or not treatment or control == treatment or {control, treatment} & runs:
            raise ValueError("training run identities must be unique across pairs")
        if len(panel) != 64 or any(c not in "0123456789abcdef" for c in panel):
            raise ValueError("expected a SHA-256 panel digest")
        n, a, b = (int(row[k]) for k in ("n_items", "correct_control", "correct_treatment"))
        if n != 300 or not (0 <= a <= n and 0 <= b <= n):
            raise ValueError("invalid fixed-panel counts")
        seeds.add(seed)
        runs.update((control, treatment))
        panels.add(panel)
        differences.append(100 * (b - a) / n)
    if len(panels) != 1:
        raise ValueError("all runs must use the same evaluation panel")
    mean = statistics.mean(differences)
    sd = statistics.stdev(differences)
    se = sd / math.sqrt(len(differences))
    # t(8, .975); approximate interval, not a confirmatory power statement.
    margin = 2.306004135 * se
    positive = sum(d > 0 for d in differences)
    negative = sum(d < 0 for d in differences)
    nonzero = positive + negative
    sign_p = min(
        1.0,
        2 * sum(math.comb(nonzero, k) for k in range(min(positive, negative) + 1))
        / 2**nonzero,
    )
    return {
        "analysis_unit": "matched_training_seed_pair",
        "n_pairs": len(differences),
        "differences_pp": differences,
        "mean_pp": mean,
        "between_pair_sd_pp": sd,
        "approximate_t95_pp": [mean - margin, mean + margin] if sd else None,
        "secondary_sign_p": sign_p,
        "power_claim": None,
    }


def validate_design(plan: dict) -> None:
    expected = {
        "analysis_unit": "matched_training_seed_pair", "pairs": 9,
        "items_per_run": 300, "runs": 18,
        "primary_analysis": "mean paired run difference; approximate t interval",
        "target_power": None, "status": "feasibility_only",
    }
    if any(plan.get(k) != v for k, v in expected.items()):
        raise ValueError("design must retain nine seed pairs without pooled-item power")


def audit(root: Path = ROOT) -> None:
    validate_design(json.loads((root / "design/next-panel.json").read_text()))
    protocol = json.loads((root / "protocol.json").read_text())
    if "matched training seed pair" not in protocol["experimental_units"]:
        raise ValueError("invalid experimental unit in protocol")
    for a in protocol["artifacts"]:
        data = (root / a["uri"]).read_bytes()
        if (
            a["sha256"] != "sha256:" + hashlib.sha256(data).hexdigest()
            or a["size_bytes"] != len(data)
        ):
            raise ValueError(f"artifact mismatch: {a['uri']}")
    for line in (root / "MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"manifest mismatch: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, help="completed run-pair CSV")
    args = parser.parse_args()
    audit()
    if args.runs is None:
        print("Feasibility design and hashes verified; no training results claimed.")
        return
    with args.runs.open(newline="", encoding="utf-8") as handle:
        print(json.dumps(analyse(list(csv.DictReader(handle))), indent=2))


if __name__ == "__main__":
    main()
