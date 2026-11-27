# Common-verifier sensitivity of matched task reward variance

This is a fixed-panel planning analysis of raw binary reward variance. It
does not rank usable learning signal, downstream utility, or environments in
general. No CyberGym level-2 data or training result is introduced here.

## Model and estimand

For each of T fixed matched tasks, observe m >= 2 binary attempts per arm.
Task pairs are independent, but need not have identical distributions.
Within each task and arm the observed attempts are conditionally iid.
Dependence between the two arms of a task is allowed. Let p denote the
latent success probability and let q = fp + d*p, where d = 1-fn-fp.
The false-negative and false-positive probabilities fn and fp must be common
to both arms and every task, with d != 0. The measurement contract is an
assumption, not inferred from the panel.

The estimand is the equally weighted mean of the task-specific differences
p_B(1-p_B) - p_A(1-p_A). It is not the variance of a pooled success rate.
Writing h = fp-fn, algebra gives

    d^2 * p(1-p) = q(1-q) + h*q - fp*(1-fn).

The last term cancels between matched arms. If k successes are observed in
m attempts, U(k) = k*(m-k)/(m*(m-1)) is unbiased for q(1-q), and k/m is
unbiased for q. Thus the mean of

    X_i(h) = U(k_B) - U(k_A) + h*(k_B-k_A)/m

divided by d^2 is unbiased for the latent panel difference when the channel
is known. No clipping is applied to this estimate.

## Unknown but bounded common channel

Prespecify an interval [l,u] containing h. For direction only, the positive
denominator d^2 need not be known. The mean of X_i(h) is affine in h, so a
uniform sign on the interval follows from the same sign at both endpoints.

For a given endpoint, let R be the range of U(k)+h*k/m over k=0,...,m.
Then X_i lies in [-R,R]. For J distinct endpoints, Hoeffding's inequality
and a union bound give simultaneous two-sided bounds with radius

    R * sqrt(2*log(2*J/alpha)/T).

The implementation evaluates these bounds in floating point. It returns
a direction only if all endpoint intervals lie strictly on that side of zero.

A second method tests the direction with a fixed-panel e-value. For each
prespecified normalized bet b in (0,1), let

    E_b = product_i (1 + b*X_i/R).

For a nonpositive average of the task means, independence gives
E[E_b] = product_i (1+b*E[X_i]/R). AM-GM bounds this by
(1+b*mean_i E[X_i]/R)^T <= 1. A fixed mixture retains this bound.
The negative direction replaces X_i by -X_i. Each direction rejects only
when its mixture exceeds 2/alpha at every endpoint. If the claimed uniform
direction is false, at least one endpoint null is true. Markov's inequality
then controls the false direction at alpha/2; a union bound over directions
gives alpha. This is a fixed-terminal-panel test, not a sequential
supermartingale under heterogeneous task means. Do not use repeated looks.

If the channel interval comes from a separate calibration procedure with
coverage 1-delta rather than a deterministic assumption, the unconditional
error bound is at most alpha+delta by a union bound; allocating the two
error budgets is required. If channels differ across tasks or arms, or
attempts are dependent within an arm, the stated unbiasedness and guarantee
do not follow without another measurement model.

## Reproduction

    python -m unittest test_verifier_sensitivity

The implementation and eleven tests use the standard library. One test
enumerates 625 combinations of exact binomial distributions and channel
parameters using rational arithmetic, including a negatively sloped
identifiable channel. Additional tests check mirrored latent rates,
endpoint affinity, task identity, abstention, and a heterogeneous mean-null
e-value. Synthetic power is not evidence of performance on a released panel.
