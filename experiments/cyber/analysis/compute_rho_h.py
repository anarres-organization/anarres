#!/usr/bin/env python3
"""Compute ρ (usable signal density) and H (effective coverage) from G-rollout results.

Implements Eq. 5-6 from the ICLR paper:
  ρ = 10^6 × (Σ_g A_g^adm) / (Σ_{g,i} ℓ_gi)     (signal per million tokens)
  H = (1/n_E) × (Σ_g A_g^adm)^2 / Σ_g (A_g^adm)^2  (effective coverage)

For binary rewards with k successes out of G rollouts per group:
  A_g^raw = 2k(G-k)/(G-1)   (Appendix D, Eq. 8)

Since we have no loss-contract admission filter, A_g^adm = A_g^raw.
"""

import argparse
import glob
import json
import os
from collections import defaultdict


def load_rollout_results(results_dir, G):
    """Load per-rollout results and group by task."""
    groups = defaultdict(list)

    for path in sorted(glob.glob(os.path.join(results_dir, "*_r*.json"))):
        fname = os.path.basename(path)
        parts = fname.replace(".json", "").rsplit("_r", 1)
        if len(parts) != 2:
            continue
        task_num, rollout_str = parts
        try:
            int(rollout_str)
        except ValueError:
            continue

        with open(path) as f:
            data = json.load(f)

        groups[task_num].append(data)

    complete = {}
    incomplete = []
    for task_num, rollouts in groups.items():
        if len(rollouts) >= G:
            complete[task_num] = sorted(rollouts, key=lambda r: r.get("rollout_id", 0))[:G]
        else:
            incomplete.append((task_num, len(rollouts)))

    return complete, incomplete


def compute_group_stats(rollouts, G):
    """Compute per-group statistics."""
    k = sum(1 for r in rollouts if r.get("success", False))
    total_output_tokens = sum(r.get("total_output_tokens", 0) for r in rollouts)
    total_input_tokens = sum(r.get("total_input_tokens", 0) for r in rollouts)

    # A_g^raw = 2k(G-k)/(G-1)  (binary reward, Appendix D Eq. 8)
    A_raw = 2 * k * (G - k) / (G - 1) if G > 1 else 0

    return {
        "task_id": rollouts[0].get("task_id", ""),
        "project": rollouts[0].get("project", ""),
        "G": G,
        "k": k,
        "success_rate": k / G,
        "A_raw": A_raw,
        "total_output_tokens": total_output_tokens,
        "total_input_tokens": total_input_tokens,
        "total_tokens": total_output_tokens + total_input_tokens,
        "mean_harness_time_s": (sum(r.get("harness_time_s", 0) for r in rollouts) / G),
    }


def compute_rho_h(group_stats_list):
    """Compute environment-level ρ and H from per-group stats."""
    n_E = len(group_stats_list)
    if n_E == 0:
        return {"rho": 0, "H": 0, "n_E": 0}

    sum_A = sum(g["A_raw"] for g in group_stats_list)
    sum_A_sq = sum(g["A_raw"] ** 2 for g in group_stats_list)

    # ℓ_gi = output tokens (generated length) per rollout
    sum_ell = sum(g["total_output_tokens"] for g in group_stats_list)

    # ρ = 10^6 × Σ A_g / Σ ℓ_gi  (Eq. 5)
    rho = 1e6 * sum_A / max(sum_ell, 1)

    # H = (1/n_E) × (Σ A_g)^2 / Σ (A_g)^2  (Eq. 6)
    H = (1 / n_E) * (sum_A**2) / max(sum_A_sq, 1e-12)

    # Also compute with total tokens (input + output) for comparison
    sum_total_tok = sum(g["total_tokens"] for g in group_stats_list)
    rho_total = 1e6 * sum_A / max(sum_total_tok, 1)

    return {
        "rho": rho,
        "rho_total_tokens": rho_total,
        "H": H,
        "n_E": n_E,
        "sum_A": sum_A,
        "sum_A_sq": sum_A_sq,
        "sum_output_tokens": sum_ell,
        "sum_total_tokens": sum_total_tok,
    }


def bootstrap_rho_h(group_stats_list, n_boot=2000, seed=42):
    """Bootstrap CI for ρ and H."""
    rng = __import__("random").Random(seed)
    n = len(group_stats_list)
    rho_samples = []
    h_samples = []

    for _ in range(n_boot):
        boot = [rng.choice(group_stats_list) for _ in range(n)]
        result = compute_rho_h(boot)
        rho_samples.append(result["rho"])
        h_samples.append(result["H"])

    rho_samples.sort()
    h_samples.sort()
    lo = int(n_boot * 0.025)
    hi = int(n_boot * 0.975)

    return {
        "rho_ci_95": [rho_samples[lo], rho_samples[hi]],
        "H_ci_95": [h_samples[lo], h_samples[hi]],
        "rho_median": rho_samples[n_boot // 2],
        "H_median": h_samples[n_boot // 2],
    }


def main():
    parser = argparse.ArgumentParser(description="Compute rho and H from G-rollout results")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--G", type=int, default=8)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=2000,
        help="Bootstrap iterations for CI (0 to skip)",
    )
    args = parser.parse_args()

    print(f"Loading rollout results from {args.results_dir} (G={args.G})")
    complete, incomplete = load_rollout_results(args.results_dir, args.G)

    if incomplete:
        print(f"\nWARNING: {len(incomplete)} tasks with incomplete rollouts:")
        for task_num, n in incomplete[:10]:
            print(f"  {task_num}: {n}/{args.G}")
        if len(incomplete) > 10:
            print(f"  ... and {len(incomplete) - 10} more")

    print(f"\n{len(complete)} complete groups (G={args.G})")

    group_stats = []
    for task_num in sorted(complete.keys()):
        rollouts = complete[task_num]
        stats = compute_group_stats(rollouts, args.G)
        group_stats.append(stats)

    # Print per-group table
    print(f"\n{'Task':<25s} {'k':>3s} {'Rate':>6s} {'A_raw':>6s} {'OutTok':>8s}")
    print("-" * 55)
    for g in sorted(group_stats, key=lambda x: -x["A_raw"]):
        print(
            f"{g['task_id']:<25s} {g['k']:3d} "
            f"{g['success_rate']:5.1%} {g['A_raw']:6.2f} "
            f"{g['total_output_tokens']:8d}"
        )

    # Environment-level metrics
    result = compute_rho_h(group_stats)
    print("\n=== Environment-level metrics ===")
    print(f"n_E (groups):         {result['n_E']}")
    print(f"Σ A_g (advantage):    {result['sum_A']:.2f}")
    print(f"Σ ℓ (output tokens):  {result['sum_output_tokens']:,}")
    print(f"ρ (per M out-tok):    {result['rho']:.2f}")
    print(f"ρ (per M all-tok):    {result['rho_total_tokens']:.2f}")
    print(f"H (eff coverage):     {result['H']:.4f}")

    # Distribution of k
    k_dist = defaultdict(int)
    for g in group_stats:
        k_dist[g["k"]] += 1
    print(f"\nk distribution (successes per {args.G} rollouts):")
    for k in range(args.G + 1):
        if k_dist[k] > 0:
            bar = "#" * k_dist[k]
            print(f"  k={k}: {k_dist[k]:3d} {bar}")

    # Groups with signal (k > 0 and k < G)
    signal_groups = [g for g in group_stats if 0 < g["k"] < args.G]
    zero_groups = [g for g in group_stats if g["k"] == 0]
    full_groups = [g for g in group_stats if g["k"] == args.G]
    print(
        f"\nSignal groups (0<k<G): {len(signal_groups)} "
        f"({len(signal_groups) / max(len(group_stats), 1):.1%})"
    )
    print(f"All-fail (k=0):        {len(zero_groups)}")
    print(f"All-success (k=G):     {len(full_groups)}")

    # Bootstrap
    if args.bootstrap > 0 and len(group_stats) > 1:
        print(f"\nBootstrap ({args.bootstrap} iterations)...")
        boot = bootstrap_rho_h(group_stats, n_boot=args.bootstrap)
        print(f"ρ 95% CI: [{boot['rho_ci_95'][0]:.2f}, {boot['rho_ci_95'][1]:.2f}]")
        print(f"H 95% CI: [{boot['H_ci_95'][0]:.4f}, {boot['H_ci_95'][1]:.4f}]")
        result.update(boot)

    # Output JSON
    output = {
        "environment": "CyberGym",
        "model": "feyospace-v1.1-small",
        "G": args.G,
        "n_groups": len(group_stats),
        "metrics": result,
        "group_stats": group_stats,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nSaved to {args.output}")
    else:
        out_path = os.path.join(args.results_dir, "_rho_h.json")
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
