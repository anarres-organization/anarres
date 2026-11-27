# Fixed-budget bounds for a homogeneous Bernoulli screen

This is a conditional planning model, not a bound on training-environment
utility. In particular, 0.035 is a hypothetical baseline: the earlier G=8
pilot requested level3, and a level2 rerun has not established this rate.
Attempts nested within a task need not be independent. The following results
apply only to the explicitly independent, homogeneous model.

## Model and two different bounds

Exactly one of K arms has Bernoulli rate q > p; all other arms have rate p.
Every arm receives n independent draws. A procedure must identify the leader
with probability at least 1-e for each possible leader identity. Costs below
are fixed per-arm counts; the total cost is K n.

For two instances that swap the identity of the leader, the divergence of
the complete observation distributions is n [D(p||q) + D(q||p)].
Data processing through the event "select the first leader" gives

    n [D(p||q) + D(q||p)] >= kl(1-e || e).

This is a necessary bound for the specified allocation and alternative class,
not a bound for arbitrary sequential or unequal-allocation procedures.
See Kaufmann, Cappé and Garivier (2016), On the Complexity of Best-Arm
Identification in Multi-Armed Bandit Models, Lemma 1, JMLR 17(1).
https://jmlr.org/papers/v17/14-377.html

For max-count selection, the probability a particular follower equals or
exceeds the leader is bounded by a Chernoff calculation on the difference
of two independent binomial counts. Minimizing its moment-generating
function gives A^(2n), where A = sqrt(p q) + sqrt((1-p)(1-q)).
A union bound over K-1 followers gives the sufficient condition

    n >= log((K-1)/e) / [-2 log A].

Ties are counted against the leader in this sufficient bound. The actual
selection probability with uniform random ties is computed by enumerating
the leader count and the number of tied followers. No approximation to
the necessary bound is presented as a universal impossibility result.

## Conditional numerical results

For p=.035, K=10, e=.05, and q=ratio*p:

| ratio | necessary n | sufficient n | max-count PCS at n=400 |
| --- | --- | --- | --- |
| 1.2 | 1997 | 15660 | 0.265953 |
| 1.5 | 358 | 2809 | 0.595725 |
| 2.3 | 67 | 524 | 0.983437 |
| 3.0 | 33 | 258 | 0.999751 |

The two-arm sequential study and the density-based screen are different
estimands and allocations. Their budgets are not compared against this table.
A finite sufficient budget exists for every distinct p and q under this model.

## Common verifier channel

Both rates are transformed by q_obs = q*(1-FN)+(1-q)*FP.
For true p=.035 and q=.0805:

| FN | FP | observed follower | observed leader | necessary n | sufficient n |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | .035 | .0805 | 67 | 524 |
| .38 | 0 | .0217 | .04991 | 109 | 865 |
| 0 | .10 | .1315 | .17245 | 203 | 1589 |

A common channel with FN+FP < 1 preserves ordering, but contracts
information. Comparing a corrupted arm with a clean arm is a separate
measurement design, not this calculation.

Run the model and small-case enumeration tests in this directory:

    python information_floor.py
    python -m unittest test_information_floor

Only the Python standard library is required. The binomial enumeration
uses floating-point probabilities, not exact rational arithmetic. It is
checked against exhaustive small cases, boundary cases, and the reviewers'
counterexamples. These are planning calculations, not evidence of a
level2 rerun or a training intervention effect.
