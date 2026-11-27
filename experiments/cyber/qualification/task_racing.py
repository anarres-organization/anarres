"""Task-cluster sequential inference for binary reward variation and raw token yield.

No assumption that individual rollouts are independent is needed for raw yield.
Tasks (or independent prespecified clusters) must be iid draws from the target
population, with a fixed common verifier, group size and token cap. No claims
about downstream training utility or a validated CyberGym baseline are made.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Group:
    successes: int
    attempts: int
    output_tokens: int

    def validate(self, g, cap):
        if (type(g) is not int or g < 2 or type(cap) is not int or cap < 1
                or type(self.attempts) is not int or self.attempts != g
                or type(self.successes) is not int or not 0 <= self.successes <= g
                or type(self.output_tokens) is not int
                or not 1 <= self.output_tokens <= g * cap):
            raise ValueError('invalid group or prespecified token cap exceeded')

    def variation(self):
        k, g = self.successes, self.attempts
        return k * (g-k) / (g*(g-1))

    def normalized(self, cap):
        return 2*self.variation(), self.output_tokens/(self.attempts*cap)


@dataclass(frozen=True)
class TaskPair:
    task_id: str
    a: Group
    b: Group


class MixtureE:
    """Two directional e-processes; two-sided anytime level alpha by Ville + union."""
    def __init__(self, alpha=0.05, bets=(.0625,.125,.25,.5,.75,.95)):
        if not 0 < alpha < 1 or not bets or any(not 0 < b < 1 for b in bets):
            raise ValueError('invalid alpha or bets')
        self.alpha, self.bets = alpha, tuple(bets)
        self.logs = [[0.0]*len(bets) for _ in range(2)]
        self.n, self.first_crossing = 0, None

    def update(self, x):
        if not math.isfinite(x) or not -1 <= x <= 1:
            raise ValueError('score outside [-1,1]')
        self.n += 1
        log_e = []
        for sign, row in zip((1,-1), self.logs):
            for i, b in enumerate(self.bets):
                row[i] += math.log1p(sign*b*x)
            m = max(row)
            log_e.append(m + math.log(sum(math.exp(v-m) for v in row)/len(row)))
        if self.first_crossing is None:
            hits = [s for s, v in zip(('b_greater','a_greater'),log_e)
                    if v >= math.log(2/self.alpha)]
            if hits:
                self.first_crossing = (self.n, hits[0] if len(hits)==1 else 'ambiguous')
        return {'n': self.n, 'log_e_b': log_e[0], 'log_e_a': log_e[1],
                'first_crossing': self.first_crossing}


class TaskRacing:
    """Observe complete matched task pairs in frozen order; no skipping or reuse.

    Joint family error is controlled by dividing alpha across the two endpoints.
    Raw yield uses disjoint blocks of two independent task pairs, removing the
    within-task mass/length product bias. Variation uses all task pairs.
    """
    def __init__(self, g, cap, alpha=.05):
        Group(0,g,1).validate(g,cap)
        if not 0 < alpha < 1:
            raise ValueError('invalid alpha')
        self.g, self.cap = g, cap
        self.variation = MixtureE(alpha/2)
        self.yield_test = MixtureE(alpha/2)
        self.seen, self.pending = set(), None
        self.mass, self.length = [0.,0.], [0.,0.]
        self.last_yield = None

    def update(self, pair):
        if not isinstance(pair.task_id,str) or not pair.task_id or pair.task_id in self.seen:
            raise ValueError('missing or duplicate independent task identity')
        for group in (pair.a,pair.b):
            group.validate(self.g,self.cap)
        self.seen.add(pair.task_id)
        vals = tuple(group.normalized(self.cap) for group in (pair.a,pair.b))
        for i,(m,l) in enumerate(vals):
            self.mass[i] += m
            self.length[i] += l
        v = self.variation.update(vals[1][0]-vals[0][0])
        if self.pending is None:
            self.pending = vals
        else:
            (ma,la),(mb,lb) = self.pending
            (na,ka),(nb,kb) = vals
            score = ((mb*ka-ma*kb)+(nb*la-na*lb))/2
            self.last_yield = self.yield_test.update(score)
            self.pending = None
        return {'task_pairs':len(self.seen), 'variation':v, 'raw_yield':self.last_yield,
                'rho_raw_per_million': [1e6*m/(self.cap*l) for m,l in zip(self.mass,self.length)]}
