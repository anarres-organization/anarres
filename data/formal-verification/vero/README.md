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

The next measurement contract is frozen in
[`policy-probe-protocol.v1.json`](policy-probe-protocol.v1.json). It selects an
open-weight Lean starting policy and records the development-only attempt and
resource budgets. Execution remains blocked until the model artifact, inference
runtime, and process-containment gates are qualified. Validate the frozen
contract with:

```bash
python data/formal-verification/vero/validate_policy_probe_protocol.py \
  --protocol data/formal-verification/vero/policy-probe-protocol.v1.json \
  --panel data/formal-verification/vero/development-lifecycle-panel-v2.json \
  --split data/formal-verification/vero/repository-split.json \
  --containment data/formal-verification/vero/containment-contract.v1.json
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
  --protocol data/formal-verification/vero/policy-probe-protocol.v1.json
```
