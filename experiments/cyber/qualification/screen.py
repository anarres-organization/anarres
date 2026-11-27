"""Report conditional global homogeneity or plan a declared iid sensitivity."""

from __future__ import annotations

import argparse
import json

from screening_budget import grid_plan, leader_rate, pcs_exact, racing_pcs
from selection_law import report as conditional_report


def report(counts: list[int], trials: int, alpha: float = 0.05) -> dict:
    return conditional_report(counts, trials, alpha)


def plan(candidates: int, ratio: float, target: float, baseline: float = 0.035) -> dict:
    if type(candidates) is not int or not 2 <= candidates <= 50:
        raise ValueError("require 2..50 candidates")
    leader = leader_rate(ratio, baseline)
    result = grid_plan(target, leader, candidates, baseline)
    return {
        "baseline": baseline,
        "leader_rate": leader,
        "variance_ratio": ratio,
        "candidates": candidates,
        "target": target,
        "pcs_at_400_per_arm": pcs_exact(leader, 400, candidates, baseline),
        "racing_at_4000": racing_pcs(
            ratio, candidates, min(4, candidates), 0.5, baseline=baseline
        ),
        **result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    rep = commands.add_parser("report")
    rep.add_argument("--counts", required=True)
    rep.add_argument("--trials", type=int, default=400)
    rep.add_argument("--alpha", type=float, default=0.05)
    rep.add_argument("--json", action="store_true")
    pla = commands.add_parser("plan")
    pla.add_argument("--candidates", type=int, default=10)
    pla.add_argument("--ratio", type=float, default=1.5)
    pla.add_argument("--target", type=float, default=0.9)
    pla.add_argument("--baseline", type=float, default=0.035)
    pla.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = (
            report([int(x) for x in args.counts.split(",")], args.trials, args.alpha)
            if args.command == "report"
            else plan(args.candidates, args.ratio, args.target, args.baseline)
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
