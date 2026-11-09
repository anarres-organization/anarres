# Formal-verification continuation guide

**Status date:** 2026-11-09

The next scientific milestone is a development screen under a tightened task
sandbox, followed by a prospective comparison of qualified formal-verification
environments and checkpoint-level regression forecasting. This guide records
the current evidence boundary and the order in which the remaining work should
proceed.

## Current state

The workstream has four completed foundations:

1. The [public-evidence record](public-evidence/README.md) reconstructs
   decisions from VeruSyn, Re:Form, Formal Disco, and Vericoding. It also
   records the production target established by Anthropic and Theorem.
2. The OSS Verify adapter preserves statement, source, checker, and entry-point
   identities. Vero has a pinned source revision, repository-disjoint split,
   fresh grader, lifecycle controls, and a completed 32-attempt development
   queue.
3. The Vero starting-policy measurement reached fresh grading for every queue
   identity without infrastructure errors. It found zero strict successes
   across 2,776 specification trials, giving zero usable signal density and
   zero effective coverage in both proof modes. The preregistered support gate
   failed, so the result does not rank environments or authorize training.
4. The development-only budget ladder tested the same Leanstral policy at
   200,000 and 1 million exported tokens. The larger budget increased tool use
   and proof drafting but produced no valid scored slot. Leanstral is rejected
   for this Vero contract, and the unopened partitions remain protected.
5. GPT-5.6 Sol with Codex 0.154.0 passed all nine PrimePy proof specifications
   in one excluded development attempt. Vero rebuilt only the editable slots
   in a fresh grader, with no failed, unfilled, tainted, or unapproved-axiom
   result. The attempt establishes policy support but not reliability.
6. The post-run containment audit found that generic upstream Lean guidance
   was readable and a temporary write outside the rendered task was possible.
   No reference proof or protected repository was accessed. Repeated
   measurement remains blocked until the sandbox matches the intended boundary.

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

### 1. Tighten containment and run the development screen

The v5 Leanstral measurement and its budget-ladder follow-up are complete and
remain unchanged. Their compact
[result record](../../../data/formal-verification/vero/results/development-policy-measurement.v1.json)
and [calibration result](../../../data/formal-verification/vero/results/development-budget-calibration.1m-v1.json)
preserve the frozen inputs and outcomes. The next qualification must use a new
policy, a new protocol version, and development repositories only.
The [requalification design](POLICY_REQUALIFICATION.md) fixes the evidence,
budget ladder, and stop rules that govern that revision.
The [starting-policy selection](STARTING_POLICY_SELECTION.md) audits the
released Vero, VeriSoftBench, and LeanLean evidence and selects GPT-5.6 Sol
through Codex 0.154.0. The resulting one-attempt
[qualification result](../../../data/formal-verification/vero/results/development-policy-qualification.codex-sol-v1.json)
passes all nine PrimePy specifications under fresh grading.

- Preserve the GPT-5.6 Sol model, Codex 0.154.0 harness, xhigh reasoning
  setting, native repository interface, and 90-minute Vero budget.
- Restrict task reads and writes to the freshly rendered workspace while
  keeping controller authentication outside the artifact and fresh grader.
- Re-run the containment negatives before any new model attempt.
- Freeze a small development-only screen across repositories and proof modes.
  Exclude its outcomes from later environment comparisons.
- Keep qualification and prospective repositories unopened until the screen
  establishes nonzero strict coverage in at least two development repositories.

This stage establishes whether the supported policy and tightened interface
produce measurable coverage beyond one excluded task. It cannot revise the v5
outcome or convert either qualification into a candidate comparison.

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
| Completed Vero development result | [`development-policy-measurement.v1.json`](../../../data/formal-verification/vero/results/development-policy-measurement.v1.json) |
| Vero policy requalification | [`POLICY_REQUALIFICATION.md`](POLICY_REQUALIFICATION.md) |
| GPT-5.6 Sol qualification result | [`development-policy-qualification.codex-sol-v1.json`](../../../data/formal-verification/vero/results/development-policy-qualification.codex-sol-v1.json) |
| Vero executable pipeline | [`../../../data/formal-verification/vero/`](../../../data/formal-verification/vero/README.md) |
| OSS Verify adapter | [`../../../data/formal-verification/oss-verify/`](../../../data/formal-verification/oss-verify/README.md) |
