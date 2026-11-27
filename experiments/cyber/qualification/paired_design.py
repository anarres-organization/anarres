"""Task-structured comparison of within-task binary reward variation."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from fractions import Fraction


def paired_summary(rows: list[tuple[str, int, int]], attempts: int) -> dict:
    """One matched task per row, fixed attempts per arm; independent task pairs assumed."""
    if type(attempts) is not int or attempts < 2 or len(rows) < 2:
        raise ValueError("require at least two task pairs and attempts")
    if len({r[0] for r in rows}) != len(rows) or any(not r[0] for r in rows):
        raise ValueError("duplicate or missing task identity")
    d = []
    for _, a, b in rows:
        if type(a) is not int or type(b) is not int or not (0 <= a <= attempts and 0 <= b <= attempts):
            raise ValueError("invalid task counts")
        d.append(b * (attempts - b) - a * (attempts - a))
    denominator = attempts * (attempts - 1)
    values = [v / denominator for v in d]
    # Exact sign-flip randomization under independent within-task label exchangeability.
    distribution = Counter({0: 1})
    for v in d:
        nxt = Counter()
        for score, w in distribution.items():
            nxt[score + v] += w
            nxt[score - v] += w
        distribution = nxt
    p = Fraction(
        sum(w for score, w in distribution.items() if abs(score) >= abs(sum(d))),
        2**len(d),
    )
    return {
        "task_pairs": len(rows),
        "mean_variance_difference": statistics.mean(values),
        "task_level_se": statistics.stdev(values) / math.sqrt(len(values)),
        "exchangeability_p": float(p),
        "per_task_differences": values,
    }
