# Comparing raw reward variation on shared tasks

The experimental unit for this comparison is a matched task pair.
For each task, both environments must be evaluated with the same fixed
number m >= 2 of attempts under a pinned verifier contract.
Conditional independence within a task is required to interpret
k(m-k)/[m(m-1)] as an unbiased estimate of its Bernoulli reward variance.
It follows from E[k(m-k)]=m(m-1)p(1-p). The difference is calculated
once per task, not once per attempt.

The primary descriptive summary is the average task-level difference
and its standard error across task pairs, assuming independent sampled
task pairs. For a sharp label-exchangeability null within independent
pairs, an exact sign-flip test enumerates the distribution of the
absolute sum of task differences by integer dynamic programming.
That p-value does not test arbitrary equality of population means under
asymmetric nonexchangeable distributions.

No task-probability heterogeneity estimate is inferred by treating k/m
from a single noisy group as a true rate. No claimed gain or minimum
detectable ratio is derived from the prior aggregate 37/12/1 count
vector. Paired covariance and a power design need independent paired
task measurements. Pairing acts on the variance of a difference;
it does not justify dividing a ratio by a standard-error gain.

The implementation accepts rows (task_id, successes_A, successes_B)
and rejects duplicated task identities and invalid counts. The
sign-flip distribution is verified against exhaustive enumeration on
synthetic task pairs. No matched level-2 panel is claimed here.

For a separate common-verifier measurement contract, see
[Common-verifier sensitivity](VERIFIER_SENSITIVITY.md) for the unbiased
latent variance contrast and fixed-panel directional tests. These methods
require independent task pairs and a known or bounded common channel.
