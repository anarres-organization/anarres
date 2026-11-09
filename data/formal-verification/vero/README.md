# Vero source adapter

This adapter qualifies Vero as a repository-level Lean source and runtime for bounded
formal-verification studies. Vero contains 43 active multi-module benchmarks
with frozen APIs, formal specifications, reference implementations, and two
evaluation modes: proof completion and joint code-and-proof synthesis.

The adapter audits source identity, benchmark structure, the pinned Lean
runtime, and bounded grader controls. It does not adopt Vero's model-facing
agent integrations, make its 43 repositories independent samples, or authorize
a downstream training experiment.

## Pinned source

[`source-pin.json`](source-pin.json) records the audited Git revision, benchmark
tree, core harness files, Lean version, and expected inventory. The active suite
contains 743 scored APIs and 2,705 scored specifications across 237 modules.
Thirty benchmarks originate from Python, five from Dafny, four from Verus, and
four from Coq.

## Audit a checkout

```bash
python data/formal-verification/vero/audit_source.py \
  --source /path/to/vero \
  --pin data/formal-verification/vero/source-pin.json \
  --output /tmp/vero-source-audit.json
```

The audit verifies the Git revision, benchmark-tree identity, core artifact
hashes, manifest schemas, path containment, file existence, source revisions,
unique benchmark identities, supported modes, and the declared inventory.

## Audit the runtime and grader

Install the lockfile-pinned development environment in the Vero checkout and
the exact Lean toolchain declared by its reference project. Then run:

```bash
python data/formal-verification/vero/audit_runtime.py \
  --source /path/to/vero \
  --pin data/formal-verification/vero/source-pin.json \
  --python /path/to/vero/.venv/bin/python \
  --lake /path/to/lake \
  --output /tmp/vero-runtime-audit.json \
  --repetitions 2
```

The audit builds BankLedger from two clean project copies and runs 93 bounded
upstream controls. These controls exercise native Lean acceptance, inconsistent
and joint-specification evidence, `sorry` and axiom rejection, unsafe and
overfilled-output rejection, fresh rendering, frozen-file restoration, and
removal of injected markers.

## Reproduce the repository split

[`repository-split.json`](repository-split.json) freezes 23 development, 10
qualification, and 10 prospective repositories before policy measurement. The
split is stratified by source language and balanced on specification count. It
uses repository as the partitioning unit.

```bash
python data/formal-verification/vero/build_repository_split.py \
  --source /path/to/vero \
  --pin data/formal-verification/vero/source-pin.json \
  --output /tmp/repository-split.json
```

The [development oracle panel](development-oracle-panel.json) selects the
smallest development repository from each source language for initial
model-facing harness qualification. All four reference projects build under the
pinned toolchain.

The first lifecycle pass preserved two admission findings. Unicode contains six
marker slots that are absent from its manifest, and VerifiedIronkv's fresh
sandbox attempts to use an external mathlib cache. The versioned
[lifecycle panel](development-lifecycle-panel-v2.json) replaces those
repositories without changing the original oracle record.

Run the proof and code-and-proof no-op and reset audit with Vero's lockfile-pinned
Python environment:

```bash
/path/to/vero/.venv/bin/python \
  data/formal-verification/vero/audit_task_lifecycle.py \
  --source /path/to/vero \
  --pin data/formal-verification/vero/source-pin.json \
  --split data/formal-verification/vero/repository-split.json \
  --panel data/formal-verification/vero/development-lifecycle-panel-v2.json \
  --output /tmp/vero-lifecycle-audit.json \
  --repetitions 2
```

## Role in Anarres

Vero contributes a repository-level environment family rather than a universal
target. Its strongest reusable contracts are fresh-project grading, frozen API
and specification layers, explicit negative evidence for inconsistent tasks,
and axiom auditing. Candidate construction must preserve repository grouping,
source provenance, trusted-axiom declarations, and benchmark-specific licenses.

The pinned Lean toolchain, reference build, and bounded grader controls are
qualified. The versioned development lifecycle panel also passes no-op,
clean-reset, manifest-marker, and timeout controls. The frozen split must remain
unchanged while starting-policy support and model-facing resource use are
measured.

[`materialize_probe_task.py`](materialize_probe_task.py) creates one fresh,
Lean-only agent workspace from a repository admitted to the frozen development
panel. It rejects leaked manifests, agent configuration, reference sidecars,
and symlinks outside the task, then records the exact visible tree and
instruction hashes. [`agent-prompt.txt`](agent-prompt.txt) supplies the fixed
Vibe user message; the repository-specific `INSTRUCTION.md` remains the task
contract.

The claim-bearing measurement contract is frozen in
[`policy-probe-protocol.v5.json`](policy-probe-protocol.v5.json). It selects an
open-weight Lean starting policy and records the development-only attempt and
resource budgets. Execution remains blocked until the model artifact, inference
runtime, and process-containment gates are qualified. Validate the frozen
contract with:

[`repetition-reliability.v2.json`](repetition-reliability.v2.json) supplies the
outcome-blind repetition and cost calculation. Four attempts per repository and
mode are the smallest candidate design with at least 95% probability of
detecting eight mixed specification groups at the preregistered 1% strict-
success floor. A preserved v1 deployment pilot is excluded from the claim
aggregate. Vibe checks its 50,000-token controller threshold between model
calls, and the corrected contract charges all actual exported input and output
tokens, including the final call that may cross that threshold.
Two v2 launches ended before inference while qualifying the host socket path.
The later deployment record preserves one completed single-sequence calibration
attempt, excludes overlapping launches made before concurrency qualification,
and records the pre-inference worker failures that informed the final launch
path. The v5 queue uses a fresh namespace under the qualified two-sequence
deployment.

```bash
python data/formal-verification/vero/validate_policy_probe_protocol.py \
  --protocol data/formal-verification/vero/policy-probe-protocol.v5.json \
  --panel data/formal-verification/vero/development-lifecycle-panel-v2.json \
  --split data/formal-verification/vero/repository-split.json \
  --containment data/formal-verification/vero/containment-contract.v1.json \
  --runtime-lock data/formal-verification/vero/runtime/runtime-lock.v1.json \
  --controller-lock data/formal-verification/vero/controller/controller-lock.v1.json \
  --inference-contract data/formal-verification/vero/inference/inference-contract.v1.json \
  --repetition-design data/formal-verification/vero/repetition-reliability.v2.json \
  --measurement-analysis data/formal-verification/vero/measurement-analysis.v2.json
```

[`containment-contract.v1.json`](containment-contract.v1.json) freezes the
external sandbox boundary and the negative tests required before execution. It
does not claim that the pending tests have passed. Validate its structure with:

```bash
python data/formal-verification/vero/validate_containment_contract.py \
  --contract data/formal-verification/vero/containment-contract.v1.json
```

The bounded agent-socket server is
[`serve_vibe_sandbox.py`](serve_vibe_sandbox.py). It starts one ephemeral
Docker container from an immutable image digest, binds only the freshly
materialized task, disables network access, drops Linux capabilities, applies
resource limits, and removes the container when the attempt ends.
The [runtime definition](runtime/README.md) pins the image inputs and exact Lean
toolchain while leaving the built-image digest pending for deployment-host
qualification.
The [controller definition](controller/README.md) pins an isolated Vibe home,
the local Leanstral provider, the tool allowlist, and all scientific attempt
limits. It prevents personal configuration and host-side extensions from
entering a run.
The [inference definition](inference/README.md) pins the official Leanstral
serving requirements and leaves exact deployment capacity and runtime artifacts
pending host qualification.

[`run_probe_attempt.py`](run_probe_attempt.py) is the fail-closed entry point
for one scientific attempt. It refuses to start until the probe, containment,
runtime, controller, inference, and materialized-task records agree. It creates
a private controller home, exposes only the frozen environment and tool
allowlists, starts one ephemeral sandbox, applies the 50-turn, 50,000-token,
and 1,800-second controller thresholds, and preserves the Vibe export and
runtime receipts. Token accounting uses the actual exported usage rather than
treating the between-call threshold as a hard cap.
Scientific retries remain disabled; infrastructure retry handling belongs to
the outer frozen queue.
After completion, [`validate_probe_attempt.py`](validate_probe_attempt.py)
checks the launcher receipt, sandbox receipt, Vibe export, task materialization,
and every frozen contract as one linked evidence bundle. Configuration,
infrastructure, and aborted outcomes are rejected as unscorable rather than
silently entering the scientific aggregate.

Before the first attempt, [`qualify_containment.py`](qualify_containment.py)
runs every negative test named by the containment contract against the exact
image and deployment. It verifies mount and credential isolation, path and
network boundaries, local-inference separation, resource limits, process
cleanup, fresh task reset, controller configuration, and Vibe export coverage.
The harness requires two independently materialized copies of one development
task and a live loopback-only Leanstral endpoint. It never opens a qualification
or prospective repository.

[`promote_probe_deployment.py`](promote_probe_deployment.py) combines the exact
inference and containment receipts with the frozen source contracts. It writes
a separate qualified execution bundle, preserves all 32 attempt identities,
and refuses to overwrite an existing output. The preregistration records in
this directory remain unchanged.

```bash
python data/formal-verification/vero/promote_probe_deployment.py \
  --protocol data/formal-verification/vero/policy-probe-protocol.v5.json \
  --queue data/formal-verification/vero/probe-queue.v5.json \
  --panel data/formal-verification/vero/development-lifecycle-panel-v2.json \
  --containment data/formal-verification/vero/containment-contract.v1.json \
  --runtime-lock data/formal-verification/vero/runtime/runtime-lock.v1.json \
  --controller-lock data/formal-verification/vero/controller/controller-lock.v1.json \
  --inference-contract data/formal-verification/vero/inference/inference-contract.v1.json \
  --containment-receipt /path/to/qualification-receipt.json \
  --inference-receipt /path/to/inference-qualification-receipt.json \
  --runtime-image sha256:<digest> \
  --output /path/to/new/qualified-bundle
```

[`grade_probe_attempt.py`](grade_probe_attempt.py) extracts only the expected
editable slots from a completed task, rerenders them against the pinned source
benchmark, and invokes Vero's fresh build, axiom, hygiene, and joint-claim
checks. Its compact receipt retains specification-level strict rewards and
resource use while replacing machine paths with stable logical identities.

[`probe-queue.v5.json`](probe-queue.v5.json) fixes the 32 claim-attempt
identities in an outcome-blind hash order.
[`measurement-analysis.v2.json`](measurement-analysis.v2.json)
fixes the mode-specific $\rho$ and $H$ estimands, leave-one-repository-out
checks, and whole-repository bootstrap before model attempts. Rebuild or verify
the queue with [`build_probe_queue.py`](build_probe_queue.py), then use
[`aggregate_probe_measurements.py`](aggregate_probe_measurements.py) only after
all fresh grade receipts are present.

The v5 queue is complete. Its compact
[development result](results/development-policy-measurement.v1.json) records 32
infrastructure-valid fresh grades and zero strict successes across 2,776
specification trials. The support gate fails in proof and code-and-proof mode,
so the result blocks candidate ranking and downstream training under this
starting-policy contract. Qualification and prospective repositories remain
unopened.

The next policy is frozen separately in
[`policy-codex-sol-qualification.v1.json`](policy-codex-sol-qualification.v1.json).
It binds GPT-5.6 Sol, Codex 0.154.0, xhigh reasoning, the excluded PrimePy
proof-only task, and Vero's 90-minute budget. The record does not authorize its
own execution. Prompt hashes, fresh-task containment, provider-only controller
networking, and the execution-host grader must be bound in an immutable receipt
before the one-attempt support test can begin.
The matching
[`execution record`](policy-codex-sol-execution.v1.json) binds the rendered
instruction, upstream run configuration, Lean toolchain, no-op fresh-grade
preflight, containment boundary, and attempt identity before inference.

[`policy-budget-calibration.200k.v1.json`](policy-budget-calibration.200k.v1.json)
freezes the first requalification stage after that result. It selects the
smallest development repository, one proof-mode attempt, a 200,000-token
controller threshold, and a 90-minute wall limit. The matching panel,
repetition record, analysis boundary, queue, and
[`controller lock`](controller/controller-lock.200k.v1.json) remain
development-only. The attempt cannot estimate $\rho$, $H$, reliability, or
environment utility.

The v1 attempt reached a clean build but produced no expected-slot edit or
fresh grade. One high-reasoning request exceeded the controller's 720-second
first-output timeout while the local inference backend remained healthy, so
the attempt is classified as an infrastructure failure and excluded from
scientific interpretation. Its stable receipt hashes and resource use are
recorded in
[`policy-budget-calibration.200k-v2.json`](policy-budget-calibration.200k-v2.json).

The v2 calibration tested one output-bounded interface under a fresh attempt
identity. It preserved the 200,000-token cumulative threshold and every
scientific input, while [`controller-lock.200k-v2.json`](controller/controller-lock.200k-v2.json)
added a 4,096-token per-response cap, a 1,800-second request timeout, and no
stream-idle cutoff. The attempt reached infrastructure-valid fresh grading but
made no expected-slot edit and closed no specification. Its trace contains
three responses cut off at exactly 4,096 tokens, almost entirely in reasoning.
Pinned Vibe then discarded each limited response and retried it under its
documented recovery policy. The complete development result is
[`development-budget-calibration.200k-v2.json`](results/development-budget-calibration.200k-v2.json).

The v3 calibration removed only the artificial per-response cap. It retained
the 1,800-second request timeout, 90-minute wall limit, 200,000-token cumulative
threshold, model, prompt, task, sandbox, and grader. The uncapped controller
restored repository inspection and Lean tool use. The policy completed a clean
baseline build, attempted one expected-slot edit, and invoked Lean on the
edited proof file. That attempted proof did not compile and was not retained.
Fresh grading found all nine specifications unfilled. The complete
development result is
[`development-budget-calibration.200k-v3.json`](results/development-budget-calibration.200k-v3.json).

This result crosses the frozen interaction gate without establishing strict
policy support. It authorizes one excluded 1-million-token development
calibration under a fresh identity. Qualification and prospective repositories
remain unopened, and downstream ranking and training remain blocked.

[`policy-budget-calibration.1m-v1.json`](policy-budget-calibration.1m-v1.json)
freezes that final development stage. It scales the cumulative token, wall, and
turn ceilings by five while preserving the model, task, prompt, uncapped
response contract, request timeout, sandbox, and grader. The matching
controller lock, repetition record, analysis boundary, and queue remain
development-only.

The 1-million-token attempt completed infrastructure-valid fresh grading after
1,018,842 exported model tokens and 52 tool calls. It inspected the repository,
drafted proof helpers, replaced the proof file repeatedly, and invoked Lean
after its edits. The final task had removed required marker lines and retained
no valid scored slot, so fresh grading found all nine specifications unfilled.
The complete development result is
[`development-budget-calibration.1m-v1.json`](results/development-budget-calibration.1m-v1.json).

The frozen budget ladder therefore rejects Leanstral as the starting policy for
this Vero contract. Qualification and prospective repositories remain unopened,
and candidate ranking and downstream training remain blocked. A new policy must
have released repository-level Lean evidence or a released Vero baseline before
another development-only qualification is frozen.

The matching [`runtime lock`](runtime/runtime-lock.200k.v1.json) binds the
same immutable Lean image to the one-attempt calibration panel. This keeps the
task runtime unchanged while making the panel hash explicit at preflight.

[`run_probe_queue_item.py`](run_probe_queue_item.py) turns one frozen queue
identity into a fresh task, isolated attempt, linked validation, and fresh
grade. It checks both cross-file hashes and each contract's semantic validator
before materialization. Materialization and grading run through the pinned Vero
checkout's `.venv/bin/python`; the controller and sandbox retain their separate
qualified runtimes. Before inference, the worker invokes Lean and Lake from the
materialized task through the qualified immutable image and records a runtime
receipt. An existing output is never overwritten. A failed stage
remains unclassified and cannot enter the aggregate through a grade receipt.

```bash
python data/formal-verification/vero/serve_vibe_sandbox.py \
  --socket /tmp/anarres-vero-attempt/agent.sock \
  --image registry.example/anarres-vero@sha256:<digest> \
  --workspace /path/to/fresh/task \
  --attempt-id <attempt-id> \
  --task-id <task-id> \
  --model-artifact-digest sha256:<digest> \
  --inference-config-digest sha256:<digest> \
  --receipt /path/to/attempt/runtime-receipt.json
```

Vibe then receives the socket through its pinned `--agent-socket` interface.
The runtime receipt records container identity, method counts, timeouts, output
truncation, infrastructure errors, and cleanup. Qualification additionally
requires every negative test in the containment contract to pass under the same
image and runtime.

After one attempt completes, validate its raw runtime receipt with:

```bash
python data/formal-verification/vero/validate_sandbox_receipt.py \
  --receipt /path/to/attempt/runtime-receipt.json \
  --protocol data/formal-verification/vero/policy-probe-protocol.v5.json
```
