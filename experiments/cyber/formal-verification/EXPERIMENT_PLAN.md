# Formal-verification environment-utility protocol

**Protocol status:** draft for source qualification. This document does not
authorize model training.

## 1. Decision and claim

The first decision is whether any qualified pre-RL measurement set can rank
three or more formal-verification environment distributions better than a
competent practical heuristic under a fixed starting model, target, and
interaction budget.

The strongest claim available from a successful first study is:

> On a frozen held-out target, policy-relative measurements improved candidate
> ordering or reduced allocation regret relative to prespecified practical
> baselines for this model, harness, and environment panel.

The first study cannot establish a universal scaling law, generalization to all
proof assistants, or utility across arbitrary model families.

## 2. Scope

### Included

- Lean 4 environments with executable, kernel-checked outcomes
- end-to-end autoformalization and repository-context proof completion
- a high-assurance cryptographic environment family based on VCVio and
  dalek-lean-bench;
- held-out evaluation on disjoint tasks, repositories, or chronological proof
  states;
- source, policy, cost, verifier, and infrastructure provenance
- outcome-blind prediction and abstention.

### Deferred

- translating TerminalBench tasks into new formal specifications
- pooling Lean, Rocq, Verus, Dafny, Tamarin, or ProVerif reward values
- training on the unreleased portion of any reported study
- unrestricted execution of generated code
- claiming semantic correctness from compilation alone
- large-scale RL before a bounded information and power analysis.

## 3. Unit of analysis

The independent intervention unit is one environment distribution trained from
one immutable starting checkpoint under one frozen recipe and budget. Tasks,
rollouts, attempts, checkpoints, and target dimensions are nested observations,
not independent interventions.

An environment distribution is defined by a manifest of task identities and
sampling weights plus its complete runtime contract. Two distributions that
share tasks but change weights are distinct interventions and must preserve
their overlap.

## 4. Task construction

### 4.1 Historical repository tasks

Use chronology-correct tasks where an accepted proof or implementation exists:

1. pin the repository and dependency revisions
2. identify the change that completed the target
3. materialize the immediately preceding valid repository state
4. freeze the target statement or specification
5. remove the target implementation/proof
6. remove or mask future lemmas and downstream references
7. retain the accepted change as hidden gold
8. run build, oracle, no-op, and leakage tests
9. assign one stable task id from source repository, revision, declaration, and
   normalized goal hash.

The originating commit or pull request is the grouping unit when it contributes
multiple related declarations.

### 4.2 Autoformalization tasks

For Python-to-Lean tasks, keep the source program, natural-language context,
toolchain, and target schema frozen. The agent may construct an implementation,
specification, and proof, but may not inspect the gold artifact or semantic
coverage labels. Safe/unsafe pairs stay in the same partition.

### 4.3 Open proof obligations

Tasks without accepted gold proofs are allowed only in an exploratory pool.
They cannot contribute supervised utility or benchmark accuracy until an
independent review and repository acceptance establishes the target.

## 5. Partitioning and leakage control

Random row splitting is prohibited. Apply all relevant grouping constraints:

- repository
- originating commit or pull request
- cryptographic primitive or protocol family
- dependency component
- safe/unsafe pair
- source program and translated variants
- near-duplicate goal or proof skeleton
- chronological boundary.

Create three layers:

1. **development:** harness construction and measurement debugging
2. **qualification:** candidate admission and frozen-policy measurements
3. **prospective target:** unopened until candidate predictions, uncertainty,
   and the training protocol are frozen.

Target tasks may not appear in training, retrieval corpora, demonstrations, or
proof-reuse libraries.

## 6. Reward and validity contract

### 6.1 Validity gate

A rollout is infrastructure-valid only if the container starts, the pinned
repository materializes, tools respond, the time budget is applied, and the
checker terminates with a typed result. Infrastructure-invalid rollouts remain
missing and are retried under the frozen retry rule.

### 6.2 Required rejection tests

The grader must reject:

- unchanged no-op submissions
- target statements modified or deleted
- `sorry`, `admit`, or equivalent placeholders
- new unapproved axioms or unsafe declarations
- reference-proof access
- imports from future or target-only modules
- vacuous weakenings of the specification
- modifications outside the allowed workspace
- cached build artifacts that survive reset
- verifier crashes presented as task failure.

### 6.3 Native outcome vector

Retain separate components:

- checker success
- target declaration proved
- approved-axiom audit
- specification/theorem coverage
- safe/unsafe discrimination where applicable
- tests and repository build
- protected-target retention
- token, tool-call, wall-time, and memory cost.

A scalar training reward may be derived only after these components are logged.
The target evaluation continues to report the full vector.

## 7. Candidate environment panel

Construct candidates only after the task sources pass qualification. The first
panel should contain three to six mechanistically distinct distributions, not
many arbitrary random mixtures. Candidate axes include:

1. **isolated proof completion:** theorem plus minimal local context
2. **repository-context completion:** full chronology-correct dependency state
3. **specification plus proof:** end-to-end formalization rather than a supplied
   statement;
4. **cryptographic repository:** VCVio or curve25519-dalek tasks
5. **proof-reuse curriculum:** access to an allowed library of previous,
   training-only proofs versus isolated attempts;
6. **policy-gap weighting:** tasks weighted by frozen-policy failure structure
   instead of uniformly.

Do not include an axis unless its task counts, overlap, difficulty support, and
runtime cost allow a compute-matched comparison.

## 8. Pre-RL measurement set

Run the starting policy without updating weights. Use repeated attempts and
common random numbers where the agent contract permits them. The repetition
count is set by a prospective reliability and cost simulation.

### Policy-response features

- strict checker success rate
- valid-output and compilation rate
- mixed-success fraction across attempts
- reward entropy and between-attempt disagreement
- proof-state progress or goals closed, when deterministically available
- specification-coverage components
- error taxonomy: parse, elaboration, missing dependency, tactic failure,
  timeout, invalid axiom, and semantic-coverage failure;
- truncation, context overflow, tokens, tool calls, and wall time.

### Static and structural features

- proof assistant and toolchain revision
- statement, implementation, and repository-context size
- dependency-graph depth and fan-out
- imported/local lemma counts
- task family and cryptographic primitive
- historical proof length and build cost, available only for development and
  training tasks;
- proof-template and source similarity
- target-alignment features computed without target outcomes.

### Reliability features

- repeated-reset agreement
- checker determinism
- fixture/oracle pass rate
- infrastructure-failure rate
- reward sensitivity to statement weakening and forbidden placeholders.

No feature may be selected because it correlates with unopened prospective
outcomes.

## 9. Baselines and models

Fit the smallest ladder consistent with the number of independent
interventions:

1. uniform allocation
2. environment size and generated-compute baselines
3. starting success/headroom heuristic
4. mixed-success or reward-information heuristic
5. regularized linear or pairwise ranking model
6. hierarchical model with repository, policy, and verifier effects.

Content or dependency encoders may be evaluated as frozen representations, but
neural capacity is promoted only if it improves held-out allocation decisions
across independent repository or policy groups and survives shuffled-pairing and
missingness controls.

## 10. Downstream utility experiment

Training is conditional on every prior gate passing.

- Use one starting checkpoint, one agent scaffold, one optimizer, and one
  generated-token budget across candidates.
- Count actual generated tokens and tool/computation cost; update count alone is
  not a compute measure.
- Use at least two training seeds only when the prospective power analysis shows
  that they can resolve the smallest effect of interest.
- Evaluate common checkpoints on the same held-out tasks.
- Keep proof-assistant-native outcomes separate.
- Preserve the incumbent/uniform environment and the competent practical
  heuristic even if early curves favor another candidate.
- Do not select the final checkpoint after seeing target performance.

The first pilot should use one model scale. Replication across a second model
family or scale is a later claim gate, not a reason to make the first pilot
intractable.

## 11. Evaluation

### Primary

- allocation regret on the held-out target vector
- pairwise environment ordering
- success of the frozen selection or abstention rule.

### Secondary

- utility-curve RMSE and rank correlation
- calibration and risk--coverage
- protected-capability regressions
- information gained per generated token and wall-clock hour
- performance versus the starting-success heuristic
- transfer across repository, primitive, policy, and model scale.

Task-level bootstrap intervals quantify fixed-panel evaluation noise. Training
seeds are the outer unit for training variability. Nested tasks or checkpoints
must not be counted as independent training interventions.

## 12. Gates and stop rules

Stop before RL if any of the following holds:

- fewer than three candidate distributions pass all integrity gates
- the public VeriBench release or another target cannot be pinned
- gold-task reconstruction leaks future proofs or target artifacts
- oracle/no-op/reset/axiom tests fail
- infrastructure failures exceed the prospectively frozen limit
- the starting policy is saturated or has no mixed-success support
- frozen-policy measurements are too unreliable
- the projected pilot cannot detect a decision-relevant effect within the
  compute budget;
- candidate distributions differ primarily in infrastructure rather than
  scientific treatment.

After RL, report a negative or unresolved result rather than widening the claim,
changing the target, or adding model capacity post hoc.

## 13. Execution phases

### Phase 0: source and license freeze

- Obtain the public VeriBench release.
- Pin VCVio, dalek-lean-bench, VeriSoftBench, Vero, FVSpec, and any admitted
  source at immutable revisions.
- Record licenses separately for code, tasks, generated artifacts, and upstream
  repositories.
- Produce content hashes and a source registry.

**Exit:** every admitted byte has an identity, license, role, and revision.

### Phase 1: task builders

- Implement chronology-correct VCVio extraction.
- Reproduce dalek-lean-bench task generation.
- Implement benchmark-specific adapters without forcing native rewards into one
  scalar schema.

**Exit:** deterministic manifests reproduce byte-identically.

### Phase 2: harness qualification

- Run oracle, no-op, forbidden-placeholder, axiom, statement-mutation,
  future-import, reset, timeout, and containment tests.
- Separate infrastructure failures from scientific failures.

**Exit:** all admitted fixtures pass every required gate.

### Phase 3: frozen-policy measurement

- Freeze policy, scaffold, decoding, tools, and attempts.
- Measure a development subset, then a disjoint qualification subset.
- Estimate reliability, support, cost, and candidate feasibility.

**Exit:** at least three informative candidates and an a-priori pilot budget.

### Phase 4: prediction and power freeze

- Freeze the target split and candidate panel.
- Fit practical baselines using development/qualification data only.
- Freeze rankings, uncertainty, abstention, smallest effect of interest, seeds,
  checkpoints, and analysis code.

**Exit:** signed run/no-run decision.

### Phase 5: bounded utility pilot

- Execute only the frozen candidates and budget.
- Score only after all required arms are complete.
- Publish outcomes, failures, costs, and regret with exact provenance.

### Phase 6: replication

Only after a resolved first result, test one additional model family/scale or
one disjoint repository family. A general scaling claim requires multiple
independent interventions across both axes.

## 14. Frontier-reference role of assembly verification

The Anthropic/Theorem workflow is the program's reference because it applies
formal verification to compiled production software, makes the specification
and trusted machine semantics explicit, and exposes the cost and proof-reuse
structure of real proof development. Its public artifacts should first undergo
a bounded source-qualification study because they use Rocq over compiled
RISC-V binaries and Linux-process semantics rather than the more tractable Lean
environments used for initial iteration.

After source qualification, the public open statements can contribute a small
candidate environment and the proved subset can provide oracle and replay
tests. The same source remains a later external target for whether environment
selection principles transfer to:

- test-to-spec conversion
- very long proofs
- shared-proof workspaces
- binary-level semantics
- properties whose validity is conditional on a large trusted model.

The broader results described in the report are not released task data. Only
the published statements, proofs, semantics, binaries, and manifests may be
used.

Converting arbitrary terminal-agent tasks into formal-verification tasks is not
the next step. Specification construction is itself a major scientific and
human-validation problem. Existing machine-checked repositories should be used
before inventing a new benchmark.

## 15. Required public artifacts

- immutable source registry
- task and partition manifests
- license and contamination audit
- harness-integrity test report
- frozen-policy measurement schema and summary
- candidate-panel and overlap report
- prediction and power freeze
- run receipts and typed failure record
- regenerable decision metrics and plots
- bounded conclusion with explicit unsupported claims.
