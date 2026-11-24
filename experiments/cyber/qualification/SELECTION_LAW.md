# Two laws: grouping cannot buy signal, selection inflates it

Screening programmes optimise in two places: how to build a group of rollouts,
and how to pick the best environment from a set. Both have exact answers, and
both answers are uncomfortable.

## Grouping

For a group of G rollouts drawn uniformly at success rate p, expected advantage
mass is 2Gp(1 - p), and that identity is exact for every G. Mass per rollout is
therefore 2p(1 - p) for every G, which is also the largest per-token value any
group can carry: the per-rollout share of a group with k successes is
2k(G - k)/(G(G - 1)), which is at most the density of the observed rate and
cannot exceed one half.

A common implementation habit is to discard groups whose rollouts all agree,
because their advantage is zero. That removes zero mass and removes exactly the
coverage it filters: at p = 0.035 and G = 8, coverage is 0.2480, so each retained
group costs 4.03 times what it should. Mass per token falls from 0.0675 to
0.0168, a 75 percent loss. The zero-mass groups were never the problem; the
rollouts spent on them are the price of the coverage that makes the other groups
possible.

There is no grouping trick that raises 2p(1 - p) at fixed p. The only levers are
p itself, which is the environment, and the verifier, which decides what counts
as p.

## Selection

At a fixed budget, choosing the best of K environments reports a density above
the truth even when all K are identical. The expectation is exact: at p = 0.035
and 400 rollouts per arm the panel maximum is 0.0438 for K = 5, 0.0472 for K = 10,
and 0.0503 for K = 20, which is 1.30, 1.40, and 1.49 times the true density.

A blind correction makes this worse, not better. Inverting the maximum assumes a
homogeneous panel, and on a genuine leader it shrinks the answer to 0.79 times
the truth. The bias and the champion are the same observation seen from two
directions, so the report needs a regime test rather than a correction.

### A two-regime rule

Take the pooled rate of all K arms as the homogeneous baseline and compute the
exact tail probability of a winner this large:

    p_value = 1 - S(pooled, observed winner)^K

If the value is at or below 0.05 the champion is certified and the raw estimate
stands, because selection bias at that separation is under one percent. Otherwise
report the panel as homogeneous, at the density whose expected maximum equals the
observation.

### Validation

Five hundred seeded panels per scenario, 400 rollouts per arm.

| scenario | mean reported | ratio to truth | claim rate |
| --- | --- | --- | --- |
| all ten equal | 0.0357 | 1.06 | 5.0% |
| one leader, 2.3 times | 0.0776 | 1.00 | 94.2% |
| one leader, 1.5 times | 0.0439 | 0.87 | 22.4% |

The null panel's inflation disappears and its claim rate sits at the size. A
certified leader is reported without inflation. A leader below what the budget
can resolve is mostly reported as a homogeneous panel, which is the honest
answer at that budget rather than a failure of the rule.

### What this bounds

Among ten candidates at 400 rollouts per arm, a 2.3 times difference can be
certified. A 1.5 times difference is certified 22 percent of the time and a 1.2
times difference 6 percent of the time. Reaching the 1.5 times case needs roughly
four times the budget, the same factor the comparison note derives for density
resolution, so the two routes agree.

## Consequences

- Report the panel, not the champion, unless the tail test clears. A ranked list
  from ten candidates at 400 rollouts per arm is a ranking of noise with a
  built-in 40 percent inflation at the top.
- Do not filter zero-advantage groups. The tax is 1 over coverage, which is four
  times at the published density.
- Spend budget on reachable separations. A screening round that aims at 1.5 times
  differences needs the budget of a 1.5 times test, not the budget of a 2.3
  times one.
