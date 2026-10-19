"""Operating-characteristic simulation for the warm-start reliability gate.

This is a DESIGN tool, frozen before any cyber rollout. It does NOT loosen any
gate and does NOT assume the starting policy's success rate. It sweeps a range
of plausible per-task success rates and reports, for the frozen probe design
(group_size=16 realized as two independent G=8 views over 48 tasks), the
probability that two independent views agree within the frozen reliability
thresholds even when the underlying environment coordinates are identical.

Purpose: choose the rollout budget and the "unmeasurable" abstention rule, not
the pass thresholds. If the agreement probability is low across the plausible
range, the correct response is more rollouts or an explicit abstention verdict,
never a weaker threshold.

Frozen thresholds (from qualification-protocol, unchanged in v2):
  rho symmetric relative difference <= 0.20
  H absolute difference             <= 0.10
  mixed-fraction absolute difference<= 0.10

Advantage mass model: for a group of G binary rewards with k successes, the
unnormalized leave-one-out absolute advantage mass is 2*k*(G-k)/(G-1). This
matches packages/environments metrics (all-success / all-failure => 0 mass).
"""

from __future__ import annotations

import argparse
import json
from statistics import NormalDist

import numpy as np


def group_mass(k: np.ndarray, g: int) -> np.ndarray:
    """Unnormalized leave-one-out absolute advantage mass per group."""
    return 2.0 * k * (g - k) / (g - 1)


def coverage(mass: np.ndarray) -> float:
    total = float(mass.sum())
    sq = float((mass * mass).sum())
    return 0.0 if sq == 0.0 else (total * total) / sq / len(mass)


def simulate(
    *,
    tasks: int,
    g: int,
    mean_success: float,
    concentration: float,
    trials: int,
    rho_rel: float,
    h_abs: float,
    mix_abs: float,
    seed: int,
) -> dict[str, float]:
    """Return gate-pass probabilities under identical true coordinates.

    Task difficulty is drawn from Beta(mean*c, (1-mean)*c); lower concentration
    c means more heterogeneous tasks. Both views share the same drawn per-task
    success probabilities, so any disagreement is sampling noise, not a real
    coordinate difference.
    """
    rng = np.random.default_rng(seed)
    a = mean_success * concentration
    b = (1.0 - mean_success) * concentration
    pass_rho = pass_h = pass_mix = pass_all = 0
    mixed_fracs = []
    for _ in range(trials):
        p = rng.beta(a, b, tasks)
        k1 = rng.binomial(g, p)
        k2 = rng.binomial(g, p)
        m1, m2 = group_mass(k1, g), group_mass(k2, g)
        r1, r2 = float(m1.sum()), float(m2.sum())
        rho_ok = (r1 + r2) > 0 and abs(r1 - r2) / ((r1 + r2) / 2.0) <= rho_rel
        h_ok = abs(coverage(m1) - coverage(m2)) <= h_abs
        f1 = float(((k1 > 0) & (k1 < g)).mean())
        f2 = float(((k2 > 0) & (k2 < g)).mean())
        mix_ok = abs(f1 - f2) <= mix_abs
        pass_rho += rho_ok
        pass_h += h_ok
        pass_mix += mix_ok
        pass_all += rho_ok and h_ok and mix_ok
        # pooled mixed-group fraction across the two views (headroom signal)
        kp = k1 + k2
        mixed_fracs.append(float(((kp > 0) & (kp < 2 * g)).mean()))
    return {
        "mean_success": mean_success,
        "concentration": concentration,
        "p_rho_gate": pass_rho / trials,
        "p_h_gate": pass_h / trials,
        "p_mixed_gate": pass_mix / trials,
        "p_all_reliability_gates": pass_all / trials,
        "median_pooled_mixed_fraction": float(np.median(mixed_fracs)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=48)
    parser.add_argument("--group-size", type=int, default=8, help="per-view G")
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--rho-rel", type=float, default=0.20)
    parser.add_argument("--h-abs", type=float, default=0.10)
    parser.add_argument("--mix-abs", type=float, default=0.10)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    # Sweep plausible success rates WITHOUT assuming the starting policy's rate.
    sweep = [0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.40]
    concentrations = [1.0, 4.0]  # heterogeneous and moderately homogeneous tasks
    rows = []
    for mean in sweep:
        for conc in concentrations:
            rows.append(
                simulate(
                    tasks=args.tasks,
                    g=args.group_size,
                    mean_success=mean,
                    concentration=conc,
                    trials=args.trials,
                    rho_rel=args.rho_rel,
                    h_abs=args.h_abs,
                    mix_abs=args.mix_abs,
                    seed=args.seed,
                )
            )

    # Abstention rule: a success regime is declared "reliably measurable" only
    # where P(all reliability gates agree | identical coordinates) >= 0.80.
    abstain_below = None
    for mean in sweep:
        both = [r for r in rows if r["mean_success"] == mean]
        if all(r["p_all_reliability_gates"] >= 0.80 for r in both):
            abstain_below = mean
            break

    z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(0.80)
    artifact = {
        "schema_version": "anarres.cyber-reliability-oc.v1",
        "frozen_before_any_cyber_rollout": True,
        "assumes_starting_policy_success_rate": False,
        "design": {
            "tasks": args.tasks,
            "per_view_group_size": args.group_size,
            "independent_views": 2,
            "trials": args.trials,
            "seed": args.seed,
        },
        "frozen_thresholds": {
            "rho_symmetric_relative_difference": args.rho_rel,
            "H_absolute_difference": args.h_abs,
            "mixed_fraction_absolute_difference": args.mix_abs,
        },
        "abstention_rule": {
            "declare_measurable_when_p_all_gates_at_least": 0.80,
            "lowest_mean_success_reliably_measurable": abstain_below,
            "below_this_rate_action": (
                "increase rollouts or return UNMEASURABLE; never lower thresholds"
            ),
        },
        "normal_z_sum_alpha05_power80": z,
        "sweep": rows,
    }
    text = json.dumps(artifact, indent=2)
    if args.output:
        with open(args.output, "w") as handle:
            handle.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
