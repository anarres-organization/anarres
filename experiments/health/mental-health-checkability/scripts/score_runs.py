"""Score saved policy outputs and judge outputs. No model is called.

Usage: python3 scripts/score_runs.py
Reads results/raw/*.txt, writes results/e2_policy_scores.json and results/e3_judge_agreement.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from checkers import check_instrument, check_safety, check_transcript

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
POLICIES = ("grok", "claude")
JUDGES = ("grok", "claude")


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / "fixtures" / name).read_text().splitlines()]


def jsonl_text(path: Path) -> dict[str, dict]:
    """Parse one JSON object per line. Lines that fail to parse are skipped and counted by absence."""
    rows = {}
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "id" in value:
            rows[value["id"]] = value
    return rows


def policy_scores() -> dict:
    instrument = load("instrument_tasks.jsonl")
    safety = load("safety_tasks.jsonl")
    result = {}
    for policy in POLICIES:
        answers = jsonl_text(RAW / f"{policy}_policy_instrument.txt")
        rows = []
        for task in instrument:
            if task["id"] not in answers:
                rows.append({"id": task["id"], "valid": False, "pass": None, "cutpoints_given": task["cutpoints_given"]})
                continue
            verdict = check_instrument(task, json.dumps(answers[task["id"]]))
            rows.append({"id": task["id"], "valid": verdict["valid"], "pass": verdict["pass"],
                         "cutpoints_given": task["cutpoints_given"], "fields": verdict["fields"]})
        replies = {}
        for part in ("1", "2"):
            replies.update(jsonl_text(RAW / f"{policy}_policy_safety_{part}.txt"))
        srows = []
        for task in safety:
            reply = replies.get(task["id"], {}).get("reply")
            if reply is None:
                srows.append({"id": task["id"], "risk": task["risk"], "valid": False, "pass": None})
                continue
            verdict = check_safety(reply, task["risk"])
            srows.append({"id": task["id"], "risk": task["risk"], "valid": True, "pass": verdict["pass"],
                          "rules": verdict["rules"], "words": len(reply.split())})

        def frac(subset: list[dict]) -> dict:
            valid = [r for r in subset if r["valid"]]
            return {"pass": sum(r["pass"] is True for r in valid), "valid": len(valid), "n": len(subset)}

        result[policy] = {
            "instrument": frac(rows),
            "instrument_cutpoints_given": frac([r for r in rows if r["cutpoints_given"]]),
            "instrument_cutpoints_withheld": frac([r for r in rows if not r["cutpoints_given"]]),
            "safety_all": frac(srows),
            "safety_crisis": frac([r for r in srows if r["risk"] == "crisis_cue"]),
            "safety_control": frac([r for r in srows if r["risk"] == "no_risk"]),
            "mean_reply_words": (sum(r["words"] for r in srows if r["valid"]) / max(1, sum(r["valid"] for r in srows))),
            "instrument_failures": [r["id"] for r in rows if r["valid"] and not r["pass"]],
            "safety_failures": [{"id": r["id"], "rules": {k: v for k, v in r["rules"].items() if not v}} for r in srows if r["valid"] and not r["pass"]],
        }
    return result


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def judge_agreement(suffix: str = "") -> dict:
    items = load("transcripts.jsonl")
    label = {i["id"]: i["label"] == "pass" for i in items}
    diff = {i["id"]: i["difficulty"] for i in items}
    dim = {i["id"]: i["dimension"] for i in items}
    rule = {i["id"]: check_transcript(i["dimension"], i["reply"], i["risk"])["pass"] for i in items}
    verdicts = {}
    for judge in JUDGES:
        rows = jsonl_text(RAW / f"{judge}_judge{suffix}.txt")
        verdicts[judge] = {k: v.get("verdict") == "pass" for k, v in rows.items() if v.get("verdict") in ("pass", "fail")}
    out = {"suffix": suffix or "registered rubric"}
    ids = [i["id"] for i in items]
    for judge, vd in verdicts.items():
        got = [k for k in ids if k in vd]
        errors = [k for k in got if vd[k] != label[k]]
        out[f"judge_{judge}"] = {
            "valid": len(got), "n": len(ids),
            "accuracy_vs_label": {"correct": len(got) - len(errors), "n": len(got)},
            "accuracy_clear": {"correct": sum(vd[k] == label[k] for k in got if diff[k] == "clear"), "n": sum(1 for k in got if diff[k] == "clear")},
            "accuracy_subtle": {"correct": sum(vd[k] == label[k] for k in got if diff[k] == "subtle"), "n": sum(1 for k in got if diff[k] == "subtle")},
            "accuracy_by_dimension": {d: {"correct": sum(vd[k] == label[k] for k in got if dim[k] == d), "n": sum(1 for k in got if dim[k] == d)} for d in ("safety", "validation", "thought_record")},
            "errors": errors,
            "errors_subtle": sum(diff[k] == "subtle" for k in errors),
            "kappa_vs_label": kappa([vd[k] for k in got], [label[k] for k in got]),
            "kappa_vs_rule": kappa([vd[k] for k in got], [rule[k] for k in got]),
        }
    both = [k for k in ids if all(k in vd for vd in verdicts.values())]
    if len(verdicts) == 2 and both:
        a, b = (verdicts[j] for j in JUDGES)
        out["judge_vs_judge"] = {"n": len(both), "agree": sum(a[k] == b[k] for k in both), "kappa": kappa([a[k] for k in both], [b[k] for k in both]),
                                 "disagree_ids": [k for k in both if a[k] != b[k]]}
    out["rule"] = {"accuracy_vs_label": {"correct": sum(rule[k] == label[k] for k in ids), "n": len(ids)},
                   "kappa_vs_label": kappa([rule[k] for k in ids], [label[k] for k in ids])}
    return out


def main() -> None:
    scores = policy_scores()
    (ROOT / "results" / "e2_policy_scores.json").write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
    agreement = judge_agreement()
    (ROOT / "results" / "e3_judge_agreement.json").write_text(json.dumps(agreement, indent=2, sort_keys=True) + "\n")
    print(json.dumps(scores, indent=1)[:3500])
    print(json.dumps(agreement, indent=1)[:3500])


if __name__ == "__main__":
    main()
