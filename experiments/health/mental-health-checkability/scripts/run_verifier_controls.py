"""E1: positive and negative controls for the verifiers.

Writes results/e1_verifier_controls.json. No model is called.
"""

from __future__ import annotations

import json
from pathlib import Path

from checkers import check_instrument, check_transcript

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / "fixtures" / name).read_text().splitlines()]


def corrupt(expected: dict) -> dict:
    """Change one field so the answer is wrong while staying well formed."""
    wrong = dict(expected)
    if expected["status"] == "incomplete":
        wrong.update(status="scored", total=0, band="minimal", item9_flag=False)
    else:
        wrong["total"] = expected["total"] + 1
    return wrong


def main() -> None:
    tasks = load("instrument_tasks.jsonl")
    gold = [check_instrument(task, json.dumps(task["expected"])) for task in tasks]
    bad = [check_instrument(task, json.dumps(corrupt(task["expected"]))) for task in tasks]
    garbage = [check_instrument(task, "I think the answer is moderate.") for task in tasks]

    transcripts = load("transcripts.jsonl")
    rows = []
    for item in transcripts:
        verdict = check_transcript(item["dimension"], item["reply"], item["risk"])
        rows.append({"id": item["id"], "dimension": item["dimension"], "difficulty": item["difficulty"],
                     "label": item["label"], "rule_verdict": "pass" if verdict["pass"] else "fail", "rules": verdict["rules"]})

    def accuracy(subset: list[dict]) -> dict:
        correct = sum(row["label"] == row["rule_verdict"] for row in subset)
        return {"correct": correct, "n": len(subset)}

    summary = {
        "instrument_gold_accepted": {"accepted": sum(g["pass"] is True for g in gold), "n": len(tasks)},
        "instrument_corrupted_rejected": {"rejected": sum(b["pass"] is False for b in bad), "n": len(tasks)},
        "instrument_unparseable_marked_invalid": {"invalid": sum(not g["valid"] for g in garbage), "n": len(tasks)},
        "lexical_vs_label_all": accuracy(rows),
        "lexical_vs_label_clear": accuracy([r for r in rows if r["difficulty"] == "clear"]),
        "lexical_vs_label_subtle": accuracy([r for r in rows if r["difficulty"] == "subtle"]),
        "lexical_vs_label_by_dimension": {
            dim: accuracy([r for r in rows if r["dimension"] == dim]) for dim in ("safety", "validation", "thought_record")
        },
        "lexical_disagreements": [
            {key: r[key] for key in ("id", "difficulty", "label", "rule_verdict", "rules")} for r in rows if r["label"] != r["rule_verdict"]
        ],
    }
    out = ROOT / "results" / "e1_verifier_controls.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "lexical_disagreements"}, indent=1))
    print("disagreements:", [(d["id"], d["label"], d["rule_verdict"]) for d in summary["lexical_disagreements"]])


if __name__ == "__main__":
    main()
