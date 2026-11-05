# Formal-verification source landscape

**Audit date:** 2026-11-03

This document records public evidence relevant to the formal-verification
environment-utility study. It distinguishes benchmark relevance from executable
environment readiness. Counts and capabilities are source-specific and should
not be combined without preserving their contracts.

## Corrections to the initial project premise

Two corrections are necessary before experiment design:

1. The current VeriBench launch draft reports **884** paired Python-to-Lean
   tasks: a 602-task canonical core and a 282-task high-assurance expansion. It
   does not report 896 tasks.
2. Cryptographic formal-verification benchmarks now exist. CrypFormBench covers
   700 instances over seven formal languages, CryptoFormalEval studies
   Tamarin-guided protocol-vulnerability analysis, and dalek-lean-bench exposes
   historical repository-scale Lean proof tasks for curve25519-dalek. The open
   opportunity is therefore not "the first cryptography benchmark." It is a
   rigorous environment-utility study with realistic repository state,
   policy-relative measurements, and downstream training outcomes.

## Source-role table

| Source | Public evidence | Proposed role | Current blocker |
| --- | --- | --- | --- |
| VeriBench | Launch draft describes 884 Python-to-Lean tasks, a nine-part gold-artifact schema, security pairs, and a smooth conjunctive score | Held-out autoformalization target; possible candidate family after release qualification | The launch page's repository link currently returns 404; the task release, evaluator, license, and immutable revision must be obtained and pinned |
| VCVio | Apache-2.0 Lean library for cryptographic games, primitives, protocols, implementations, oracle semantics, probability, and program logic | Leading cryptographic training-environment candidate; historical repository tasks; proof-reuse and curriculum studies | Must reconstruct gold historical tasks without future-lemma leakage; existing unresolved `sorry` declarations are not gold outcomes |
| dalek-lean-bench | 249-theorem history, 146 theorem--proof pairs, chronology-aware proof injection, and a real Rust-to-Lean verification repository | Independent cryptographic target/candidate and validation of the historical-task builder | Must pin an immutable release and audit task identities, source licenses, and agent harness |
| VeriSoftBench | 500 Lean tasks from 23 repositories with project and local dependencies | Repository-scale external target and possible disjoint candidate family | Pin code/data and verify that training and evaluation repositories can be separated without dependency leakage |
| Vero | Multi-module Lean repository construction benchmark | Repository-level external target | Pin released tasks, harness, and license; verify target isolation |
| FVSpec | 9,415 Lean challenges derived from 11,039 property-based tests from 333 repositories | Broad real-code specification/proof candidate; source of scalable task diversity | Audit translation quality, source-license propagation, repository grouping, and specification validity |
| Anthropic/Theorem OSS Verify | Public Rocq statements and proofs for compiled RISC-V OSS-Fuzz targets plus Linux-process semantics | Primary frontier reference; bounded source candidate; later external transfer target; source of hypotheses about proof reuse, test-to-spec conversion, and cost | Different proof assistant and machine model; proof generation can require millions of tokens; public subset is not the entire reported study |
| CrypFormBench | 700 instances, 677 schemes, seven verifier languages, five task types, 160 properties | Cryptography landscape and multi-tool diagnostic | Composite scores and heterogeneous verifier languages are not directly comparable to Lean repository utility |
| CryptoFormalEval | Manually validated flawed protocols with Tamarin interaction | Symbolic-protocol diagnostic | Symbolic protocol analysis is a different target from Lean proof development and computational-security reductions |

## VeriBench

The public launch draft treats autoformalization as more than compilation. It
separates executable behavior, preconditions, property theorems, bundled
correctness, and implementation equivalence. Its evaluation combines:

- successful Lean compilation
- nontrivial formal content
- absence of unresolved proof placeholders
- semantic coverage of a human-curated gold specification.

That is a useful held-out target because an agent can produce compiling Lean
that states the wrong or incomplete property. The security subset also includes
paired safe and unsafe programs, which can test whether a generated
specification discriminates the intended safety condition.

The source also reports an important limitation: human/judge agreement on
theorem coverage is imperfect, and the gold corpus reports residual maturity
issues. The evaluator must therefore be independently qualified. A target score
should retain its compilation, proof-completeness, and semantic-coverage
components rather than relying on one scalar.

**Admission decision:** target candidate only until the repository, evaluator,
license, task identities, and revision are publicly available and pinned.

## VCVio

VCVio was inspected at commit
`cc6ae6cc39c1cca024d292262f90880b551fb2b3` (2026-11-02), under Apache-2.0.
Its repository exposes a much richer environment than isolated theorem
completion:

- monadic oracle computations and probabilistic semantics
- relational and unary program logics
- reductions and query-bound reasoning
- signatures, encryption, Sigma protocols, Fiat--Shamir, and Fischlin
- ML-DSA, ML-KEM, Falcon, and SLH-DSA developments
- examples, test libraries, CI, axiom accounting, and agent-facing proof guides.

VCVio is suitable for environment research because it supplies repository
context, reusable lemmas, machine checking, multiple cryptographic mechanisms,
and realistic proof-maintenance workflows. It is **not** immediately suitable
for claim-bearing RL by simply replacing arbitrary proofs with `sorry`:

- randomly masked theorems can leak through later lemmas
- source files include intentional unresolved definitions or proofs
- compilation alone can reward vacuous statements or forbidden axioms
- neighboring tests and examples can reveal target structure
- dependency and proof-reuse structure is central to the task.

The preferred task construction is historical replay:

1. identify a commit that introduces or completes a theorem
2. reconstruct the repository state immediately before the proof
3. preserve only definitions and lemmas available at that time
4. remove the target proof while freezing its statement
5. store the later accepted proof as hidden gold evidence
6. verify that the task builds with the gold proof and fails the no-op
7. group tasks by originating change and dependency component.

Existing unresolved holes may become open research tasks, but cannot provide a
supervised success label until an independently accepted proof exists.

**Admission decision:** source-qualified candidate; historical task extraction
and harness-integrity validation required before warm-start measurement.

## Anthropic and Theorem: production-scale assembly verification

Anthropic reports proofs for 239 entry points across 123 OSS-Fuzz libraries in
its broader effort. The public `theorem-labs/oss-verify-proofs` repository is a
smaller released subset and should be described by its own manifest. At the
time of this audit, the public repository reports:

- 61 entry points in 26 libraries with published proofs
- 2,148 fuzz-target statement groups from 427 buildable projects
- 337 proved statements and a much larger open statement set
- exact RISC-V binaries, build provenance, hashes, Rocq checker versions, and
  Linux-process semantics.

The work suggests three environment axes worth testing:

1. **Specification source:** expert theorem, extracted implementation contract,
   or developer-written test converted into a universal property.
2. **Proof reuse:** isolated proof attempts versus a shared library of previously
   established proof components. Anthropic reports that shared workspaces
   reduced token use in its 36-task study.
3. **Repository realism:** isolated proof holes versus full build, semantics,
   and dependency context.

It also demonstrates why "machine checked" is not synonymous with "bug free."
The claim is relative to a specification, semantics, assumptions, covered entry
points, and trusted checker. Those fields belong in every environment record.

**Admission decision:** primary frontier reference and design evidence. Its
public open statements may enter a bounded source-qualification study after the
checker, cost, reset, license, and task-identity contracts are pinned. It also
remains a later external transfer target. Do not pool its Rocq rewards with
Lean rewards, and do not use the unreleased portion of the reported study as if
it were public data.

## Cryptographic benchmarks and novelty

### dalek-lean-bench

This is the closest public precedent for the proposed VCVio task builder. It
replays the order in which proofs were completed in a real curve25519-dalek
verification repository. Earlier proofs remain available, while the target and
future proofs are replaced. Its public artifacts report 249 timeline entries
and 146 recovered theorem--proof pairs.

### CrypFormBench

CrypFormBench spans symbolic and computational verification across seven
languages. It is useful for measuring interpretation, generation, completion,
transformation, and correction, but its aggregate score is not an RL reward for
one common executable environment.

### CryptoFormalEval

CryptoFormalEval pairs language models with Tamarin to identify flaws in
cryptographic protocols. It is valuable for a later symbolic-protocol track,
but should remain separate from computational game proofs and implementation
verification.

The defensible contribution is therefore:

> a controlled, policy-relative study of which production-formal-verification
> environment distributions improve held-out verification capability at fixed
> interaction compute, including a repository-scale cryptographic domain.

## Sources

- VeriBench launch draft: <https://ehersch.github.io/veribench-blog/>
- VCVio: <https://github.com/Verified-zkEVM/VCVio>
- dalek-lean-bench: <https://github.com/Beneficial-AI-Foundation/dalek-lean-bench>
- Anthropic formal-verification report:
  <https://www.anthropic.com/research/formal-verification>
- Public OSS Verify proofs: <https://github.com/theorem-labs/oss-verify-proofs>
- Public RISC-V/Linux semantics:
  <https://github.com/theorem-labs/rocq-linux-process-semantics>
- VeriSoftBench: <https://utopia-group.github.io/VeriSoftBench/>
- Vero: <https://vero.verina.io/>
- FVSpec: <https://fvspec.galois.com/>
- CrypFormBench: <https://arxiv.org/abs/2606.25561>
- CryptoFormalEval: <https://arxiv.org/abs/2411.13627>
