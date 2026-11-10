# Legal policy-response measurement v1

- Stability: development
- Revision: `v1-development`
- Scope: candidate legal-task mixtures measured under one frozen starting policy

This convention transports the policy-response concepts used by the legal
environment-selection program. It does not prescribe one mixture rule or imply
that a larger value is always better. Native evidence retains task-generator
identity, legal domain, verifier behavior, interaction depth, and missingness.

## `readiness_fraction`

Fraction of measured attempts satisfying the study's declared readiness rule.
Unit: `fraction`. Direction is contextual because an environment can be too easy
to provide useful corrections or too difficult to yield usable responses.

## `eligible_response_fraction`

Fraction of responses eligible under the study's fixed learning or scoring
contract. Unit: `fraction`. The native record defines exclusions and preserves
infrastructure failure separately.

## `reward_discrimination`

Study-defined separation in valid verifier outcomes under the starting policy.
Unit: `normalized_score`. The estimator and reward contract must be explicit in
the profile and native evidence.

## `binary_reward_entropy_nats`

Candidate-weighted mean binary entropy of all-turn episode completion within
each component task generator. Unit: `nats`. The SylloGym producer estimates
each component from 256 independent starting-policy attempts before applying a
frozen mixture. Direction is contextual because maximal entropy identifies
response variation rather than downstream utility by itself.

## `mean_token_cost`

Arithmetic mean charged model tokens per valid measured response. Unit:
`model_tokens_per_response`.

## `truncation_rate`

Fraction of measured responses externally truncated by the interaction limit.
Unit: `fraction`. Truncation remains distinct from an ordinary incorrect legal
answer.

## `format_valid_fraction`

Candidate-weighted fraction of attempts that satisfy the fixed response-format
contract. Unit: `fraction`. Invalid formatting remains distinct from a valid but
legally incorrect response.

## `effective_task_coverage`

Normalized inverse-Simpson effective count of the candidate's task-generator
weights. Unit: `fraction`, with one denoting uniform mass across the measured
support. Direction is contextual because broader coverage is a property of the
mixture rather than a validated utility rule.

## `measurement_reliability`

Study-defined agreement across independent measurement views. Unit:
`normalized_score`. The native record specifies the agreement statistic.

## `missingness_rate`

Fraction of expected policy-response measurements absent after infrastructure
and verifier accounting. Unit: `fraction`. Missing observations are not
converted into unsuccessful outcomes.

## Regression-risk boundary

The LAB regression-risk study predicts which evaluation tasks may decline after
continued training from task and workflow structure. That task-level predictor
is a separate scientific object, not a coordinate of one candidate training
environment. It remains a linked evaluation record unless a future experiment
defines an explicit environment-level aggregation and validates its use.

## SylloGym producer

The SylloGym adapter projects three prospectively compared mixtures from one
outcome-blind component measurement. Each of fourteen procedural legal task
generators has 256 independent attempts under the same pinned starting policy.
Candidate-level readiness, eligible-response availability, binary reward
entropy, generated-token cost, truncation, and format validity are weighted
means of those fixed component measurements. Effective task coverage is
computed from the frozen candidate weights. Candidate-training and target-
evaluation outcomes are not adapter inputs.
