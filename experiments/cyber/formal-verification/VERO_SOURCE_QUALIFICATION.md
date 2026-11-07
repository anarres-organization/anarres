# Vero source qualification

**Audit date:** 2026-11-07

This record qualifies the structure, provenance, pinned Lean runtime, and
bounded grader controls of Vero's active benchmark suite. It does not qualify a
model-facing agent or a downstream training environment.

## Pinned source

| Component | Immutable identity |
| --- | --- |
| Repository | `sunblaze-ucb/vero` |
| Commit | `0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09` |
| Benchmark tree | `21f18407dc780b2500f4a81be93261c8b4426bfb` |
| Lean | 4.29.1 |
| Harness license | Apache-2.0 |
| Benchmark licenses | Per-source licenses, including three active LGPL exceptions |

The source identity, artifact hashes, expected inventory, and license
exceptions are recorded in the
[source pin](../../../data/formal-verification/vero/source-pin.json).

## Reproduced inventory

The [source audit](../../../data/formal-verification/vero/audit_source.py)
verified benchmark identities, upstream source revisions, manifest paths,
active files, and aggregate counts.

| Unit | Count |
| --- | ---: |
| Active repository benchmarks | 43 |
| Modules | 237 |
| Scored APIs | 743 |
| Scored specifications | 2,705 |
| Benchmarks declaring trusted axioms | 5 |
| Declared trusted axioms | 81 |

The source-language composition is 30 Python, five Dafny, four Verus, and four
Coq repositories. Every active manifest supports proof and code-and-proof modes
and pins an upstream source revision.

## Scientific role

Vero provides the strongest currently released repository-level candidate in
the source landscape. Its frozen API and specification layers permit separate
proof-only and joint implementation-and-proof environments. Fresh-project
grading, marker-only overlays, axiom checks, and machine-checked negative
evidence are useful integrity contracts for Anarres.

The 43 repositories are heterogeneous and are not interchangeable task rows.
Repository is the minimum partitioning unit. Trusted axioms, source language,
upstream license, specification count, and dependency structure remain visible
in candidate construction and evaluation.

## Runtime and grader qualification

The [runtime audit](../../../data/formal-verification/vero/audit_runtime.py)
reproduced two clean builds of the BankLedger reference project under Lean
4.29.1 at compiler commit
`f72c35b3f637c8c6571d353742168ab66cc22c00`. Both builds used the same
source digest and completed successfully.

The bounded upstream suite then passed all 93 selected controls. Three controls
invoke the native evaluator on an inconsistent-specification fixture, including
an accepted individual unsatisfiability proof, an accepted joint
unsatisfiability proof, and rejection of an unpaired satisfiability claim. The
remaining controls exercise `sorry`, user-axiom, `admit`, and unsafe-declaration
rejection together with overfilled and malformed claim rejection. They also
test fresh-project rendering, frozen-file restoration, injected-marker removal,
and benchmark materialization.

This qualifies the released runtime and grader behavior covered by those
controls. It does not establish policy support, useful task difficulty, or
downstream learning value.

## Repository-disjoint split

The [frozen split](../../../data/formal-verification/vero/repository-split.json)
assigns 23 repositories to development, 10 to qualification, and 10 to the
prospective target before any policy measurement. Each partition contains
Python, Dafny, Verus, and Coq sources. Specification counts are 1,494, 616, and
595, respectively. The builder balances specification volume within
source-language quotas and uses only benchmark identities and source metadata.

Specifications, APIs, and modules remain nested within repositories. They do
not increase the number of independent held-out groups.

## Four-language development oracle

The [development oracle panel](../../../data/formal-verification/vero/development-oracle-panel.json)
selects the development repository with the fewest specifications in each
source language. Fresh copies of primepy, piggybank-v2, unicode-v2, and
verified_ironkv all build under the pinned Lean toolchain. Their declared Lake
dependencies are resolved from repository-pinned revisions.

This confirms that all four source-language families contain at least one
executable development oracle. It does not measure no-op rejection, model
success, mixed outcomes, or task cost.

## Remaining gates

The next gate is model-facing qualification under the frozen split. The task
interface must measure oracle and no-op behavior, timeout handling,
repeated-reset agreement, wall time, memory, tool calls, generated tokens, and
starting-policy support.
