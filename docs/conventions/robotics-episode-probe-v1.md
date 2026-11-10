# Robotics episode probe v1

- Stability: development
- Revision: `v1-development`
- Scope: repeated closed-loop episodes grouped by task under one starting policy

This convention supports the synthetic CLI fixture. A real adapter must also
record the policy, runtime, dataset, task, embodiment, and evaluation contract
used to produce the measurements. Natural termination and external truncation
remain separate in the native evidence.

A profile exports only the coordinates defined by its native study. The list
below covers the broader robotics program and does not require every study to
manufacture every coordinate.

## `target_relevance`

Study-defined similarity or relevance between selected experience and the
frozen evaluation target. Unit: `normalized_score`. The estimator must identify
the representation, target split, and aggregation rule.

## `policy_weakness`

Study-defined extent to which selected experience exposes failures or weak
behavior of the starting policy. Unit: `normalized_score`. Direction is
contextual because severe failures may be outside the policy's learnable
frontier.

## `selection_coverage`

Study-defined coverage or diversity of the selected episodes, states, tasks, or
operators. Unit: `normalized_score`. The native record defines the support and
distance function.

## `quality_correction`

Magnitude of the study's data-quality adjustment before or during candidate
construction. Unit: `normalized_score`. The coordinate records an intervention
property and does not assume that stronger filtering improves downstream
performance.

## `measurement_reliability`

Agreement of the policy-relative measurement across declared independent
views, checkpoints, or seeds. Unit: `normalized_score`. The agreement statistic
remains part of the measurement contract.

## `missingness_rate`

Fraction of expected native measurements absent after runtime and sensor
accounting. Unit: `fraction`. Missing episodes are not unsuccessful episodes.

## `episode_success_variation`

Mean per-task Bernoulli variance of repeated episode success. Unit:
`bernoulli_variance`. The coordinate describes observed variation under the
starting policy and has contextual direction.

## `mixed_task_coverage`

Fraction of measured tasks with at least one successful and one unsuccessful
episode. Unit: `fraction`. The sample count is the number of tasks.

## `mean_action_steps`

Arithmetic mean number of executed action steps over valid episodes. Unit:
`action_steps_per_episode`. Truncated, failed, and invalid episodes must remain
distinguishable in the native evidence.
