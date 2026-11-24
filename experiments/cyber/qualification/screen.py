"""One entry point for screening decisions.

Two verbs cover the screening workflow.

    report   given per-arm success counts at a fixed number of rollouts, decide
             whether a champion exists and what density to publish for it.
    plan     given the number of candidates and the separation worth detecting,
             return the per-arm budget and the identification probability.

Both verbs read the laws in this directory rather than restating them, so the
numbers they print are the numbers the scripts verify.
"""

from __future__ import annotations

import argparse
import json

import numpy as np

import screening_budget as budget
import selection_law as law


def report(counts: list[int], trials: int, alpha: float = 0.05) -> dict[str, object]:
    counts_array = np.array(counts)
    answer = law.report(counts_array, trials=trials, alpha=alpha)
    winner = int(np.argmax((counts_array / trials) * (1 - counts_array / trials)))
    return {
        "trials_per_arm": trials,
        "candidates": len(counts),
        "winner_index": winner,
        "winner_count": int(counts[winner]),
        "regime": answer["regime"],
        "raw_density": round(float(answer["raw"]), 4),
        "reported_density": round(float(answer["corrected"]), 4),
        "p_value": round(float(answer["pvalue"]), 4),
    }


def plan(
    candidates: int, ratio: float, target: float, baseline: float = 0.035
) -> dict[str, object]:
    leader = (1 - (1 - 4 * baseline * (1 - baseline) * ratio) ** 0.5) / 2
    trials = budget.trials_for_pcs(target, leader, candidates, baseline=baseline)
    even = budget.pcs_exact(leader, budget.TOTAL // candidates, candidates, baseline=baseline)
    racing = budget.racing_pcs(ratio, candidates, keep=4, pilot_fraction=0.5)
    return {
        "candidates": candidates,
        "ratio": ratio,
        "baseline": baseline,
        "leader_rate": round(leader, 4),
        "target_identification": target,
        "trials_per_arm_needed": trials,
        "total_rollouts_needed": trials * candidates,
        "identification_at_400_per_arm": round(even, 3),
        "identification_with_racing_at_4000": round(racing, 3),
        "advice": (
            "spend the depth"
            if trials * candidates > 400 * candidates
            else "the published budget suffices"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    verbs = parser.add_subparsers(dest="verb", required=True)
    rep = verbs.add_parser("report")
    rep.add_argument("--counts", required=True, help="comma separated success counts per candidate")
    rep.add_argument("--trials", type=int, default=400)
    rep.add_argument("--alpha", type=float, default=0.05)
    rep.add_argument("--json", action="store_true")
    pla = verbs.add_parser("plan")
    pla.add_argument("--candidates", type=int, default=10)
    pla.add_argument("--ratio", type=float, default=1.5)
    pla.add_argument("--target", type=float, default=0.9)
    pla.add_argument("--baseline", type=float, default=0.035)
    pla.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.verb == "report":
        counts = [int(value) for value in args.counts.split(",")]
        answer = report(counts, args.trials, args.alpha)
    else:
        answer = plan(args.candidates, args.ratio, args.target, args.baseline)
    if args.json:
        print(json.dumps(answer, indent=2))
        return
    for key, value in answer.items():
        print("%-32s %s" % (key, value))


if __name__ == "__main__":
    main()
