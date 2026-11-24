# Comparing on shared tasks

An unpaired comparison measures each environment on its own task set, and the
task set enters the measurement. Two panels drawn from the same task pool inherit
different mixes, so the difference between reported densities carries the mix
variance of both panels on top of each panel's binomial variance.

This note decomposes that variance at the published panel, reports the factor a
paired design recovers, and states the limits of the estimate.

## Decomposition

The panel proxy is the published k vector: 37 tasks at 0 of 8, 12 at 1 of 8, and
1 at 2 of 8, with p taken as k / G. The proxy reproduces 24.0 total advantage
mass against the released 27.43, close enough for an order statement and far
enough to mark that this is not a forecast.

At G = 8 the binomial component of the panel's total mass has standard deviation
5.17. The task-mix component, which is the standard deviation of a resampled
50-task panel's expected mass, has 5.91. The mix term is the larger of the two,
at 1.14 times the binomial term.

## What pairing recovers

| design | standard deviation of the difference |
| --- | --- |
| paired, shared tasks | 7.32 |
| unpaired, separate panels | 11.11 |

The gain is 1.52. A paired comparison removes the panel-mix term because each task
contributes its own difference, so the comparison becomes a statement about that
task set rather than about two mixtures.

Carrying the factor into the previous note's minimum detectable density ratio,
an unpaired ratio of 2.30 becomes 1.52 at the same total budget. Anything the
unpaired design can only resolve above 1.52 moves into reach.

## Consequences

- Run both environments on the same tasks. The public protocols in this
  directory already pin a panel, so the marginal cost is scheduling, not task
  curation.
- When shared tasks are impossible, report the panel overlap. A comparison across
  disjoint panels at 400 rollouts per arm cannot separate densities closer than
  2.3 times, and neither can it separate a 1.5 times gap that pairing would
  resolve.
- The estimate above uses mean group mass per task from k / G. A task at 0 of 8
  is treated as p = 0, which understates the mix term for tasks whose true
  probability is small but nonzero, so read the gain as a lower bound.
