"""The information floor under every screen this suite can run.

Each screen in this directory answers a different question with its own
arithmetic: the budget law says what coverage a rollout count buys, the
comparison criterion says how dense two environments are, the selection law says
what a maximum over candidates reports, and the screening budget says how often a
ratio is found. They all rest on one quantity, the Bernoulli divergence between
the two arms as the rollout actually observes them.

    D(p, p r) = q1 log(q1/q2) + (1 - q1) log((1 - q1)/(1 - q2))

with q the verifier-filtered rate. A candidate screen that has to pick one of K
arms and be wrong at most a fraction e of the time needs, at minimum,

    n >= (log K + log(1/e)) / D

rollouts per arm. This is an impossibility statement instead of a heuristic: no
estimator, sequential or fixed, exact or approximate, resolves a ratio below that
floor at that budget. It also prices the verifier exactly, because a false
negative scales D rather than the rate, so the floor scales with it.

The floor is loose by design (union bound over K plus Chernoff), and every screen
in this suite sits just above it, which is the check that matters: exact
enumeration, dynamic programming, and the bound agree to within a few percent on
the same panel.
"""

from __future__ import annotations

import math

BASELINE = 0.035


def observed_rate(p: float, false_negative: float = 0.0, false_positive: float = 0.0) -> float:
    return p * (1.0 - false_negative) + (1.0 - p) * false_positive


def divergence(
    p: float, ratio: float, false_negative: float = 0.0, false_positive: float = 0.0
) -> float:
    """Bernoulli divergence between an arm and a ratio-better arm."""

    q1 = observed_rate(p, false_negative, false_positive)
    q2 = observed_rate(min(1.0, p * ratio), false_negative, false_positive)
    if q1 == q2:
        return 0.0
    if not 0.0 < q1 < 1.0 or not 0.0 < q2 < 1.0:
        return float("inf")
    return q1 * math.log(q1 / q2) + (1.0 - q1) * math.log((1.0 - q1) / (1.0 - q2))


def floor_rollouts(
    p: float,
    ratio: float,
    candidates: int = 2,
    error: float = 0.05,
    false_negative: float = 0.0,
    false_positive: float = 0.0,
) -> float:
    """Fewest rollouts per arm any screen of this shape can get away with."""

    information = divergence(p, ratio, false_negative, false_positive)
    if information <= 0:
        return float("inf")
    return (math.log(candidates) + math.log(1.0 / error)) / information


def smallest_ratio(
    p: float,
    rollouts: float,
    candidates: int = 2,
    error: float = 0.05,
    false_negative: float = 0.0,
    false_positive: float = 0.0,
) -> float:
    """Closest ratio a screen at this budget can resolve, from the floor."""

    target = (math.log(candidates) + math.log(1.0 / error)) / rollouts
    low, high = 1.0, 1.0 / p
    for _ in range(80):
        middle = 0.5 * (low + high)
        if divergence(p, middle, false_negative, false_positive) < target:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def verifier_multiplier(p: float, ratio: float, false_negative: float) -> float:
    """How many more rollouts a false-negative rate costs at this comparison."""

    clean = divergence(p, ratio)
    noisy = divergence(p, ratio, false_negative)
    return clean / noisy if noisy > 0 else float("inf")


def corruption_multiplier(p: float, ratio: float, false_positive: float) -> float:
    """Rollout multiplier a false-positive rate costs, separate from its bias."""

    clean = divergence(p, ratio)
    dirty = divergence(p, ratio, false_positive=false_positive)
    return clean / dirty if dirty > 0 else float("inf")


def released_panel() -> dict[str, float]:
    """The floor for the published 400-rollout, 50-task panel."""

    return {
        "ratio_1_5_floor": floor_rollouts(BASELINE, 1.5, candidates=10),
        "ratio_1_5_screen": 1600.0,
        "ratio_2_3_floor": floor_rollouts(BASELINE, 2.3, candidates=10),
        "ratio_2_3_screen": 400.0,
        "ratio_2_3_sequential": 310.0,
        "resolvable_at_400": smallest_ratio(BASELINE, 400.0, candidates=10),
    }


def main() -> None:
    print("ratio  divergence  floor(n, K=10, e=.05)  screen")
    for ratio, screen in ((1.2, 1600.0), (1.5, 1600.0), (2.3, 400.0), (3.0, 400.0)):
        print(
            "%.1f   %.6f   %8.0f              %6.0f"
            % (ratio, divergence(BASELINE, ratio), floor_rollouts(BASELINE, ratio, 10), screen)
        )
    panel = released_panel()
    print()
    print(
        "at 400 per arm and ten candidates the floor resolves %.3f times, "
        "and the 2.3 times floor is %.0f rollouts"
        % (panel["resolvable_at_400"], panel["ratio_2_3_floor"])
    )
    print(
        "1.5 times: floor %.0f, exact screen %.0f, ratio %.2f"
        % (
            panel["ratio_1_5_floor"],
            panel["ratio_1_5_screen"],
            panel["ratio_1_5_floor"] / panel["ratio_1_5_screen"],
        )
    )
    print(
        "2.3 times: floor %.0f, sequential expected sample %.0f, ratio %.2f"
        % (
            panel["ratio_2_3_floor"],
            panel["ratio_2_3_sequential"],
            panel["ratio_2_3_sequential"] / panel["ratio_2_3_floor"],
        )
    )
    print(
        "a 38 percent false-negative rate multiplies the 2.3 times floor by %.3f"
        % verifier_multiplier(BASELINE, 2.3, 0.38)
    )
    print(
        "a 10 percent false-positive rate multiplies it by %.3f and reports %.4f, "
        "above the clean 2.3 times arm's 0.0805"
        % (
            corruption_multiplier(BASELINE, 2.3, 0.10),
            observed_rate(BASELINE, false_positive=0.10),
        )
    )
    if not 0.90 < panel["ratio_1_5_floor"] / panel["ratio_1_5_screen"] < 1.10:
        raise SystemExit("the 1.5 times floor and the exact screen disagree")
    if not 0.90 < panel["ratio_2_3_sequential"] / panel["ratio_2_3_floor"] < 1.10:
        raise SystemExit("the sequential design is not sitting on the floor")
    if panel["resolvable_at_400"] < 2.0:
        raise SystemExit("the floor claims a resolution the exact table does not deliver")
    if verifier_multiplier(BASELINE, 2.3, 0.38) < 1.5:
        raise SystemExit("the verifier does not cost what the lever note claims")
    if corruption_multiplier(BASELINE, 2.3, 0.10) < 2.0:
        raise SystemExit("the false-positive rate does not dilute as claimed")


if __name__ == "__main__":
    main()
