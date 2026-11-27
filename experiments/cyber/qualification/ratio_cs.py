"""Anytime marginal ratio bounds for matched iid task clusters.

A one-task-per-update alternative to cross-product testing. Bounds apply to
raw mass per generated token, not admitted signal or downstream utility.
"""

import math


class RatioCS:
    """Invert four one-sided fixed-mixture e-processes (two arms, two tails)."""

    def __init__(self, alpha=0.05, bets=(0.125, 0.25, 0.5, 0.75, 0.95)):
        if not 0 < alpha < 1 or not bets or any(not 0 < b < 1 for b in bets):
            raise ValueError("invalid alpha or bets")
        self.bets = tuple(bets)
        self.log_threshold = math.log(4 / alpha)
        self.rows = [[], []]

    def update(self, a, b):
        """Each pair consists of (normalized raw mass, normalized cost)."""
        for m, c in (a, b):
            if not 0 <= m <= 1 or not 0 < c <= 1:
                raise ValueError("invalid normalized pair")
        self.rows[0].append(tuple(a))
        self.rows[1].append(tuple(b))

    def log_e(self, arm, ratio, sign):
        if (
            arm not in (0, 1)
            or not math.isfinite(ratio)
            or ratio < 0
            or sign not in (-1, 1)
        ):
            raise ValueError("invalid inversion parameter")
        scale = max(1.0, ratio)
        vals = [
            sum(
                math.log1p(sign * bet * (m / scale - (ratio / scale) * c))
                for m, c in self.rows[arm]
            )
            for bet in self.bets
        ]
        top = max(vals)
        return top + math.log(sum(math.exp(v - top) for v in vals) / len(vals))

    def interval(self, arm):
        """Numerically invert monotone evidence using outer bisection endpoints."""
        if not self.rows[arm]:
            return 0.0, math.inf
        if self.log_e(arm, 0.0, 1) < self.log_threshold:
            lower = 0.0
        else:
            lo, hi = 0.0, 1.0
            while self.log_e(arm, hi, 1) >= self.log_threshold:
                hi *= 2
                if hi > 1e12:
                    return 0.0, math.inf
            for _ in range(40):
                mid = (lo + hi) / 2
                if self.log_e(arm, mid, 1) >= self.log_threshold:
                    lo = mid
                else:
                    hi = mid
            lower = lo
        lo, hi = 0.0, 1.0
        while self.log_e(arm, hi, -1) < self.log_threshold:
            hi *= 2
            if hi > 1e12:
                return lower, math.inf
        for _ in range(40):
            mid = (lo + hi) / 2
            if self.log_e(arm, mid, -1) >= self.log_threshold:
                hi = mid
            else:
                lo = mid
        return lower, hi

    def decision(self):
        a, b = self.interval(0), self.interval(1)
        direction = None
        if a[0] <= a[1] and b[0] <= b[1]:
            if a[1] < b[0]:
                direction = "b_greater"
            elif b[1] < a[0]:
                direction = "a_greater"
        return {"a": a, "b": b, "direction": direction, "pairs": len(self.rows[0])}
