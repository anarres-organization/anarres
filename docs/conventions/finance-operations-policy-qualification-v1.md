# Finance-operations policy qualification v1

- Stability: development
- Revision: `v1-development`
- Scope: repeated policy attempts on stateful finance-operation scenarios

This convention measures whether a frozen starting policy can operate a
versioned finance environment reliably enough to support later candidate-bank
construction. The native record must preserve the model revision, task-source
revision, agent harness, scenario grouping, rollout count, executable outcome,
material-control outcome, generated-token cost, tool use, truncation, and
infrastructure state.

The qualification profile is not a training-environment forecast. Passing the
gate authorizes candidate measurement under the native study protocol. Failing
the gate records why a policy is unsuitable without treating infrastructure
failures as unsuccessful finance work.

## `tool_protocol_valid_rate`

Proportion of infrastructure-valid episodes whose model traces satisfy the
fixed tool-call protocol. Unit: `fraction`. The sample unit is one episode, and
higher values indicate more reliable operation under the measured harness.

## `executable_completion_rate`

Proportion of tool-protocol-valid episodes that pass the source task's
executable checks. Unit: `fraction`. Direction is contextual because a starting
policy must expose learnable variation: an environment in which the policy
always fails or always succeeds cannot support the planned grouped comparison.

## `mixed_scenario_group_fraction`

Proportion of complete scenario groups containing both successful and failed
rollouts. Unit: `fraction`. Each group contains repeated attempts on one native
scenario. Direction is contextual because the coordinate qualifies measurable
outcome variation rather than downstream utility.

## `material_control_violation_rate`

Proportion of infrastructure-valid episodes that violate a task-defined
material control. Unit: `fraction`. Examples include unauthorized payments or
state changes. Lower is preferable, but the native control taxonomy remains
authoritative.

## `truncation_rate`

Proportion of infrastructure-valid episodes that exhaust the fixed interaction
limit. Unit: `fraction`. Lower is preferable. Truncation remains distinct from
task failure and infrastructure failure.

## `median_generated_tokens_per_episode`

Median generated tokens over infrastructure-valid episodes. Unit:
`generated_tokens_per_episode`. Direction is contextual because it measures
realized interaction cost under a fixed qualification budget.

## `median_tool_calls_per_episode`

Median tool calls over infrastructure-valid episodes. Unit:
`tool_calls_per_episode`. Direction is contextual because the appropriate tool
count depends on the workflow and does not by itself determine quality.

## Readiness and edge cases

The native gate requires complete planned-episode accounting, at least 98%
valid tool protocol, executable completion between 2% and 80%, mixed outcomes
in at least 10% of complete groups and at least two workflow families, and no
more than 10% truncation. Zero completion and zero mixed-group coverage are
valid measurements that fail readiness. Infrastructure-invalid episodes remain
separately counted and are excluded from scientific rates where the native
estimator requires valid execution.
