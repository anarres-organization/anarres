# Comparing two environments by signal density

A selection decision asks one question: which candidate environment gives more
training signal per generated token? Success rate is the obvious answer and the
wrong one, because signal density is proportional to p (1 - p) and that quantity
is symmetric about one half. An environment at 10 percent success and one at 90
percent carry identical density, and they are not the same environment.

This note builds the comparison that the quantity actually implies, states what
a fixed budget can distinguish, and shows that the symmetry is fragile: a
verifier with false negatives breaks it in a fixed direction.

## The null is equal density, not equal success

With p for success probability, density is phi = p (1 - p). The hypothesis a
comparison should test is equal phi across two environments, which leaves the
common value free and leaves each environment free to sit on either side of one
half. A binomial likelihood over successes s and trials t is sufficient for that
test, since tasks are independent and the group size enters only through t.

The test profiles the likelihood over the common phi and over the two side
choices, then compares it with the unconstrained maximum. One degree of freedom,
so the 95 percent point is 3.841.

## Calibration

| null pair | rejection at 3.841 |
| --- | --- |
| p = 0.035 against 0.035 | 0.060 |
| p = 0.10 against 0.90 | 0.055 |
| p = 0.25 against 0.75 | 0.080 |

The nominal five percent behaves as six to eight percent, and the excess sits at
high density where the asymptotic point is liberal. Read the instrument as a
six to eight percent test rather than claiming exact five percent coverage.

## What 400 rollouts per arm can distinguish

From a baseline at p = 0.035, which is the released CyberGym density:

| competing p | density ratio | power |
| --- | --- | --- |
| 0.020 | 0.58 | 0.235 |
| 0.050 | 1.41 | 0.170 |
| 0.080 | 2.18 | 0.790 |
| 0.120 | 3.13 | 0.995 |
| 0.200 | 4.74 | 1.000 |

Reading the table at 80 percent power, the closest distinguishable densities sit
at 0.15 times and 2.30 times the baseline. On the low side that means an
essentially silent environment, since p near 0.005 carries density 0.005. On the
high side it means a competing density of 0.078 rather than 0.034.

So an unpaired comparison at 400 rollouts per arm separates environments along
when one of them is nearly silent or more than twice as dense. Anything in
between is a coin flip dressed as a verdict, which is the same lesson the
verifier pilot reached from the other direction: at a small budget, the
resolution of the design, not the significance of the number, settles what can
be claimed.

## The symmetry is fragile under a bad verifier

A verifier with false-negative rate a reports p (1 - a), which pulls every
success probability toward zero. For a density pair that was exactly symmetric,
this pull separates them, and it always favours the higher success rate:

| p | partner | clean density | reported density | partner reported | ratio |
| --- | --- | --- | --- | --- | --- |
| 0.10 | 0.90 | 0.0900 | 0.0582 | 0.2466 | 0.24 |
| 0.25 | 0.75 | 0.1875 | 0.1310 | 0.2488 | 0.53 |
| 0.50 | 0.50 | 0.2500 | 0.2139 | 0.2139 | 1.00 |
| 0.75 | 0.25 | 0.1875 | 0.2488 | 0.1310 | 1.90 |
| 0.90 | 0.10 | 0.0900 | 0.2466 | 0.0582 | 4.24 |

At a 38 percent false-negative rate the pair at 0.10 and 0.90 reports a 4.2 times
density difference that does not exist. Two consequences follow. First, a
leaderboard built on reported density under unequal verifier quality rewards
environments where the policy already succeeds, because misreported successes
move those tasks toward one half where density peaks. Second, any comparison
must publish the verifier error rates it ran at, or its ordering is
unidentifiable.

## Design consequences

- Rank by density, and test the density null. Success-rate ordering inverts
  density ordering for any pair straddling one half.
- At 400 rollouts per arm, treat anything inside a factor of 2.3 as unresolved.
  Resolving a factor of 1.5 costs roughly four times the budget.
- Compare on shared tasks when the task sets differ, because the density of a
  panel depends on which tasks entered it. Shared tasks make the comparison
  conditional rather than a mixture.
- Report the verifier error rates with every density number, since they multiply
  signal and can reverse a ranking.

## Reproduction

```bash
cd experiments/cyber/qualification
python3 environment_ranking.py
python3 -m unittest test_environment_ranking
```

The script checks the symmetry identity, calibrates the test at three null pairs,
prints the power table, solves the minimum detectable density in both directions,
and checks that the verifier snap favours the easier task.
