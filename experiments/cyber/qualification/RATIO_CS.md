# Marginal ratio confidence sequences

This companion to TASK_RACING.md estimates the normalized raw yield
r = E[M]/E[C] for each arm, with bounded normalized mass M in [0,1]
and positive normalized cost C in (0,1]. Use the same frozen matched-task
sampling contract. Within a task the two arms and mass/cost can be dependent;
across task pairs assume iid sampling. No actual CyberGym runs are added.

For any candidate r >= 0, the score (M-rC)/max(1,r) lies in [-1,1].
At the true ratio its conditional expectation is zero. For either sign
and any fixed betting fraction in (0,1), the product of 1 plus the signed
fraction times the score is a nonnegative martingale. A fixed mixture
inherits that property. Ville's inequality at the true ratio, with alpha/4
for each of two arms and two directions, controls simultaneous coverage
at all task-pair stopping times. Independence between arms is not needed.

For each realized observation the score decreases monotonically with r:
below 1 it is M-rC; above 1 it is M/r-C. Consequently positive and negative
evidence are monotone in opposite directions, permitting one-dimensional
bisection without a parameter grid or a multiplicity correction over
candidate ratios. Report outer numerical root endpoints; float64 arithmetic
is not a directed-rounding proof. If an upper endpoint cannot be bracketed,
return infinity rather than a finite claim. Disjoint intervals establish
ordering; nonseparation does not establish equality.

Convert normalized ratio bounds to raw mass per million generated tokens
by multiplying by 1e6 / cap, under the common frozen cap. This does not
estimate admitted signal, effective coverage, or training utility.

Five local unit tests cover directional separation, equal ratios, empty
data, monotonicity, and atomic input rejection. Full repository make check
has not been run. The marginal intervals can be conservative compared with
a paired contrast; no efficiency superiority is claimed. Inversion costs
O(number of observed tasks * number of bets * bisection iterations) per
look. This is an exploratory companion, not a modification of a frozen
prospective protocol.
