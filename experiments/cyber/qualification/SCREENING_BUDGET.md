# What a screening budget buys

A screening round puts several candidate environments on the same panel and
keeps the one with the largest measured density. Two decisions are buried in
that sentence: how much per arm, and how to split the budget between a first
pass and a deeper pass.

One leader against identical followers makes the answer exact, because the arms
are independent and the leader only has to exceed the largest of the followers:

    PCS = sum over k of f_leader(k) * S(k)^(K - 1)

## How much per arm

Identification probability at 400 rollouts per arm, exact:

| ratio | K = 6 | K = 10 |
| --- | --- | --- |
| 2.3 | 0.996 | 0.994 |
| 1.5 | 0.748 | 0.664 |
| 1.2 | 0.440 | 0.334 |

A 2.3 times leader is certified at the published budget. A 1.5 times leader is
certified two times in three, and reaching 0.970 needs 1600 rollouts per arm,
four times the budget. A 1.2 times leader reaches only 0.590 even at four times
the budget, so a screening round aimed at that separation is not a matter of
spending more; it needs a different measurement.

## How to split it

Half the budget as a pilot on every arm, then the rest on the top four:

| ratio | K = 6, even | K = 6, racing | K = 10, even | K = 10, racing |
| --- | --- | --- | --- | --- |
| 2.3 | 1.000 | 1.000 | 0.994 | 0.995 |
| 1.5 | 0.858 | 0.897 | 0.664 | 0.742 |

At the screening margin the reallocation is worth 7.8 points on ten candidates,
which is what an even split with 536 rollouts per arm would buy, a third more
budget. Below and above that margin it is worth nothing, because the outcome is
already decided either way. Reallocation moves budget, it does not create
information.

## Limits

- Seeded panels, 4000 replicates per cell, so each reported probability carries
  a Monte Carlo error near 0.01. The even-split column is exact and the
  single-round check reproduces the exact answer to 0.04.
- One leader against identical followers. A panel with several near-equal
  leaders behaves differently, and the ranking there is the noise ranking the
  selection note warns about.
- The racing configuration is fixed at half the budget and the top four, chosen
  from a small grid. It is a defensible default, not a proven optimum.
