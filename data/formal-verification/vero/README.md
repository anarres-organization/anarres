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

The installed adapter accepts one native source format,
`vero-checkout-v1`, for the exact public Vero revision recorded in
[`source-pin.json`](source-pin.json). Create an environment source manifest
beside the checkout and run the shared qualification flow:

```bash
anarres init /path/to/vero \
  --adapter formal \
  --revision git:0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09 \
  --license "Apache-2.0 with benchmark-specific upstream licenses"
anarres qualify /path/to/vero/anarres.toml
```

Qualification checks the Git revision and benchmark tree, core artifact
hashes, all benchmark manifests and referenced files, immutable upstream
revisions, license exceptions, and the frozen inventory. It does not build
Lean, run a policy, open qualification or prospective tasks, or reproduce the
released measurement.

## Qualify an execution contract

Runtime qualification is a separate, model-free gate. Begin with
[`runtime-contract.v1.example.json`](runtime-contract.v1.example.json), retain
the exact source binding, and declare one proof or codeproof execution mode.
Then run:

```bash
anarres formal qualify-runtime \
  --manifest /path/to/vero/anarres.toml \
  --runtime /path/to/runtime-contract.json \
  --lean-executable /path/to/lean \
  --lake-executable /path/to/lake \
  --output /path/to/runtime-report.json
```

The preflight requalifies the source and verifies the package lock, local Lean
and Lake identities, execution mode, task-only visibility, tool allowlist,
token and wall ceilings, strict verifier command, network policy, cleanup,
filesystem boundaries, and resource limits. It writes a content-addressed
report and does not open a task or contact a model. Source qualification and
runtime qualification remain distinct states.

A qualified runtime report does not enable `policy-probe`. Model execution
remains unavailable until a sanitized task route independently passes the
containment tests and binds its policy, seeds, verifier, runtime, and source
identities.

The underlying source audit remains available for repository development:

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
Docker container from an immutable image digest, copies the freshly
materialized task into an in-memory workspace, disables network access, drops
Linux capabilities, applies resource limits, collects the final workspace, and
removes the container when the attempt ends.
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
The first launch stopped before inference because Codex 0.154 no longer accepts
the adapter's `--full-auto` flag. The frozen
[`infrastructure-retry record`](policy-codex-sol-infrastructure-retry.v1.json)
replaces it with the current non-interactive workspace-write flag, preserves
every scientific setting, and permits the protocol's single infrastructure
retry.

The replacement launch completes in 1,668.606 seconds and passes all nine
PrimePy specifications under Vero's fresh slot-only grader. The compact
[qualification result](results/development-policy-qualification.codex-sol-v1.json)
records zero failed, unfilled, overfilled, tainted, or unapproved-axiom
outcomes. One attempt establishes strict task support without estimating
reliability. The post-run audit found broader read and temporary-write scope
than the intended task-only boundary, although no reference proof or protected
repository was accessed. The task-only boundary below closed that gap before
the repeated measurement ran.

### Task-only execution boundary

[`containment-contract-codex-sol.v3.json`](containment-contract-codex-sol.v3.json)
freezes the tightened route for GPT-5.6 Sol attempts and the seventeen negative
controls it must pass. It supersedes the v2 record, which remains unchanged.
[`containment-contract-codex-sol.v4.json`](containment-contract-codex-sol.v4.json)
keeps that route and adds request validation, described below.
The v2 runner tested a container it started itself rather than the model's
route, and two of its tests passed unconditionally. The v3 route runs the task
as the unprivileged host user with network and IPC namespaces disabled, a
read-only message-queue mount, and an in-memory task workspace. Writes are
confined to the task, `/tmp`, and `/cache`.

Fresh grading previously compiled the model's Lean on the controller host,
where elaboration-time code can run with host network and file access. The
grader now runs every Lake invocation inside the same runtime image with the
same isolation flags, mounting only the fresh evaluation directory. An attempt
whose task tree links outside the task is recorded as an integrity failure and
is not graded. Grader, sandbox, and integrity failures stay unscored and outside
every aggregate. The wall limit is a hard deadline: requests and commands are
bounded by the remaining budget, and only a request still pending at the
deadline ends the attempt with `wall_time_limit`.

[`run_containment_tests.py`](run_containment_tests.py) qualifies that boundary
without contacting a model. It launches the sandbox server through the probe's
own command builder, so every control travels the agent socket a model would
use. It materializes independent development tasks and plants host-side
canaries for reference solutions, protected repositories, and credentials, with
a positive control for each. It runs one complete attempt through the probe's
own entry point with a deterministic fixture policy that writes a correct
proof. It grades one accepted proof and fixed no-op, invalid-proof,
forbidden-axiom, admitted-proof, and unsafe-declaration fixtures, and checks
that elaboration-time code inside the grader cannot write host files or reach
the network. The runner writes one content-addressed receipt that binds the
runtime image, the source and runtime qualification reports, the controller
configuration, every materialization, the route's file hashes, and every
control outcome.

```bash
python data/formal-verification/vero/run_containment_tests.py \
  --image sha256:<deployment-image-digest> \
  --vero-root /path/to/vero \
  --vero-python /path/to/vero/.venv/bin/python \
  --source-report /path/to/source-report.json \
  --runtime-report /path/to/runtime-report.json \
  --work-root /path/to/scratch \
  --output /path/to/new/receipt-directory
python data/formal-verification/vero/validate_task_boundary_receipt.py \
  --contract data/formal-verification/vero/containment-contract-codex-sol.v4.json \
  --receipt /path/to/new/receipt-directory/task-boundary-receipt.json \
  --route-root data/formal-verification/vero
```

The runtime report must declare the runner's stand-in controller endpoint
(`http://127.0.0.1:18765` by default) and the route's limits. A receipt is
qualified only when every control passes, every bound report field agrees
with the exercised route, and the image runs natively. It qualifies only the
image it binds, and a run under emulation is a fixture execution. The frozen
contract never changes: `anarres formal qualification` reports the boundary as
qualified only after a validated receipt directory is released at the path the
contract names, and `policy-probe` remains unavailable until a
repeated-measurement protocol is frozen. That protocol must cite the released
receipt and its image, and it must state how integrity failures enter its
estimates.

Grading also confirms every specification Vero reports as passed. Vero parses
its axiom report from Lake output, and model code can forge it in several ways:
by printing during elaboration, through a tactic trace that runs no code, or
from an initializer that runs whenever a check imports the model's module and
then exits before the real check. A model can also switch kernel checking off
while its module builds, so a false proof compiles, or declare its own axiom
under the name of an axiom the benchmark trusts. Fixtures and grader tests show
that Vero passes each of these. Grading therefore builds a reference of the
untouched task in its own contained Lake invocation and runs
[`AnarresAxiomCheck.lean`](AnarresAxiomCheck.lean) in a sealed container, once
for each of Vero's axiom-check files. The checker never imports a model module.
It reads the compiled libraries of both builds as data and sends each target
theorem, with every safe declaration it depends on, back through the kernel.
It requires every declaration the proof rests on that the reference also
declares to equal the reference, unless it is a slot the model fills, so a
trusted axiom keeps the meaning the reference gives it. Every axiom outside the
toolchain must be the reference's own declaration. A specification stays passed
only when the one theorem Vero graded for it is confirmed. Every forgery above
is downgraded.

A check that does not finish gets one retry with three times the budget Vero
gives a compilation. If it still does not finish, the specification is recorded
as `check_incomplete`. A codeproof `sat` claim rests on Vero's separate joint
rerender, which the checker does not cover, and is recorded as
`sat_unverified`. Both are reported apart from passes, model failures, and
infrastructure failures, and the repeated-measurement protocol must state how
they enter its estimates. A container that cannot start, a reference build that
fails or cannot be read, or a grading stage that outlives the sum of Vero's own
Lake budgets leaves the attempt unscored.

No directory the model can write is on host disk. The task workspace is an
in-memory filesystem inside the sandbox container, limited to 8 GiB and 200,000
entries, and the task is copied in when the sandbox starts. Each grading build
compiles in a container that sees the evaluation directory read-only and writes
its Lake outputs to an in-memory volume limited to 16 GiB and 500,000 entries.
The kernel enforces these limits on every byte, including files a process
deletes while holding them, passes through a socket, or keeps only as a memory
mapping. While a container runs, its in-memory pages also count against its
memory limit, which swap cannot extend; a grading volume keeps its pages after
its build container exits, so each concurrent grading can hold up to its volume
limit of host memory until cleanup. A task that fills its space therefore only
fails its own commands or build, which is scored as the policy's result.
Containers keep no log on host disk, each stream of Lake output is cut at 64 MiB
before it reaches the grader, a Lake exit status that Docker reserves for its
own failures is reported as an ordinary failure, and once Lake returns the
grading container exits, ending every process the build left in it.

When the attempt ends, the sandbox stops the task's processes and archives the
workspace from inside the container. It chooses each member from its metadata
before reading any data, so a file whose apparent size would pass the workspace
limit, a path longer than 1,024 bytes or 64 components, a name that is not
UTF-8, a special file, or anything past the entry limit is left behind, and a
sparse file or a deep directory chain cannot make the archive larger than the
workspace. The host reads at most that many bytes and
extracts them with a filter that also leaves absolute or escaping links behind.
What is left behind is recorded, and the rest is graded. Only a workspace that
cannot be collected at all, for example because the task ran its container out
of memory, is an integrity failure. A collection that outlasts its ten-minute
limit is an infrastructure failure; the byte, entry, path, and depth limits keep
a collection far inside it.

Before grading, a scan that lexes each slot body as Lean, so comment markers
inside strings cannot hide code, also rejects bodies that run code during
elaboration, switch kernel checking off, or carry an attribute outside a list
of toolchain attributes. It reads each body twice, once recognizing
interpolated strings by context and once treating every string as
interpolated. The scan is syntactic and may still miss constructs; confirming a
pass never depends on it. Code that evades it runs only inside the contained
build, where it can at most force `check_incomplete` on a specification Vero
passed, which never produces a confirmed pass. A policy can also cause an
integrity failure deliberately, for example by exhausting its container's
memory. The repeated-measurement protocol therefore counts policy-caused
integrity failures and `check_incomplete` as failures in its primary estimate.

The released receipt in
[`results/task-boundary-qualification.codex-sol-v3/`](results/task-boundary-qualification.codex-sol-v3/)
qualifies the route on the image it binds,
`sha256:c48a1075ff53f6107f8f812b5072f5b6d470e5d722b40ff3bce589b5b6015825`, run
natively on an amd64 Docker host. That digest is a local image identifier, so a
protocol that cites the receipt must run that exact image. All seventeen
controls passed. Each network and visibility control has a positive control: a
networked container reaches the outside and the stand-in controller endpoint,
and a container with the agent socket mounted finds it. The bound reports agree
with the exercised route on all twenty compared fields, and the receipt bundles
the runtime contract the runtime report qualified. The v1 runtime contract
cannot state this route's filesystem layout or Lake location, and its cleanup
fields are not compared, so the receipt names those three as uncompared and the
runner's own controls observe them instead.

That image was pruned from the execution host before any repeated-measurement
attempt. It was rebuilt from [`runtime/Dockerfile`](runtime/Dockerfile) as
`sha256:9ca594ce645b2be8903dcdadd7c58c11bb0d8b7448077842ee559e0a4dfb574c`, and
the same seventeen controls passed on it under the same contract, route,
controller, and Lean build. That receipt is in
[`results/task-boundary-qualification.codex-sol-v4/`](results/task-boundary-qualification.codex-sol-v4/),
and the first repeated-measurement protocol cited it and its image.

The v3 sandbox server recorded any unexpected error while serving a policy
request as an infrastructure failure. GPT-5.6 Sol sometimes writes a Lean
focusing dot as a NUL byte, which no process argument can hold, so one of its
own commands voided an attempt and forced a rerun. An unpaired surrogate or an
argument longer than the kernel accepts would have done the same.
[`containment-contract-codex-sol.v4.json`](containment-contract-codex-sol.v4.json)
answers such requests to the policy as invalid requests instead. The same
seventeen controls passed on the rebuilt image under that contract, and its
receipt is in
[`results/task-boundary-qualification.codex-sol-v5/`](results/task-boundary-qualification.codex-sol-v5/).

The earlier GPT-5.6 Sol development attempts were graded before contained
grading and the trusted checker existed. Every one of them that has a grading
report and at least one passed specification was regraded through the current
grader, thirteen attempts including the screen behind the 388 of 694 result.
All 447 specifications Vero passed in them are confirmed. Six attempts had no
grading report and five passed nothing, so neither group was regraded. The
artifacts of the original released PrimePy qualification attempt were not
available, so that attempt was not regraded.

### Repeated measurement

[`policy-probe-protocol.codex-sol-v2.json`](policy-probe-protocol.codex-sol-v2.json)
freezes the repeated GPT-5.6 Sol measurement before any of its attempts. It
replaces protocol v1, whose queue was stopped after six runs over five entries
because of the NUL-byte classification above. The
[v1 stop record](results/repeated-measurement-stop.codex-sol-v1.json) lists
those runs with their tokens and planning cost and no specification outcome.
None of them enters the v2 aggregate, and no v1 specification outcome was read
before v2 was frozen. It
measures the same four development repositories as the earlier starting-policy
measurement, with four attempts per repository and mode, 32 in all, under the
qualified task-only route. The protocol binds the model, reasoning setting,
harness, prompt, inference configuration, budgets, and retry policy. Its
validator checks each setting against the hash-pinned harness and requires the
released boundary receipt to validate against the current route files.
Repeated attempts within a repository are measurements of that repository,
which remains the independent unit. The
[screen usage record](results/development-screen-usage.codex-sol-v1.json)
shows that the 100-turn budget ended every Verified Bitmasks and Arithmetic
attempt in the screen behind 388 of 694, so the result describes reliability
under that budget.

[`measurement-analysis.codex-sol-v1.json`](measurement-analysis.codex-sol-v1.json)
keeps the advantage-mass, coverage, cluster-sensitivity, and support-gate
definitions of the earlier analysis contract. A specification earns strict
reward only when the trusted axiom check confirms Vero's pass, so
`check_incomplete` and `sat_unverified` count as failures. An upper bound that
counts them as passes is reported beside the primary estimate and never decides
anything. A policy-caused integrity failure scores zero on every specification
of its attempt. An infrastructure failure is never scored. Each queue entry
gets one retry: a failure during grading regrades the preserved workspace, and
any other infrastructure failure reruns the attempt under a fresh run identity.
Every receipt must report the task digests frozen in the protocol, which come
from materializing each task twice on the execution host without a model. An
entry without a scored or integrity-failure receipt makes the release an
abstention. The measurement is
ready only when the support
gate passes, each mode has mixed outcomes in at least two repositories, and
leaving out any one repository still leaves eight mixed specification groups.
Otherwise the release records an abstention.

[`probe-queue.codex-sol-v2.json`](probe-queue.codex-sol-v2.json) fixes the 32
attempt identities in an outcome-blind hash order.
[`run_codex_sol_queue_item.py`](run_codex_sol_queue_item.py) runs one entry at
a time, in queue order, through the unchanged harness. Before every run it
checks that the Vero checkout, which supplies both the task and the grader, is
at the pinned commit with no modified tracked files. It records each run before
the run starts, so a run that never finishes stays on the ledger as
interrupted, counts as an infrastructure failure, and is charged the
authorization's reserve. It refuses to start without a separate authorization
record that binds the protocol, the queue, a spend ceiling, and a per-attempt
reserve. An attempt starts only while the planning cost so far plus the reserve
stays within the ceiling. One run can still cost more than the reserve. The
ceiling is never raised after the first run, and a queue stopped at the ceiling
is released as an abstention.
[`execution-authorization.codex-sol-v2.json`](execution-authorization.codex-sol-v2.json)
sets the ceiling to the approved $250 less the planning cost of the stopped v1
queue. The screen's token use suggests about $150 at the contract's planning
prices.
[`aggregate_codex_sol_measurements.py`](aggregate_codex_sol_measurements.py)
checks the protocol, queue, and authorization, confirms that each receipt
restates its run records, and records the digest of every input.

```bash
python data/formal-verification/vero/validate_codex_sol_probe_protocol.py \
  --protocol data/formal-verification/vero/policy-probe-protocol.codex-sol-v2.json
python data/formal-verification/vero/build_probe_queue.py \
  --protocol data/formal-verification/vero/policy-probe-protocol.codex-sol-v2.json \
  --panel data/formal-verification/vero/development-lifecycle-panel-v2.json \
  --output data/formal-verification/vero/probe-queue.codex-sol-v2.json --check
```

### Repeated-measurement result

The v2 queue completed on 24 November 2026 with one run per entry. Thirty-one
attempts were scored and one was a policy-caused integrity failure. No run
failed for infrastructure reasons, so no entry used its retry. The
[released measurement](results/repeated-measurement.codex-sol-v2/measurement.json)
is ready. Of 2,776 specification trials, 1,653 passed strictly, and 289
specification groups were mixed. Both modes have mixed groups in Arithmetic and
Verified Bitmasks. Leaving out Arithmetic, the repository with the most mixed
groups, still leaves 81. PiggyBank and PrimePy passed every specification in
every attempt, so they contribute no signal.

| Repository | Proof: strict passes | Proof: mixed groups | Code and proof: strict passes | Code and proof: mixed groups |
| --- | --- | --- | --- | --- |
| Arithmetic | 224 / 764 | 112 of 191 | 553 / 764 | 96 of 191 |
| Verified Bitmasks | 235 / 496 | 39 of 124 | 385 / 496 | 42 of 124 |
| PiggyBank | 92 / 92 | 0 of 23 | 92 / 92 | 0 of 23 |
| PrimePy | 36 / 36 | 0 of 9 | 36 / 36 | 0 of 9 |

| Mode | Signal density $\rho$ per million model tokens | Coverage $H$ | 90% repository bootstrap for $\rho$ and $H$ |
| --- | --- | --- | --- |
| Proof | 4.17 | 0.43 | $\rho$ 0 to 6.55, $H$ 0 to 0.55 |
| Code and proof | 3.24 | 0.39 | $\rho$ 0 to 5.25, $H$ 0 to 0.47 |

The bootstrap intervals reach zero because only two of the four repositories
carry signal. The queue used 177.8 million model tokens and 3.7 agent hours. Its
planning cost is $134.54, and the stopped v1 queue adds $26.53. These are
estimates at the contract's planning prices, not a billing record.

Four details shape how the result can be read.

- In the Arithmetic proof attempt `r02` the policy wrote `native_decide` in two
  proof slots of `Proof/Power2.lean`. The frozen contract scores every one of
  that attempt's 191 specifications as zero. The prompt and task instruction
  forbid `axiom`, `sorry`, and `admit` and require `#print axioms` to report
  only the three standard axioms, which `native_decide` breaks. They do not
  name `native_decide` itself. Because that attempt is zero, no Arithmetic
  proof specification reaches four successes, and 28 specifications that passed in the other three attempts
  count as mixed. Treating the attempt as missing, a sensitivity check outside
  the frozen analysis, gives 123 mixed proof groups, $\rho$ of 3.32, and $H$ of
  0.35.
  The gates still pass.
- In the Verified Bitmasks proof attempt `r02` five passes were downgraded to
  `axiom_recheck_failed`. The policy imported `Impl/BitFieldsAxioms.lean`, which
  is unchanged from the task, and used its curator-declared axiom
  `axiom_as_uint64_as_bv64`. The trusted checker builds its reference from the
  untouched task's import closure, which never loads that module, so it refuses
  the axiom. The strict rule counts these five as failures. Counting them as
  passes, another check outside the frozen analysis, gives 1,658 passes and 294
  mixed groups, with no change to any gate. The frozen upper bound, which counts
  `check_incomplete` and `sat_unverified` as passes, equals the primary result
  because no run reported either status.
- All 16 attempts that stopped at the 100-turn limit are Arithmetic or Verified
  Bitmasks attempts, so every mixed group comes from an attempt the turn budget
  ended. The 92 build errors come from four runs whose last edit left one module
  failing to compile. The measurement describes the policy under this budget.
- The run records bind the authorization, which binds the protocol that names
  the model and pins the harness. The transcripts do not show which model the
  API served.

The next frozen protocol should name every banned tactic in the prompt and
should build the checker's reference from the task's trusted-axiom modules.
Both changes touch hash-pinned files, so they wait for a new protocol and
boundary receipt instead of changing this one. GPT-5.6 Sol is a hosted model
that this project cannot train, so a prospective environment comparison also
needs a trainable starting policy measured under the same contract.

The [release directory](results/repeated-measurement.codex-sol-v2/) holds the
grade receipt and run records of every entry. The started records omit the host
interpreter path and are otherwise unchanged. The directory's
`MANIFEST.sha256` lists the digest of every released file. `anarres formal verify` checks every file
against that manifest, then reruns the frozen aggregator over the records. It
requires exact structural and discrete agreement and permits only floating-point
roundoff within $10^{-12}$ across supported Python versions.

The earlier v1 protocol was corrected twice at its original paths before the
first attempt: once to harden execution semantics and once to bind a newly
qualified runtime image after the prior local image was pruned. The
[freeze-history record](repeated-measurement-freeze-history.json) preserves the
commit, digest, and size of every revision. Only the final v1 revision was
executed, then stopped and superseded by v2. The v2 protocol, queue, and
authorization remained byte-stable through execution and release.

Project the completed measurement into the shared Anarres profile contract
without changing that interpretation:

```bash
uv tool install ./data/formal-verification/vero
anarres adapter doctor formal
anarres formal status --repository /path/to/anarres
anarres formal qualification --repository /path/to/anarres
anarres formal verify --repository /path/to/anarres
anarres formal profile --repository /path/to/anarres \
  --output-dir /tmp/vero-profiles

# The native exporter remains available for repository development.
uv run python data/formal-verification/vero/export_environment_profiles.py \
  --output-dir /tmp/vero-profiles
anarres qualify \
  /tmp/vero-profiles/vero-codex-sol-development-proof-v2.profile-input.json
anarres measure \
  /tmp/vero-profiles/vero-codex-sol-development-proof-v2.profile-input.json \
  --output /tmp/vero-profiles/vero-codex-sol-development-proof-v2.profile.json
anarres validate \
  /tmp/vero-profiles/vero-codex-sol-development-proof-v2.profile-input.json \
  /tmp/vero-profiles/vero-codex-sol-development-proof-v2.profile.json

# The superseded Leanstral negative measurement remains reproducible.
anarres formal profile --repository /path/to/anarres \
  --measurement leanstral-v5 \
  --output-dir /tmp/vero-leanstral-profiles
```

The adapter emits separate `proof` and `codeproof` profiles because their
native rewards are not interchangeable. By default, `anarres formal profile`
projects the completed GPT-5.6 Sol measurement, preserving its positive signal
density, effective coverage, measured token cost, readiness decision, and
released evidence digests. The profiles remain development evidence: the
hosted starting policy cannot support the planned matched training comparison,
and neither candidate ranking nor downstream training is authorized. The
superseded Leanstral profiles preserve exact zero signal and coverage, positive
measured cost, and the failed support gate. They remain available through the
explicit `leanstral-v5` selector.

`anarres formal qualification` reports the separate GPT-5.6 development
support test. It reproduces the strict 9/9 PrimePy result, realized cost,
artifact hashes, and containment finding without adding any outcome to the
Leanstral profiles. The one-attempt result establishes task support but does
not authorize repeated measurement, candidate ranking, or downstream training.

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
