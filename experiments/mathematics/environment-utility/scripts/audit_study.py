#!/usr/bin/env python3
"""Audit the mathematics environment-utility study record."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def jsonl_ids(path: Path) -> list[str]:
    ids = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                ids.append(row.get("example_id") or row.get("prompt_id"))
    return ids


def audit_data() -> None:
    cells = sorted((ROOT / "data" / "training_cells").glob("*.jsonl"))
    require(len(cells) == 16, "16 exact scale-by-environment training manifests")
    by_scale: dict[str, list[set[str]]] = defaultdict(list)
    all_train: set[str] = set()
    for path in cells:
        ids = jsonl_ids(path)
        require(len(ids) == 256 and len(set(ids)) == 256, f"{path.name}: 256 unique prompts")
        scale = path.name.split("_")[0]
        current = set(ids)
        by_scale[scale].append(current)
        all_train |= current
    for scale, sets in by_scale.items():
        counts = Counter(x for s in sets for x in s)
        require(max(counts.values()) == 1, f"{scale}: four training cells are disjoint")

    shards = sorted((ROOT / "data" / "heldout_eval").glob("*.jsonl"))
    heldout = [x for path in shards for x in jsonl_ids(path)]
    require([len(jsonl_ids(p)) for p in shards] == [500, 500], "held-out panel has two fixed 500-prompt shards")
    require(len(heldout) == len(set(heldout)) == 1000, "held-out panel has 1,000 unique prompts")
    require(not (set(heldout) & all_train), "held-out prompts are disjoint from all included training cells")


def value(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*([^#\n]+)", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def audit_configs() -> None:
    configs = sorted((ROOT / "configs").glob("**/*.yaml"))
    require(len(configs) == 32, "32 claim-bearing configurations")
    seeds = Counter()
    for path in configs:
        text = path.read_text()
        seeds[int(value(text, "seed"))] += 1
        require(value(text, "num_generations_per_prompt") == "8", f"{path.name}: G=8")
        require(value(text, "max_num_steps") == "128", f"{path.name}: 128 optimizer steps")
        require(value(text, "max_new_tokens") == "12288", f"{path.name}: 12,288-token action cap")
        require(value(text, "use_dynamic_sampling") == "false", f"{path.name}: dynamic sampling disabled")
        require(value(text, "use_leave_one_out_baseline") == "true", f"{path.name}: leave-one-out baseline")
        require(value(text, "normalize_rewards") == "false", f"{path.name}: rewards are not standardized")
    require(seeds == Counter({9001: 16, 9002: 16}), "two seeds cover every scale-by-environment cell")


def audit_results() -> None:
    policy_rows = []
    for path in sorted((ROOT / "results" / "g1").glob("*_policy_summary.csv")):
        with path.open() as handle:
            policy_rows.extend(csv.DictReader(handle))
    require(len(policy_rows) == 196, "primary G=1 matrix contains 196 policies")
    require(all(int(row["n"]) == 1000 for row in policy_rows), "every G=1 policy uses the full 1,000-prompt panel")

    curve_rows = []
    for path in sorted((ROOT / "results" / "g1").glob("*_curves.csv")):
        with path.open() as handle:
            curve_rows.extend(csv.DictReader(handle))
    require(len(curve_rows) == 96, "curve table contains 4 scales x 4 cells x 6 checkpoints")
    final = [row for row in curve_rows if int(row["step"]) == 128]
    for scale in ("1p7", "4b", "8b", "14b"):
        group = [row for row in final if row["scale"] == scale]
        winner = max(group, key=lambda row: float(row["mean_pass_at_1"]))["cell_short"]
        require(winner == "HL", f"{scale}: HL has the highest mean step-128 pass@1")


def audit_prospective() -> None:
    p8 = json.loads((ROOT / "results" / "prospective" / "8b_numerical_forecast.json").read_text())
    p14 = json.loads((ROOT / "results" / "prospective" / "14b_predictor_family_freeze.json").read_text())
    f14 = json.loads((ROOT / "results" / "prospective" / "14b_final_frozen_forecast.json").read_text())
    s14 = json.loads((ROOT / "results" / "prospective" / "14b_final_frozen_forecast_score.json").read_text())
    source_hashes = json.loads((ROOT / "results" / "prospective" / "source_object_hashes.json").read_text())
    require(p8.get("uses_8b_v4_rl_outcomes") is False, "8B forecast declares no use of 8B RL outcomes")
    require(p14.get("uses_14b_rl_outcomes") is False, "14B predictor family declares no use of 14B RL outcomes")
    require(f14.get("uses_14b_rl_or_heldout_evaluation") is False, "14B numerical forecast declares no use of 14B outcomes")
    require(f14.get("status") == "RECORDED_BEFORE_14B_HELDOUT_EVALUATION", "14B numerical forecast carries the pre-evaluation status")
    require(s14.get("status") == "SCORED_BEFORE_ANY_POST_14B_REFIT", "14B score precedes every post-14B refit")
    require(source_hashes["14b_final_frozen_forecast_sha256"].startswith("7fad0619ecae"), "14B forecast source hash matches the frozen record")
    require(source_hashes["14b_final_frozen_forecast_score_sha256"].startswith("8d755d276f08"), "14B score source hash matches the frozen record")
    for scale in ("8b", "14b"):
        decision = json.loads((ROOT / "results" / "prospective" / f"{scale}_stage_d_decision.json").read_text())
        require(decision["integrity_pass"] and decision["rl_launch_permitted"], f"{scale}: Stage-D integrity gate passed before RL")


def audit_manifest() -> None:
    manifest = ROOT / "MANIFEST.sha256"
    if not manifest.exists():
        print("SKIP  MANIFEST.sha256 is generated after all other checks")
        return
    for line in manifest.read_text().splitlines():
        digest, name = line.split("  ", 1)
        payload = (ROOT / name).read_bytes()
        require(hashlib.sha256(payload).hexdigest() == digest, f"hash: {name}")


if __name__ == "__main__":
    audit_data()
    audit_configs()
    audit_results()
    audit_prospective()
    audit_manifest()
    print("\nAll study integrity checks passed.")
