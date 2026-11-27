"""Fixed-panel sensitivity of paired binary reward variance to a common verifier."""
from __future__ import annotations

import math
from fractions import Fraction


def _fraction(value: int | float | str | Fraction) -> Fraction:
    return Fraction(str(value))


def _score(k: int, m: int, h: Fraction) -> Fraction:
    return Fraction(k * (m - k), m * (m - 1)) + h * Fraction(k, m)


def corrected_difference(rows: list[tuple[str, int, int]], attempts: int,
                         fn: float, fp: float) -> Fraction:
    """Unbiased mean B-minus-A latent variance under one known common channel."""
    f, g = _fraction(fn), _fraction(fp)
    if not (0 <= f <= 1 and 0 <= g <= 1) or f + g == 1:
        raise ValueError("invalid or nonidentifiable channel")
    h = g - f
    return _mean_score_difference(rows, attempts, h) / (1 - f - g) ** 2


def _mean_score_difference(rows: list[tuple[str, int, int]], attempts: int,
                           h: Fraction) -> Fraction:
    if type(attempts) is not int or attempts < 2 or not rows:
        raise ValueError("require nonempty matched tasks and at least two attempts")
    seen = set()
    total = Fraction(0)
    for task_id, a, b in rows:
        if not isinstance(task_id, str) or not task_id or task_id in seen:
            raise ValueError("duplicate or missing task identity")
        if any(type(k) is not int or not 0 <= k <= attempts for k in (a, b)):
            raise ValueError("invalid task counts")
        seen.add(task_id)
        total += _score(b, attempts, h) - _score(a, attempts, h)
    return total / len(rows)


def sensitivity(rows: list[tuple[str, int, int]], attempts: int,
                asymmetry: tuple[float, float], alpha: float = 0.05) -> dict:
    """Simultaneous fixed-panel Hoeffding bounds for common FP-FN in an interval.

    Independent task pairs; conditionally iid observed attempts within each arm.
    Cross-arm dependence within a task is allowed. Assume a prespecified interval
    contains the common channel asymmetry and exclude FN+FP=1. The sign of the
    latent difference is the sign of its numerator; no magnitude is certified.
    Floating-point evaluation of a theoretical concentration bound, not interval
    arithmetic. No repeated-look guarantee or overall utility interpretation.
    """
    lo, hi = map(_fraction, asymmetry)
    if not -1 <= lo <= hi <= 1 or not 0 < alpha < 1:
        raise ValueError("invalid asymmetry interval or alpha")
    bounds = []
    endpoints = sorted({lo, hi})
    for h in endpoints:
        center = _mean_score_difference(rows, attempts, h)
        scores = [_score(k, attempts, h) for k in range(attempts + 1)]
        width = float(max(scores) - min(scores))
        radius = width * math.sqrt(2 * math.log(2 * len(endpoints) / alpha) / len(rows))
        bounds.append((float(h), float(center), float(center) - radius, float(center) + radius))
    lower = min(x[2] for x in bounds)
    upper = max(x[3] for x in bounds)
    status = "B_greater" if lower > 0 else "A_greater" if upper < 0 else "abstain"
    return {"task_pairs": len(rows), "alpha": alpha, "endpoint_bounds": bounds,
            "numerator_lower": lower, "numerator_upper": upper, "status": status}


# Fixed before data; mixing preserves the e-value bound.
BET_FRACTIONS = tuple(Fraction(1, 2**i) for i in range(1, 12)) + (Fraction(19, 20),)


def _log_mixture(values: list[Fraction], width: Fraction, direction: int) -> float:
    if width == 0:
        return 0.0
    x = [float(direction*v/width) for v in values]
    logs = [math.fsum(math.log1p(float(b)*v) for v in x) for b in BET_FRACTIONS]
    peak = max(logs)
    return peak + math.log(math.fsum(math.exp(v-peak) for v in logs)/len(logs))


def fixed_panel_test(rows: list[tuple[str, int, int]], attempts: int,
                     asymmetry: tuple[float, float], alpha: float = .05) -> dict:
    """Directional e-tests valid for independent non-identical fixed tasks.

    For the positive direction, E prod(1+lambda X_i) <= 1 if the mean
    of the task-specific means is nonpositive, by independence and AM-GM.
    For a robust claim require both endpoint tests; at least one endpoint
    null is true if the claimed direction is not uniform. Each direction
    spends alpha/2. This is a terminal test, not an anytime-valid process.
    """
    lo, hi = map(_fraction, asymmetry)
    if not -1 <= lo <= hi <= 1 or not 0 < alpha < 1:
        raise ValueError("invalid asymmetry interval or alpha")
    evidence = []
    for h in sorted({lo,hi}):
        _mean_score_difference(rows, attempts, h)
        scores = [_score(k, attempts, h) for k in range(attempts+1)]
        width = max(scores)-min(scores)
        values = [scores[b]-scores[a] for _,a,b in rows]
        evidence.append((float(h), _log_mixture(values,width,1), _log_mixture(values,width,-1)))
    threshold = math.log(2/alpha)
    positive = all(x[1] >= threshold for x in evidence)
    negative = all(x[2] >= threshold for x in evidence)
    return {"task_pairs":len(rows), "alpha":alpha, "endpoint_log_e":evidence,
            "log_threshold":threshold, "status":"B_greater" if positive and not negative else
            "A_greater" if negative and not positive else "abstain"}
