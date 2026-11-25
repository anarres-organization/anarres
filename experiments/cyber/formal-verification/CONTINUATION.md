# Formal-verification continuation guide

**Status date:** 2026-11-25

The next scientific milestone is a prospective comparison of qualified
formal-verification environments under a trainable starting policy, followed
by checkpoint-level regression forecasting. This guide records the current
evidence boundary and the order in which the remaining work should proceed.

## Current state

The workstream has eight completed foundations:

1. The [public-evidence record](public-evidence/README.md) reconstructs
   decisions from DafnySynth, VeruSyn, Re:Form, Formal Disco, and Vericoding.
   DafnySynth provides the densest positive grid: verifier-filtered synthetic
   augmentation improves seven of eight matched paper comparisons and ties the
   eighth across two starting models and four human-data fractions. The record
   also preserves the production target established by Anthropic and Theorem.
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
   No reference proof or protected repository was accessed. The task-only
   execution boundary closed that gap before the repeated measurement ran.
7. The public Forall VeriSoftBench release identifies a nondegenerate policy
   boundary under GPT-5.6 Sol at xhigh reasoning through Codex. Fifteen of its
   100 tasks are first solved on samples 2--6 under a Pass@8 contract, so each
   has at least one unsuccessful sample before a successful sample for the same
   policy and task. These tasks span five real Lean repositories.
8. GPT-5.6 Sol completed the frozen 32-attempt Vero development measurement
   across four repositories and two modes. Thirty-one attempts were scored and
   one had an integrity failure; no run had an infrastructure failure. The
   released measurement contains 1,653 strict successes across 2,776 trials,
   passes the frozen support and readiness gates, and yields positive usable
   signal density and effective coverage in both modes. It qualifies the
   measurement regime but does not rank environments or authorize training.

No claim-bearing reinforcement-learning run has begun. Qualification and
prospective repositories remain unopened.

## Collaborator handoff

The completed Leanstral and GPT-5.6 Sol outcomes are immutable evidence. Do not
rerun them under the same identities, edit their frozen contracts, or treat the
PrimePy result as an estimate of reliability. The repository split also remains
fixed. Development repositories may be used for the next screen; qualification
and prospective repositories must remain unopened.

The immediate work has three phases:

1. **Release preservation.** Keep the completed GPT-5.6 Sol measurement and its
   v2 protocol, queue, authorization, receipts, and manifest immutable. The
   [freeze-history record](../../../data/formal-verification/vero/repeated-measurement-freeze-history.json)
   preserves the two corrections made to v1 before its first attempt.
2. **Trainable-policy qualification.** Choose a trainable starting policy and
   qualify it under the same task-only workspace, fresh grader, strict reward,
   and repeated-measurement contract. Keep infrastructure, integrity, and task
   outcomes separate. The policy must produce nondegenerate support before any
   candidate comparison is designed.
3. **Prospective candidate freeze.** Construct three to six distinct training
   environments, freeze their memberships and costs, and serialize predictions
   before matched training outcomes are opened. Qualification and prospective
   repositories remain protected until the new protocol explicitly opens them.

The first collaborator deliverables are therefore a trainable-policy
qualification protocol, one route-qualification receipt, and a prospective
candidate-panel proposal. The selected route must freeze the exact policy,
harness, workspace, network, credential, reset, and checker boundaries before
model execution. Containment artifacts remain infrastructure evidence rather
than scientific outcomes.

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

### 1. Qualify a trainable starting policy

The v5 Leanstral measurement and its budget-ladder follow-up are complete and
remain unchanged. Their compact
[result record](../../../data/formal-verification/vero/results/development-policy-measurement.v1.json)
and [calibration result](../../../data/formal-verification/vero/results/development-budget-calibration.1m-v1.json)
preserve the frozen inputs and outcomes. The
[requalification design](POLICY_REQUALIFICATION.md) fixes the evidence, budget
ladder, and stop rules that governed that revision.
The [starting-policy selection](STARTING_POLICY_SELECTION.md) used the released
Vero, VeriSoftBench, and LeanLean evidence to select GPT-5.6 Sol through Codex
0.154.0 for one excluded qualification. The resulting one-attempt
[qualification result](../../../data/formal-verification/vero/results/development-policy-qualification.codex-sol-v1.json)
passes all nine PrimePy specifications under fresh grading. The later repeated
measurement supersedes that one-attempt screen as evidence about GPT-5.6 Sol:
it passes the frozen support and readiness gates across all four development
repositories and both modes.

- Treat GPT-5.6 Sol as one supported and executable candidate rather than a
  required model. The public policy record shows that Opus 5 leads LeanLean
  compression, GPT-5.6 Luna has the lowest reported LeanLean cost, and GPT-5.5
  xhigh leads Vero repository completion.
- Nominate a small trainable-policy panel from released evidence, executable
  routes, cost, and reproducibility. Any candidate receives an excluded
  development qualification under the same Vero task and grader.
- Restrict task reads and writes to the freshly rendered workspace while
  keeping controller authentication outside both the model workspace and
  released evidence.
- Re-run the containment negative controls before a new model route is
  authorized. Emit a new protocol when a hash-pinned harness, checker, or
  boundary changes.
- Select the starting policy under a frozen rule, then preserve its checkpoint,
  harness, decoding, native repository interface, and interaction budget
  through candidate measurement and matched training.
- Keep qualification and prospective repositories unopened until the selected
  policy produces nonzero strict coverage in at least two development
  repositories and pooled success remains below the preregistered ceiling.

This stage establishes whether a trainable policy produces measurable support
under the qualified interface. It cannot revise either released starting-policy
measurement or convert development evidence into an environment comparison.

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

## Verification commands

From the repository root, collaborators should run:

```bash
python -m unittest \
  tests.integration.test_formal_verification_vero \
  tests.integration.test_formal_verification_vero_sandbox \
  tests.integration.test_formal_verification_release
python tools/check_repo_hygiene.py
python tools/check_prose_style.py
```

Before any public commit or archive, inspect the complete changed-file list and
exclude credentials, raw model traces, machine-specific paths, temporary
runtime state, and unreleased benchmark artifacts.

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
| Codex containment requalification | [`CODEX_CONTAINMENT.md`](CODEX_CONTAINMENT.md) |
| Vero executable pipeline | [`../../../data/formal-verification/vero/`](../../../data/formal-verification/vero/README.md) |
| OSS Verify adapter | [`../../../data/formal-verification/oss-verify/`](../../../data/formal-verification/oss-verify/README.md) |
