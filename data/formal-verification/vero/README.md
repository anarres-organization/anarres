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

## Role in Anarres

Vero contributes a repository-level environment family rather than a universal
target. Its strongest reusable contracts are fresh-project grading, frozen API
and specification layers, explicit negative evidence for inconsistent tasks,
and axiom auditing. Candidate construction must preserve repository grouping,
source provenance, trusted-axiom declarations, and benchmark-specific licenses.

The pinned Lean toolchain, reference build, and bounded grader controls are
qualified. Before frozen-policy measurement, the remaining task interface must
pass timeout and cost tests. The frozen split must remain unchanged while
policy support is measured.
