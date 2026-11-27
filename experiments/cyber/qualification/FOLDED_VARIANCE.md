# Folded-count sequential test for heterogeneous matched tasks

This is a separate diagnostic for a stronger null than equality of mean
raw reward variation. No benchmark outcomes or new training claims are used.

For a task with m independent binary attempts per arm and success rates
p and q, define F(k)=min(k,m-k). Under p(1-p)=q(1-q), either q=p or q=1-p;
F has the same distribution in both arms. Conditional exchangeability of
the folded pair implies that its non-tied signs are fair, even when the
baseline rate, group size, and choice of null branch vary predictably by task.
Cross-arm independence is sufficient but not necessary for exchangeability.

If W and L count positive and negative signs, respectively, integrate the
fair-sign likelihood ratio against a uniform Beta(1,1) mixing distribution:

    E(W,L) = 2^(W+L) / [(W+L+1) choose(W+L,W)].

A tie leaves wealth unchanged. On a non-tie the sign is fair, and the
average of E(W+1,L) and E(W,L+1) equals E(W,L) exactly. Thus the process
is a nonnegative martingale under the conditional symmetry null, and Ville's
inequality controls ever crossing 1/alpha at level alpha. The inverse running
maximum is an anytime-valid p-value. Both directions share this single
mixture, not two independent tests. Exact integer/rational thresholds avoid
rounding errors in the decision. The test does not certify a direction or
magnitude, and non-rejection does not prove equality.

Folded-binomial stochastic ordering was established by Porzio and Ragozini
(2009), [On the stochastic ordering of folded binomials](https://www.sciencedirect.com/science/article/abs/pii/S0167715209000558).
The betting construction is classical. This contribution is their scoped
combination, exact implementation and validation, not a new general theorem.

## Synthetic finite-state evaluation

The following four-task schedules repeat 20 times (80 tasks maximum).
Triples below are (attempts,p,q); probabilities are exact fractions in the
model, with floating-point propagation of DP masses.

| Scenario | Rejection probability | Expected tasks |
| --- | ---: | ---: |
| Null: (8,.05,.95), (6,.4,.4), (4,.5,.5), (3,0,1) | .02023760 | 79.06197 |
| Strong alternative: (8,.05,.5), (6,.1,.4), (4,0,.5), (3,.05,.4) | 1.00000000 (rounded) | 10.73565 |
| Modest alternative: (8,.1,.2), (6,.2,.3), (4,.1,.2), (3,.2,.3) | .64302565 | 55.88196 |
| All ties: (8,0,1) throughout | 0 | 80 |

These are conditional planning examples, not empirical power or evidence of
performance on an actual task panel. The modest alternative shows the cost
of discarding sign magnitude. The strong alternative is deliberately easy.

The nine local tests include 630 exact null-branch checks, 1,331 direction
checks, 496 martingale identities and all 6,561 paths of a short heterogeneous
schedule. Run `python -m unittest test_folded_variance`. The full repository
`make check` was not run in the isolated environment.

## Boundary

Equal mean variance is not sufficient: with group sizes 2 and 8, opposite
variance differences +1/4 and -1/4 give an expected sum of signs -63/128.
This rules out interpreting the folded test as a mean-variance comparison.
A taskwise symmetric null also does not establish equivalent token yield,
verifier validity, or downstream training utility. No assumption about
independence can be certified from task IDs alone. Use the separate task-level
mean analysis for its own estimand. Do not access prospective outcomes or
change a frozen evaluation contract to apply this exploratory diagnostic.
