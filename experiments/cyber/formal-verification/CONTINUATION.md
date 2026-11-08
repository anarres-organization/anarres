# Formal-verification continuation guide

**Status date:** 2026-11-08

The next scientific milestone is a prospective comparison of qualified
formal-verification environments, followed by checkpoint-level regression
forecasting. This guide records the current evidence boundary and the order in
which the remaining work should proceed.

## Current state

The workstream has three completed foundations:

1. The [public-evidence record](public-evidence/README.md) reconstructs
   decisions from VeruSyn, Re:Form, Formal Disco, and Vericoding. It also
   records the production target established by Anthropic and Theorem.
2. The OSS Verify adapter preserves statement, source, checker, and entry-point
   identities. Vero has a pinned source revision, repository-disjoint split,
   fresh grader, lifecycle controls, and a frozen 32-attempt development queue.
3. The Vero deployment path has exercised the first four positions in that
   queue. Three reached fresh machine-checked grading and one ended during the
   model-attempt stage. The remaining 28 positions have not run. This partial
   development measurement does not rank environments or authorize training.

No claim-bearing reinforcement-learning run has begun. Qualification and
prospective repositories remain unopened.

## Why this advances production verification

The frontier target is verified software built from real code, explicit
specifications, machine semantics, and kernel-checked proofs. Anthropic and
Theorem demonstrate this workflow for OSS-Fuzz entry points compiled to RISC-V
and verified in Rocq. The initial Anarres environments use smaller Lean and
repository-level tasks because they make source qualification, reward
integrity, repeated measurement, and controlled training practical. Transfer
to the OSS-Fuzz and Rocq setting is a later test, not an assumption.

The program asks two linked questions:

1. Which candidate environment produces the greatest held-out improvement at a
   fixed interaction budget?
2. Which held-out tasks or capabilities are likely to regress as aggregate
   verification performance improves?

Both questions require downstream training outcomes. Starting-policy
measurements alone can qualify candidates and form predictions, but they
cannot establish utility.

## Next execution steps

### 1. Close the Vero development measurement

- Compact the four existing execution receipts without machine paths or
  transient logs.
- Classify the failed attempt as scientific, infrastructure-invalid, or
  configuration-invalid under the frozen contract.
- Make the rolling scheduler fail closed while continuing past a typed
  scientific failure.
- Run the 28 identities that have not been attempted. Rerun the failed identity
  only if the frozen retry rule permits its typed disposition. Never overwrite
  or relabel the first four attempts.
- Aggregate the 32 attempts only after every identity has a valid typed
  disposition.

The output is a bounded support, reliability, and cost record for one starting
policy. It remains a development measurement.

### 2. Construct the candidate panel

Admit three to six environment distributions only after their sources and
harnesses pass qualification. The first panel should draw from mechanistically
distinct choices such as:

- isolated proof completion
- repository-context proof completion
- specification plus proof
- chronology-correct cryptographic proof development
- training-only proof reuse
- policy-gap weighting under a fixed task source.

Each candidate record must freeze task identities, source revision,
dependencies, agent-visible context, checker, reset behavior, sampling weights,
starting policy, and interaction budget. Native Lean, Rocq, Verus, and Dafny
outcomes remain separate.

### 3. Measure candidates before training

Use repeated attempts from the intended starting policy to measure:

- strict machine-checked success and valid-output rate
- mixed success across attempts
- specification coverage and semantic integrity
- dependency and repository-context structure
- generated tokens, tool calls, wall time, and verifier cost
- reset reliability and infrastructure-failure rate
- proof-reuse opportunity and overlap with the held-out target.

Target match, semantic reward integrity, verified feature coverage,
reliability, and cost are the current evidence-backed measurement families.
Any fitted selector must compete with uniform allocation, starting success,
mixed success, and a competent source-native heuristic.

### 4. Freeze one prospective selection test

Before downstream outcomes are opened, freeze:

- the candidate memberships and overlap report
- held-out repositories and protected capabilities
- target vector and smallest effect of interest
- starting checkpoint, trainer, seeds, checkpoints, and compute budget
- selection and abstention rule
- baselines, uncertainty method, and scoring code.

The primary outcome is allocation regret at matched interaction cost. Pairwise
ordering, curve error, calibration, machine-checked completion, and completion
per token are supporting outcomes.

### 5. Forecast regressions along training

Evaluate common checkpoints on a fixed held-out repository panel. Define a
regression before training as a task or protected capability that moves from a
prespecified acceptable state to an unacceptable state. Useful endpoints
include:

- solved-to-failed proof obligations
- lower strict pass rate across repeated attempts
- verifier success obtained through weaker specifications
- new timeouts or context failures
- losses in a protected proof language, repository family, or capability.

Fit behavior-only, static-structure-only, and combined predictors using only
information available before training. Evaluate them with leave-one-repository
or leave-one-library-out splits. Report average precision, top-risk recall,
Brier score, and calibration alongside a starting-performance baseline,
shuffled pairing, and random fingerprints. Tasks and checkpoints remain nested
within independently trained intervention arms.

### 6. Test production transfer

After a resolved repository-level result, qualify a bounded subset of the
public OSS Verify artifacts. Replay released proofs, validate the Rocq and
RISC-V semantics contract, and construct a small panel that varies proof
context or reuse while holding target entry points fixed. Measure proof
completion, token and verifier cost, patch integrity, and reuse. This test asks
whether the earlier selection and regression signals survive at binary level.

## Stop conditions

Do not begin downstream training when fewer than three candidates pass every
integrity gate, the starting policy is saturated or unsupported, measurements
are too unreliable, or the available budget cannot resolve a
decision-relevant effect. Treat infrastructure failure as invalid execution,
not reward zero. Report unresolved and negative results without changing the
target or candidate panel after outcomes are observed.

## Entry points

| Purpose | File |
| --- | --- |
| Workstream overview | [`README.md`](README.md) |
| Governing experiment protocol | [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) |
| Public source and evidence audit | [`SOURCE_LANDSCAPE.md`](SOURCE_LANDSCAPE.md) |
| Reproducible public results | [`public-evidence/`](public-evidence/README.md) |
| Vero source qualification | [`VERO_SOURCE_QUALIFICATION.md`](VERO_SOURCE_QUALIFICATION.md) |
| Vero policy-measurement contract | [`STARTING_POLICY_PROBE.md`](STARTING_POLICY_PROBE.md) |
| Vero executable pipeline | [`../../../data/formal-verification/vero/`](../../../data/formal-verification/vero/README.md) |
| OSS Verify adapter | [`../../../data/formal-verification/oss-verify/`](../../../data/formal-verification/oss-verify/README.md) |
