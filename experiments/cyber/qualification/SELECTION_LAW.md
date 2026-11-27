# Binary-reward grouping and conditional screening

These calculations are a planning sensitivity under independent homogeneous
Bernoulli draws, not a law of training utility or usable signal per token.
The illustrative baseline .035 is hypothetical until a level-2 rerun confirms
it; the earlier G=8 pilot requested level 3. Task-level heterogeneity, shared
tasks, verifier correlations, response lengths, admission and token weights
are not identified by this model.

## Denominators and grouping

For group size G >= 2, k successes give absolute leave-one-out advantage mass
2 k (G-k)/(G-1). Under iid binary rewards with rate p, its expectation is
2 G p(1-p). This is raw mass, not useful learning signal.

The mixed-group probability is C = 1 - p^G - (1-p)^G. All-identical groups
already have zero mass. Discarding them does not change expected raw mass
per generated rollout. Conditional on retention the mass per retained rollout
is 2p(1-p)/C, whereas the expected generated cost per retained group is G/C.
If every mixed group is admitted, admitted and retained rollout counts agree;
additional admission policies and token costs are outside this calculation.

For hypothetical p=.035 and G=8, C=.247999, generated mass per rollout=.06755,
retained mass per rollout=.272380, and generated rollouts per retained group
=32.2582. This is a ratio of expectations, not a claim about finite-sample
training yield.

## Selection and global testing

The plug-in reward-variance estimate has score k(n-k)/n^2. Mirrored counts
are equal scores, so probabilities are aggregated before taking the maximum.
Maximizing the estimate over candidates induces selection bias.

Under the global null that all K independent binomial arms have the same
unknown rate, conditioning on the total successes T eliminates that nuisance
parameter. A count vector has weight product_i choose(n,k_i)/choose(Kn,T).
The exact inclusive tail of the maximum score is computed by subtracting
the probability that every score is strictly below the observed maximum.
Integer dynamic programming counts that complement. Every conditional test
has size at most alpha; hence the unconditional test does too.

Rejecting this global null does not certify a unique champion, nor does it
make a selected estimate unbiased. Failure to reject does not prove
homogeneity. The report keeps all tied indices, the raw selected estimate,
and the global p-value separate. Independent confirmation is required for
effect estimation; no ad hoc shrinkage or inversion correction is claimed.

Run:

    python selection_law.py
    python -m unittest test_selection_law

The tests enumerate every small count vector and verify conditional size
at every total, including mirrored and tied scores.
