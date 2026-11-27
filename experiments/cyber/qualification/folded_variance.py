"""Anytime test of a taskwise folded-binomial symmetry null.

The null is conditional equality of folded count distributions on each task,
with exchangeable arms. It is NOT equality of the population mean variances.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from math import comb


@lru_cache(maxsize=32768)
def wealth(wins: int, losses: int) -> Fraction:
    """Uniform-Beta mixture of fair-sign likelihood ratios; ties omitted."""
    if any(type(x) is not int or x < 0 for x in (wins, losses)):
        raise ValueError("invalid sign counts")
    n = wins + losses
    return Fraction(2**n, (n + 1) * comb(n, wins))


def folded(count: int, attempts: int) -> int:
    if (type(attempts) is not int or attempts < 2 or type(count) is not int
            or not 0 <= count <= attempts):
        raise ValueError("invalid binomial count or group size")
    return min(count, attempts - count)


@dataclass
class FoldedTest:
    """One update per complete task pair; fixed or varying group size by task.

    Group size and task selection must be predictable before outcomes. The
    folded pair must be conditionally exchangeable under the null. Unique IDs
    prevent accidental reuse, but cannot establish independence or provenance.
    """
    alpha: Fraction = Fraction(1, 20)
    wins: int = field(default=0, init=False)
    losses: int = field(default=0, init=False)
    seen: set[str] = field(default_factory=set, init=False)
    first_crossing: int | None = field(default=None, init=False)
    max_wealth: Fraction = field(default=Fraction(1), init=False)

    def __post_init__(self) -> None:
        self.alpha = Fraction(str(self.alpha))
        if not 0 < self.alpha < 1:
            raise ValueError("alpha must be in (0,1)")

    def update(self, task_id: str, a: int, b: int, attempts: int) -> dict:
        if not isinstance(task_id, str) or not task_id or task_id in self.seen:
            raise ValueError("missing or repeated task identity")
        fa, fb = folded(a, attempts), folded(b, attempts)
        self.seen.add(task_id)
        self.wins += int(fb > fa)
        self.losses += int(fb < fa)
        e = wealth(self.wins, self.losses)
        self.max_wealth = max(self.max_wealth, e)
        if self.first_crossing is None and e * self.alpha >= 1:
            self.first_crossing = len(self.seen)
        return {"tasks": len(self.seen), "wins": self.wins, "losses": self.losses,
                "ties": len(self.seen) - self.wins - self.losses, "e": e,
                "anytime_p": 1 / self.max_wealth,
                "first_crossing": self.first_crossing}


def sign_probabilities(attempts: int, p: Fraction, q: Fraction) -> tuple[Fraction, ...]:
    """Exact P(fold B>fold A), P(<), P(=) for independent binomial arms."""
    folded(0, attempts)
    p, q = Fraction(str(p)), Fraction(str(q))
    if not 0 <= p <= 1 or not 0 <= q <= 1:
        raise ValueError("invalid Bernoulli probability")
    def pmf(rate: Fraction) -> list[Fraction]:
        masses = [Fraction(0)] * (attempts // 2 + 1)
        for k in range(attempts + 1):
            masses[folded(k, attempts)] += comb(attempts, k)*rate**k*(1-rate)**(attempts-k)
        return masses
    aa, bb = pmf(p), pmf(q)
    plus = sum(x*y for i,x in enumerate(aa) for j,y in enumerate(bb) if j > i)
    minus = sum(x*y for i,x in enumerate(aa) for j,y in enumerate(bb) if j < i)
    return plus, minus, 1-plus-minus


def evaluate(schedule: list[tuple[Fraction, Fraction, Fraction]],
             alpha: Fraction = Fraction(1, 20)) -> dict:
    """Finite-state DP on sign counts for an independent, heterogeneous schedule.

    Transition masses use floats; rejection boundaries use exact rationals.
    No simulated outcomes, no data-driven nuisance calibration.
    """
    alpha = Fraction(str(alpha))
    if not schedule or not 0 < alpha < 1:
        raise ValueError("invalid schedule or alpha")
    # validate every row before propagating mass
    parsed = []
    for row in schedule:
        if len(row) != 3:
            raise ValueError("expected three sign probabilities")
        prob = tuple(Fraction(str(x)) for x in row)
        if min(prob) < 0 or sum(prob) != 1:
            raise ValueError("invalid sign distribution")
        parsed.append(tuple(map(float, prob)))
    states = {(0, 0): 1.0}
    crossed = cost = 0.0
    for t, prob in enumerate(parsed, 1):
        nxt: dict[tuple[int, int], float] = {}
        for (w,l), mass in states.items():
            for (dw,dl), chance in zip(((1,0),(0,1),(0,0)),prob,strict=True):
                if chance == 0:
                    continue
                key = w+dw, l+dl
                v = mass*chance
                if wealth(*key)*alpha >= 1:
                    crossed += v
                    cost += t*v
                else:
                    nxt[key] = nxt.get(key,0.)+v
        states = nxt
    remain = sum(states.values())
    return {"rejection_probability": crossed, "expected_tasks": cost+len(parsed)*remain,
            "mass_check": crossed+remain, "max_tasks": len(parsed)}
