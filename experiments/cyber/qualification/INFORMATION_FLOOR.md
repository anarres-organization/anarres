# The information floor

Every screen in this directory rests on one quantity: the Bernoulli divergence
between an arm and the ratio-better arm, measured on the rate the verifier
actually reports.

    D = q1 log(q1/q2) + (1 - q1) log((1 - q1)/(1 - q2))

A screen that picks one of K arms and may be wrong a fraction e of the time
needs at least

    n >= (log K + log(1/e)) / D

rollouts per arm. This is a bound: no estimator, sequential or fixed, exact or approximate,
resolves a ratio below it at that budget.

## Floor against the exact tables

Base rate 0.035, K = 10, e = 0.05:

| ratio | divergence | floor | exact screen | floor / screen |
| --- | --- | --- | --- | --- |
| 1.2 | 0.000644 | 8224 | no budget in the table | - |
| 1.5 | 0.003469 | 1527 | 1600 (0.970) | 0.95 |
| 2.3 | 0.017456 | 304 | 400 fixed, 310 sequential | 0.76, 1.02 |
| 3.0 | 0.034217 | 155 | 400 | 0.39 |

Three consequences follow from the table, and each was already published as an
independent arithmetic result.

1. **1.2 times is not a budget problem.** The floor is 8224 rollouts per arm.
   The screening table stops at a 0.590 detection probability on 1600, and no
   further spend reaches the target, because the floor sits five times above the
   largest budget in it.
2. **1.5 times sits five percent above the floor.** The exact permutation
   calculation lands at 1600 where the bound says 1527. The bound is tight
   enough to be useful and loose enough to be safe.
3. **Sequential testing reaches the floor.** The fixed 400-rollout design pays
   32 percent over the bound; the three-look design expects 310 against a floor
   of 304. The saving from stopping is not a trick, it is recovering the slack in
   the fixed design.

At 400 per arm and ten candidates the floor resolves 2.096 times, which is also
what the exact table delivers: 2.3 times is found 0.994 of the time and 1.5 times
only 0.664.

## Why the floor prices the verifier

| fault | multiplier on rollouts | reported rate |
| --- | --- | --- |
| 38 percent false negative | 1.654 | 0.0217 (too low) |
| 10 percent false positive | 2.772 | 0.1315 (too high) |

A false negative scales both rates toward the same side, so the divergence
shrinks and the floor grows by 1.65. It costs budget.

A false positive does something worse. At 0.035 it lifts the reported rate to
0.1315 while the clean rival stays at 0.0805, so the panel needs 2.77 times
the rollouts to separate them and then separates them in the wrong order. Bias
and dilution arrive together, and no budget removes either: the divergence
shrinks, and what remains points at the worse arm.

## Limits

- The bound is a union bound over K candidates plus a Chernoff exponent, so it
  can only be loose, never optimistic. Where an exact table exists it agrees
  within five percent; where the exact table is absent it is the only estimate.
- Divergence is computed on the marginal per-rollout rate, so it assumes
  independent flips across rollouts. Task-level clustering reduces effective n
  and the paired design note measures that loss separately.
- The bound says nothing about which arm is better, only whether the budget can
  tell. Direction is the verifier's business, not the budget's.
