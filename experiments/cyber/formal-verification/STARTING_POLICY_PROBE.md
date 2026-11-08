# Vero starting-policy probe

The first Vero policy measurement uses
[Leanstral 1.5](https://huggingface.co/mistralai/Leanstral-1.5-119B-A6B)
through the pinned [Mistral Vibe](https://github.com/mistralai/mistral-vibe)
Lean agent. Leanstral is an Apache-2.0 open-weight model designed for Lean 4
proof engineering. Its published training and evaluation interface includes
filesystem edits, compiler feedback, and repository-scale proof work, which
matches Vero more closely than a whole-proof text generator.

The claim-bearing pre-execution contract is frozen in
[`policy-probe-protocol.v5.json`](../../../data/formal-verification/vero/policy-probe-protocol.v5.json).
It pins the model, agent scaffold, prompt, Vero revision, development panel,
sampling settings, resource limits, native outcomes, and stop rules. The probe
uses only the four repositories in the versioned development panel. The ten
qualification and ten prospective repositories remain unopened.

One deployment-calibration pilot ran under the preserved v1 contract and is
excluded from the claim aggregate. It showed that Vibe evaluates its token stop
threshold between model calls, so the final call can raise actual usage above
the threshold. The corrected contract charges every exported input and output
token. Subsequent deployment launches are recorded as exclusions when they
changed socket, concurrency, path, or runtime qualification. The v5 queue
retains the original outcome-blind 32-attempt design in a fresh namespace.

All 32 v5 queue positions completed fresh machine-checked grading. The compact
[result record](../../../data/formal-verification/vero/results/development-policy-measurement.v1.json)
contains the frozen input hashes, execution summary, and measured coordinates.
Every attempt was infrastructure-valid, but no specification passed strict
grading. Both proof modes therefore have zero usable signal density and zero
effective coverage under this interaction contract. The preregistered support
gate failed, so the result does not rank environments or authorize training.

The companion
[`containment-contract.v1.json`](../../../data/formal-verification/vero/containment-contract.v1.json)
freezes the task-sandbox boundary and its required negative tests. The exact
deployment passed those tests before the v5 queue began.

## What the probe measures

Each repository is attempted four times in proof and code-and-proof mode. This
is the smallest prespecified candidate count giving at least 95% fixed-panel
probability of observing eight mixed specification groups at the protocol's 1%
success floor. Fresh Vero grading retains specification-level success, build
validity, approved-axiom status, and unfilled or failed obligations. Vibe's run
export supplies actual model tokens, tool use, wall time, and stop reason.
System measurement adds peak
memory. The first pass asks whether the policy produces nonzero, non-saturated,
mixed verified outcomes at a tractable cost. It does not rank environments or
authorize training.

The completed pass answers that qualification question negatively. All 32
attempts reached the cumulative exported-token threshold after four to six
controller steps. The task tree changed in eight attempts, but fresh grading
found zero strict successes across 2,776 specification trials. This result
measures support under the frozen policy and interaction contract. It leaves
the behavior of other policies and interaction budgets unresolved.

## Containment gate

Vero's fresh re-render protects the score from edits outside expected marker
slots. It does not isolate an agent process from its host. Model attempts must
therefore use Vibe's pinned agent-socket protocol, which routes model-facing
file reads and shell commands to an external sandbox server. The controller may
reach only the local inference endpoint, while the task sandbox has no external
network egress. Only one freshly materialized task, the pinned Lean toolchain,
required local dependencies, and an isolated writable cache may be visible.
Reference solutions, source benchmarks, host credentials, global agent
configuration, and other repository partitions remain outside the agent view.

The interface is a routing mechanism rather than evidence of isolation. Before
the probe runs, negative tests must exercise path and symlink escape, hidden-file
visibility, network egress, process cleanup after timeout, process and memory
limits, and fresh-task reset. Each attempt receives a new sandbox, and the
resulting receipt records the runtime and image digests together with every
test outcome. The bounded
[`serve_vibe_sandbox.py`](../../../data/formal-verification/vero/serve_vibe_sandbox.py)
adapter implements the pinned interface and container boundary. The v5
deployment passed these controls under the exact task image before execution.

The completed queue used the separately promoted deployment bundle that binds
the model digest, inference runtime, serving configuration, containment
controls, and resource-limit receipts. The source contracts remain immutable.
Any revised qualification requires a new protocol version and must preserve the
v5 measurement unchanged.
