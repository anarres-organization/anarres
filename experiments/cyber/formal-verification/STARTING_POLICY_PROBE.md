# Vero starting-policy probe

The first Vero policy measurement uses
[Leanstral 1.5](https://huggingface.co/mistralai/Leanstral-1.5-119B-A6B)
through the pinned [Mistral Vibe](https://github.com/mistralai/mistral-vibe)
Lean agent. Leanstral is an Apache-2.0 open-weight model designed for Lean 4
proof engineering. Its published training and evaluation interface includes
filesystem edits, compiler feedback, and repository-scale proof work, which
matches Vero more closely than a whole-proof text generator.

The exact pre-execution contract is frozen in
[`policy-probe-protocol.v1.json`](../../../data/formal-verification/vero/policy-probe-protocol.v1.json).
It pins the model, agent scaffold, prompt, Vero revision, development panel,
sampling settings, resource limits, native outcomes, and stop rules. The probe
uses only the four repositories in the versioned development panel. The ten
qualification and ten prospective repositories remain unopened.

The companion
[`containment-contract.v1.json`](../../../data/formal-verification/vero/containment-contract.v1.json)
freezes the task-sandbox boundary and its required negative tests. Its status is
unqualified until those tests run under the exact deployment runtime.

## What the probe measures

Each repository is attempted twice in proof and code-and-proof mode. Fresh Vero
grading retains specification-level success, build validity, approved-axiom
status, and unfilled or failed obligations. Vibe's run export supplies model
tokens, tool use, wall time, and stop reason. System measurement adds peak
memory. The first pass asks whether the policy produces nonzero, non-saturated,
mixed verified outcomes at a tractable cost. It does not rank environments or
authorize training.

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
test outcome.

Execution remains blocked until the local model digest, inference runtime,
serving configuration, containment controls, and resource-limit receipts are
recorded. This keeps a harness smoke test from silently becoming a scientific
measurement under an incomplete contract.
