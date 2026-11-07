# Predictable utility of formal-verification environments

**Status:** the OSS Verify release indexes and checker bootstrap are qualified.
Vero's source structure, pinned Lean runtime, reference build, bounded grader
controls, and repository-disjoint split are also qualified. OSS Verify proof
replay and both sources' model-facing policy qualification remain pending. No
claim-bearing reinforcement-learning run is authorized.

This workstream asks a narrower question than benchmark construction:

> For a fixed starting policy, target, tool contract, and interaction budget,
> which formal-verification training environment is expected to produce the
> greatest held-out improvement, and when is the evidence too weak to choose?

The immediate objective is a reproducible comparison of executable environment
families, not a claim that one benchmark, proof assistant, or task distribution
is universally best. The long-term scientific objective is to learn which
policy-relative properties of a verification environment predict downstream
utility before full training is run.

The detailed protocol is in [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md). The dated
source assessment and role of each public artifact are in
[SOURCE_LANDSCAPE.md](SOURCE_LANDSCAPE.md). The fields required before a source
can be admitted are listed in
[source-registry.template.yaml](source-registry.template.yaml). The first
completed source-index audit is recorded in
[SOURCE_QUALIFICATION.md](SOURCE_QUALIFICATION.md), with its reproducible
[adapter](../../../data/formal-verification/oss-verify/README.md). The
repository-level Vero audit is recorded separately in
[VERO_SOURCE_QUALIFICATION.md](VERO_SOURCE_QUALIFICATION.md). The frozen
development measurement and its remaining containment gates are recorded in
[STARTING_POLICY_PROBE.md](STARTING_POLICY_PROBE.md).

## Why this workstream is timely

Formal verification is moving from isolated theorem proving toward production
software workflows:

- [VeriBench](https://ehersch.github.io/veribench-blog/) evaluates end-to-end
  Python-to-Lean formalization, including compilation, nontrivial formal
  content, and semantic coverage of a human-curated target.
- [VeriSoftBench](https://utopia-group.github.io/VeriSoftBench/) and
  [Vero](https://vero.verina.io/) emphasize repository context rather than
  isolated theorem statements.
- [VeriContest](https://github.com/HIPREL-Group/VeriContest) separates
  specification, implementation, proof, and end-to-end generation in native
  Verus and Dafny environments.
- [FVSpec](https://fvspec.galois.com/) turns real property-based tests into
  Lean challenges drawn from hundreds of open-source repositories.
- Anthropic and Theorem's
  [assembly-level verification effort](https://www.anthropic.com/research/formal-verification)
  demonstrates a production-scale workflow over OSS-Fuzz libraries and releases
  a subset of its Rocq statements, proofs, RISC-V binaries, and Linux-process
  semantics.
- [VCVio](https://github.com/Verified-zkEVM/VCVio) and
  [dalek-lean-bench](https://github.com/Beneficial-AI-Foundation/dalek-lean-bench)
  expose realistic cryptographic proof development in Lean.

These sources do not define one interchangeable task pool. They differ in
proof assistant, specification source, repository context, trusted computing
base, reward surface, and target capability. Those differences are part of the
scientific problem and must remain explicit.

## One program, multiple environment families

The reference is the production workflow demonstrated by Anthropic and
Theorem: start from real software, construct an executable formal claim, use an
agent inside a full proof-development environment, and obtain a
machine-checkable guarantee whose assumptions and trusted components are
explicit. The research question is which training experiences most efficiently
improve that capability.

The initial public sources are different environment families within that one
program:

- Anthropic/Theorem's OSS Verify artifacts supply the most frontier-relevant
  production workflow: fuzz-test-to-spec conversion, compiled binaries,
  machine semantics, very long proofs, and reusable proof components.
- VeriBench supplies a smaller end-to-end autoformalization setting in which
  specification quality and theorem coverage can be measured directly.
- VeriSoftBench, Vero, and FVSpec supply repository context and real-code proof
  obligations at a more tractable scale.
- VeriContest supplies a later cross-tool target for verified Rust and Dafny
  generation, with positive and mutated-negative tests for specification
  completeness.
- VCVio and the historical curve25519-dalek corpus supply a high-assurance
  cryptographic environment family, where the software properties involve
  implementations, games, protocols, reductions, and probabilistic reasoning.

Cryptography is therefore a domain slice of production formal verification,
not a separate research project. Native verifier outputs remain separate in
the data layer so that Lean compilation, Rocq proof checking, and symbolic
protocol analysis are not mistaken for one numerical reward. They meet at the
decision layer through typed validity, policy response, cost, reliability,
target improvement, and allocation regret.

## What counts as an environment

A claim-bearing environment includes more than a collection of theorem
statements. Its record must freeze:

1. task identities and source revision
2. initial repository state and dependency closure
3. agent-visible files and tools
4. action and observation interface
5. build, proof-check, and timeout contract
6. reward components and invalid-output rules
7. reset and sandbox behavior
8. sampling or mixture weights
9. starting policy and decoding contract
10. generated-token or equivalent interaction budget.

The transition function includes file edits, tool calls, compiler or proof-state
feedback, and repository state. A rollout may contain many actions. A
"pre-RL measurement" is a frozen-policy rollout under this environment, not a
one-token trajectory and not an optimizer step.

## Scientific object

For environment distribution $E$, starting policy $\pi_0$, fixed budget
$C$, and target vector $D$, define

$$
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D).
$$

The target vector keeps distinct:

- machine-checked completion
- specification or theorem coverage
- absence of `sorry`, unapproved axioms, and vacuous claims
- transfer to disjoint repositories or domains
- retained performance on protected capabilities
- generated tokens, wall time, and verifier cost.

The primary decision metric is allocation regret relative to the best admissible
candidate under the frozen target vector. Predictive error, pairwise ordering,
calibration, risk--coverage, and cost are supporting metrics.

## Governing constraints

- Candidate construction may not inspect claim-bearing downstream outcomes.
- Historical proofs may be used only with a chronology-correct snapshot that
  removes future lemmas and target proofs.
- A compiling file is not automatically a correct solution.
- `sorry`, unapproved axioms, theorem-statement edits, weakened specifications,
  and hidden access to reference proofs must be rejected.
- Infrastructure failures are missing/invalid observations, never reward zero.
- Raw scores from different proof assistants or harnesses are not pooled.
- Random theorem splits are insufficient when tasks share repositories,
  dependencies, or proof templates.
- No RL is authorized until source, license, containment, reset, oracle, no-op,
  and reward-integrity gates pass.

## Immediate deliverables

1. Pin every admitted source and record its license and content manifest. The
   OSS Verify `v2026.11.1` index and checker metadata are complete. Vero's
   source structure, bounded runtime qualification, and repository split are
   complete.
2. Recover chronology-correct historical tasks from VCVio and validate the
   existing dalek-lean-bench construction.
3. Obtain and pin a public VeriBench release before creating any benchmark split.
4. Implement a common environment record without erasing native verifier
   semantics. The OSS Verify source adapter now preserves statement status,
   revision, fingerprint, entry-point grouping, and checker identity. The Vero
   adapter preserves repository, module, API, specification, source revision,
   trusted-axiom, and license boundaries.
5. Run oracle, no-op, statement-mutation, `sorry`, axiom, reset, and containment
   tests. The bounded OSS Verify and Vero controls are complete; selected
   production-task replay and model-facing controls remain.
6. Perform a bounded frozen-policy qualification pass.
7. Freeze candidate environments, predictions, uncertainty, and an a-priori
   power/cost decision before any downstream training outcome is opened.

Until those deliverables are complete, the Anthropic/Theorem workflow remains
the frontier reference, its public release is a source-qualified candidate
pending proof replay and selected-harness qualification, Vero is a
runtime-qualified repository candidate pending policy measurement, VCVio is a
promising high-assurance source candidate, and VeriBench is a narrower target
candidate. None is yet a validated RL environment in this workstream.
