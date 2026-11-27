# Comparing raw binary reward variance

This is a conditional homogeneous independent Bernoulli model. It does not
rank training environments by usable signal per generated token, admission,
response lengths, effective coverage or downstream learning utility.
The earlier .035 G=8 success rate is not a validated level-2 baseline; the
example rates are illustrative. Attempts nested within tasks require a
task-structured analysis instead of the pooled model.

## Composite null and exact finite-count test

For independent Bernoulli rewards with probabilities p and q, the variance
is p(1-p). Equality of the variances is equivalent to the union of two
null branches: p=q or p=1-q. The branches intersect at one half; a
chi-square likelihood-ratio calibration is not assumed.

For the first branch, condition on the total successes in two independent
binomial counts. The conditional hypergeometric mass is proportional to
choose(n_A,a) choose(n_B,T-a). Use the two-sided inclusive probability-
ordered tail, evaluated with integer weights. For the mirror branch,
replace B successes by its failure count and apply the same test.
The union-null p-value is the maximum of the two valid p-values. Reject
only when both branches reject. At every parameter in the union null,
at least one branch is true; the rejection event is a subset of that
branch's rejection event. Thus the test controls size uniformly at alpha
under its stated iid model, with no fitted nuisance-rate calibration.

Finite-count power at a fixed design is enumerated over both binomial
count distributions. These calculations use floating-point probabilities
for power but exact rational p-values for rejection. No sharp minimum
detectable ratio is inferred from a small Monte Carlo sample.

A common known verifier channel maps p to p(1-FN)+(1-p)FP. The mapping
is invertible when FN+FP differs from one. It does not preserve reward
variance in general. Channel uncertainty or arm-dependent corruption
requires separate measurement evidence; the code does not claim to infer
true variance from an unknown verifier.

Run python environment_ranking.py or python -m unittest test_environment_ranking.
All code uses the standard library. Tests enumerate small conditional
tables and check both composite-null branches on a grid including
boundaries and one half.
