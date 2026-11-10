# Formal-verification source landscape

**Audit date:** 2026-11-10

This document records public evidence relevant to the formal-verification
environment-utility study. It distinguishes benchmark relevance from executable
environment readiness. Counts and capabilities are source-specific and should
not be combined without preserving their contracts.

## Corrections to the initial project premise

Three corrections are necessary before experiment design:

1. The VeriBench launch corpus reports **884** paired Python-to-Lean tasks. A
   separate, unmerged Harbor v1.3 candidate at commit `c9dfd8e3b535` contains
   **896** prove-first tasks. Versions 1.0 through 1.2 preserve the earlier
   study but instructed agents to insert `sorry` placeholders and used a
   compile-oriented success contract. Those versions cannot support a
   proof-completion claim, and the v1.3 candidate still requires release and
   evaluator qualification.
2. Cryptographic formal-verification benchmarks now exist. CrypFormBench covers
   700 instances over seven formal languages, CryptoFormalEval studies
   Tamarin-guided protocol-vulnerability analysis, and dalek-lean-bench exposes
   historical repository-scale Lean proof tasks for curve25519-dalek. The open
   opportunity is therefore not "the first cryptography benchmark." It is a
   rigorous environment-utility study with realistic repository state,
   policy-relative measurements, and downstream training outcomes.
3. Released studies already contain controlled formal-verification environment
   decisions. VeruSyn varies generated training data, Re:Form varies the RL
   reward environment, and Formal Disco varies verified-program generation.
   New computation should extend this evidence rather than restart from a
   benchmark-only premise.

## Source-role table

| Source | Public evidence | Proposed role | Current blocker |
| --- | --- | --- | --- |
| VeriBench | The launch corpus reports 884 paired tasks; an unmerged Harbor v1.3 candidate pins 896 prove-first tasks at `c9dfd8e3b535` | Held-out autoformalization target after a prove-first release is qualified | Qualify the task manifest, evaluator, container, semantic scorer, and licenses; do not use v1.0--v1.2 scores as proof success |
| VeruSyn | Controlled Part 1, Part 2, combined, teacher, and data-scale comparisons with VerusBench and VeruSAGE outcomes | Retrospective training-data decision panels and source of system-proof candidates | Public tables support compact decisions, but training-seed uncertainty and exact generation-token accounting are incomplete |
| Re:Form | Three Dafny RL reward environments across five model scales | Reward-integrity falsification and cross-scale environment evidence | Training-seed support is incomplete and the repository has no identified top-level license at the pinned revision |
| DafnySynth | Fixed-step augmentation comparisons over two starting models and four human-data fractions | Positive training-environment grid and source of annotation candidates | Released result JSONs omit the pure-synthetic arms and differ from several paper-table endpoints; both records must remain separate |
| Formal Disco | Specialized and monolithic generation systems, feature-entropy measurements, and matched downstream SFT results | Verified-diversity measurement and training-data comparison | Released run checkpoints and failed generations remain incomplete |
| ATLAS | Qwen2.5-Coder-7B gains 23 points on DafnyBench and 50 points on DafnySynthesis after training on more than 19,000 examples extracted from 2,700 verified programs | Independent positive evidence for verifier-filtered synthetic data | Public outcome summaries do not yet provide the crossed candidate grid needed for an allocation audit |
| InvBench | Fine-tuning and sampling comparisons measure invariant correctness and the resulting reduction in verifier runtime | Candidate source for utility definitions that include verification speed | No crossed candidate grid or released raw outcome set has yet been admitted for an allocation audit |
| LeanContext | Crossed training and inference views over 129,826 Lean targets; dependency prioritization improves Pass@32 by 1.40 and 1.70 points on two backbones | Controlled context-environment candidate and source of independently matched context panels | The repository releases construction and analysis code but not the model outcome files needed for an independent score audit |
| Vericoding | 55,397 model-task outcomes over 6,336 tasks, nine models, and three formal languages | Broad policy-support and cross-language diagnostic | Cross-model disagreement is not a repeated-policy measurement or downstream training outcome |
| LeanLean | Comparator-checked compression, cost, duration, checkpoints, and action summaries for six policies over 64 Lean repositories | Repository-level policy and cost screen before new inference | Compression is a different objective from filling Vero proof slots or closing a verified repository |
| Forall VeriSoftBench | 1,300 task records across 13 configurations on the 100-task Aristotle subset, with partial axiom-audit and independent-checker coverage | Policy, harness, reasoning-effort, and cost screen | Reported totals, retained artifacts, axiom audits, and independent checks have different coverage; proofs and transcripts are withheld |
| VCVio | Apache-2.0 Lean library for cryptographic games, primitives, protocols, implementations, oracle semantics, probability, and program logic | Leading cryptographic training-environment candidate; historical repository tasks; proof-reuse and curriculum studies | Must reconstruct gold historical tasks without future-lemma leakage; existing unresolved `sorry` declarations are not gold outcomes |
| dalek-lean-bench | 249-theorem history, 146 theorem--proof pairs, chronology-aware proof injection, and a real Rust-to-Lean verification repository | Independent cryptographic target/candidate and validation of the historical-task builder | Must pin an immutable release and audit task identities, source licenses, and agent harness |
| VeriSoftBench | 500 Lean tasks from 23 repositories with project and local dependencies | Repository-scale external target and possible disjoint candidate family | Pin code/data and verify that training and evaluation repositories can be separated without dependency leakage |
| Vero | 43 active multi-module Lean repositories with 743 APIs and 2,705 specifications | Repository-level candidate and external target | Source structure, runtime controls, and a repository-disjoint split are qualified; one excluded task establishes policy support, while containment and multi-repository coverage remain pending |
| FVSpec | 9,415 Lean challenges derived from 11,039 property-based tests from 333 repositories | Broad real-code specification/proof candidate; source of scalable task diversity | Filter the 41% of samples with stub implementations and audit translation quality, source-license propagation, repository grouping, axiom use, and specification validity |
| VeriContest | Current release reports 1,006 verified-programming problems in Verus and Dafny, with a fixed 300-problem Lite split | Later cross-tool target for specification, code, proof, and end-to-end generation | Pin one release, task list, toolchains, large test artifacts, and per-source licenses before use |
| Anthropic/Theorem OSS Verify | Public Rocq statements and proofs for compiled RISC-V OSS-Fuzz targets plus Linux-process semantics | Primary frontier reference; bounded source candidate; later external transfer target; source of hypotheses about proof reuse, test-to-spec conversion, and cost | Release indexes and checker bootstrap are qualified; proof replay, reset, rejection tests, and cost measurement remain pending |
| CrypFormBench | 700 instances, 677 schemes, seven verifier languages, five task types, 160 properties | Cryptography landscape and multi-tool diagnostic | Composite scores and heterogeneous verifier languages are not directly comparable to Lean repository utility |
| CryptoFormalEval | Manually validated flawed protocols with Tamarin interaction | Symbolic-protocol diagnostic | Symbolic protocol analysis is a different target from Lean proof development and computational-security reductions |

## Public environment evidence

The [compact public-evidence record](public-evidence/README.md) follows the
legal and robotics analyses. It retains native outcomes, scores choices within
comparable panels, and keeps retrospective evidence distinct from prospective
tests.

The strongest repeated positive intervention comes from DafnySynth. Adding
verifier-filtered synthetic annotations improves seven of eight matched settings
and ties the eighth across two starting models and four human-data fractions,
with a 15.8-point mean gain in the paper table. The pinned result JSONs preserve
the direction in every available comparison, although several endpoints differ
and the pure-synthetic arms are absent. The strongest current decision panel
comes from VeruSyn. A target-matched rule
chooses Part 1 data for algorithmic proofs and combined Part 1 plus Part 2 data
for system proofs. It selects the observed best arm in seven of eight nested
Accuracy@K panels with 0.25 points of mean regret. Formal Disco provides a
second positive family across Dafny and Verus annotation and Dafny lemma
proving. Re:Form provides the required
falsification: choosing the arm with the highest raw verifier success misses
the best specification-superiority arm at all five model scales.

The repository-policy record adds LeanLean, Vero, and Forall VeriSoftBench
without pooling their scores. Opus 5 leads LeanLean compression, GPT-5.6 Luna
has the lowest reported mean LeanLean cost, and GPT-5.5 xhigh leads Vero
repository completion. The reversal shows why a model must be selected for a
specific harness, objective, verifier, and budget. GPT-5.6 Sol remains one
locally executable Vero qualification policy rather than a universal default.

These are retrospective results. They justify target match, verified feature
coverage, semantic reward integrity, reliability, and cost as candidate
measurements. They do not establish a prospective selector.

## VeriBench

The launch corpus treats autoformalization as more than compilation. It
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

The version history matters. VeriBench v1.0 through v1.2 instructed the agent
to use `sorry` placeholders and preserved a compile-oriented contract. An
unmerged Harbor v1.3 candidate changes the instruction to require every
theorem to be proved and assigns zero credit to `sorry`. Its 896 task
directories are distinct from the 884-task launch corpus and remain a release
candidate rather than a qualified benchmark version.

**Admission decision:** prove-first target candidate. Commit `c9dfd8e3b535`
pins the Harbor task directories, but the release status, evaluator, container,
semantic scorer, licenses, and task identities must be qualified before use.

## Vero

Vero provides 43 active Lean repositories derived from Python, Dafny, Verus,
and Coq sources. Each instance freezes APIs and formal specifications while
supporting proof-only and joint code-and-proof modes. The grader reconstructs a
fresh project from source artifacts, overlays only marked agent outputs, builds
the result, and audits proof assumptions. Its negative-evidence paths also let
an agent prove that a reference implementation violates a specification or
that specifications are inconsistent.

The public source is pinned at commit
`0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09`. Its 43 manifests contain 237
modules, 743 scored APIs, and 2,705 scored specifications. Five benchmarks
declare 81 trusted axioms, and three active benchmarks retain LGPL licenses.
These properties must remain explicit rather than being collapsed into one
success label.

**Admission decision:** runtime-qualified repository-level candidate. The
pinned Lean runtime, bounded grader controls, clean reference builds, and
repository-disjoint split are qualified. A four-language development panel also
passes no-op, clean-reset, manifest-marker, and timeout controls. One excluded
GPT-5.6 Sol attempt establishes support on all nine PrimePy specifications.
Task-only model-facing containment and a multi-repository development screen
remain required before Vero can enter a claim-bearing environment comparison.

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

## VeriContest

VeriContest broadens the landscape beyond Lean while retaining executable
verification. Its current release reports 1,006 competitive-programming tasks,
with separate specification, code, proof, and end-to-end modes under Verus and
an end-to-end Dafny track. The release also includes positive and
mutated-negative tests designed to expose incomplete postconditions.

This is useful as a later transfer target because it separates failures in
specification construction from failures in implementation and proof. It
should not enter the first Lean study or share a scalar reward with Lean or
Rocq. One versioned release, explicit problem list, verifier toolchain, large
test artifacts, and upstream licenses must be pinned before qualification.

**Admission decision:** cross-tool target candidate only; immutable source and
artifact qualification remain pending.

## Anthropic and Theorem: production-scale assembly verification

Anthropic reports proofs for 239 entry points across 123 OSS-Fuzz libraries in
its broader effort. The public `theorem-labs/oss-verify-proofs` repository is a
smaller released subset and must be described by its own manifest. Release
`v2026.11.1`, pinned at commit
`6d15d8457aeecc77db61395ec8bcb3879b1d0f8b`, reports:

- 90 entry points in 32 libraries with published proofs
- 2,148 fuzz targets with statements from 427 buildable projects
- 526 proved statements and 19,656 open statements
- 20,421 statements and 8,718 indexed binaries overall
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

**Admission decision:** primary frontier reference and design evidence. The
release indexes, statement identities, checker digest, semantics revision, and
checker bootstrap are pinned and qualified. A deterministic development panel
can now be constructed from entry points that contain both proved oracle
statements and open measurement statements. Runtime admission still requires
proof replay, reset and rejection tests, remaining release-asset verification,
and measured cost. The source also remains a later external transfer target.
Do not pool its Rocq rewards with Lean rewards, and do not use the unreleased
portion of the reported study as if it were public data.

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
- VeriBench v1.3 Harbor candidate history:
  <https://github.com/harbor-framework/harbor-datasets/pull/148>
- VeruSyn: <https://arxiv.org/abs/2602.04910>
- Re:Form: <https://arxiv.org/abs/2507.16331>
- DafnySynth: <https://arxiv.org/abs/2411.15143>
- Formal Disco: <https://arxiv.org/abs/2607.04631>
- ATLAS: <https://arxiv.org/abs/2512.10173>
- InvBench: <https://arxiv.org/abs/2509.21629>
- LeanContext: <https://arxiv.org/abs/2611.08277>
- Vericoding Benchmark: <https://arxiv.org/abs/2509.22908>
- VCVio: <https://github.com/Verified-zkEVM/VCVio>
- dalek-lean-bench: <https://github.com/Beneficial-AI-Foundation/dalek-lean-bench>
- Anthropic formal-verification report:
  <https://www.anthropic.com/research/formal-verification>
- Public OSS Verify proofs: <https://github.com/theorem-labs/oss-verify-proofs>
- Public RISC-V/Linux semantics:
  <https://github.com/theorem-labs/rocq-linux-process-semantics>
- VeriSoftBench: <https://utopia-group.github.io/VeriSoftBench/>
- Vero: <https://github.com/sunblaze-ucb/vero> and <https://vero.verina.io/>
- FVSpec: <https://fvspec.galois.com/> and
  <https://github.com/GaloisInc/fvspec/tree/d680df4b00c68064db5a35994a89782aa4f637fb>
- VeriContest: <https://github.com/HIPREL-Group/VeriContest>
- CrypFormBench: <https://arxiv.org/abs/2606.25561>
- CryptoFormalEval: <https://arxiv.org/abs/2411.13627>
