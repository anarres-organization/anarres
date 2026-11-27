# Conditional fixed-budget screening

This is a one-leader, identical-follower, independent homogeneous Bernoulli
planning model, not a measured law of the released Cyber task panel.
The baseline .035 is an illustrative parameter until a level-2 rerun verifies
it. The earlier G=8 pilot requested level 3. Shared-task and verifier
dependence are excluded. The criterion is raw binary reward variance p(1-p),
not usable signal per token or downstream RL utility.

## Exact finite-count probability with random ties

For n draws per arm, aggregate the binomial probability at every integer
score k(n-k), including mirrored counts. Conditional on the leader score,
let f be the follower probability of that score and B its strictly lower
score probability. With m=K-1 followers, the leader's probability of being
selected is sum_j choose(m,j) f^j B^(m-j)/(j+1), since tied winners share
credit uniformly. Averaging over the leader score gives the selection
probability by finite enumeration (floating-point masses).

At p=.035 and K=10, the leader rates are derived from the specified
variance ratio, not rounded lookup constants:

| Variance ratio | Leader rate | PCS at 400 | PCS at 1600 |
| --- | --- | --- | --- |
| 1.2 | .042321 | .275356 | .522636 |
| 1.5 | .053528 | .625978 | .966322 |
| 2.3 | .084889 | .991544 | 1.000000 (rounded) |

The CLI reports the first tested grid point meeting its target, not a
globally minimal sample size. The grid is 25, 50, 100, 200, 400, 700, 1000,
1600, 2400, 3200, 4800, 6400, and 10000 draws per arm. It returns no budget
when no tested point reaches the target.

## Two-stage simulation

A fixed total budget funds a pilot on every arm, followed by equal
additional draws for retained arms. Uniform tie-breaking applies at both
stages. The specified baseline is used in both stages. Results include
the actual spend, the replicate count and a Wilson interval for Monte Carlo
uncertainty. This is a simulation of the declared model, not a claim that
racing must beat uniform allocation or that a simulated gain transfers to
clustered task data.

Run:

    python screen.py plan --ratio 1.2 --candidates 10 --baseline .035 --target .9
    python screen.py report --counts 34,14,12,16,11,15,13,9,17,10
    python -m unittest test_selection_law test_screening_budget test_screen

All scripts use the Python standard library. They validate input counts,
ratio feasibility, targets, and tied or mirrored rates. Tests compare
the selection probability to exhaustive small-case enumeration.
