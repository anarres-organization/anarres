# Public evidence for formal-verification environments

**Status:** retrospective and external evidence. No result in this record is a
prospective forecast.

This release asks which measurements distinguish useful environments for
training and deploying formal-verification systems. It follows the same
evidence pattern as the legal and robotics studies: preserve native outcomes,
score decisions only within comparable panels, retain practical controls, and
report falsifications alongside positive results.

The target is formal verification of real code. Anthropic and Theorem show the
frontier form of this target: compile existing OSS-Fuzz entry points to RISC-V,
derive specifications from their maintained tests, ask an agent to construct
Rocq proofs, and check those proofs against pinned machine semantics. Their
study proves 239 entry points from 123 open-source libraries and measures proof
completion against token budget. The pinned public Theorem repository exposes
proofs for 90 entry points across 32 libraries, so it is a reproducible subset
rather than the complete reported experiment. This record uses that workflow
to define the deployment target. It does not treat theorem-prover benchmark
accuracy as a substitute for production-code verification.

## Evidence at a glance

| Record | Decision or mechanism | Result | Appropriate conclusion |
| --- | --- | --- | --- |
| DafnySynth verified augmentation | Add verifier-filtered synthetic annotations at fixed DafnyBench fraction and training steps | The augmentation improves 7 of 8 matched settings in the paper table and ties the eighth, with a 15.8-point mean gain across two starting models | Verifier-filtered, task-relevant synthetic data can improve formal-verification training utility across policies and data scales |
| VeruSyn target matching | Choose among Part 1, Part 2, and combined training data for algorithmic or system proofs | The target-matched rule chooses the best arm in 7 of 8 nested budget panels, with 0.25 percentage points of mean regret | Training-data utility depends on the target proof distribution |
| Re:Form reward integrity | Use raw verifier success to choose among three RL reward environments | The rule chooses the wrong semantic winner at all five model scales, with 14.78 points of mean specification-superiority regret | Verifier acceptance alone is unsafe for environment selection |
| Formal Disco data generation | Prefer the generation environment with broader verified feature coverage | Formal Disco data beats SAFE at Pass@1 and Pass@32 under the same SFT pipeline | Verified diversity and feature coverage are useful data-environment measurements |
| Vericoding policy support | Measure which tasks are supported across models and verification languages | 2,847 of 6,121 tasks with at least eight model outcomes have both successes and failures | Candidate support is policy- and language-dependent |
| Repository policy support | Compare released agents without combining their native objectives | Opus 5 leads LeanLean compression, GPT-5.6 Luna has the lowest reported LeanLean cost, and GPT-5.5 xhigh leads Vero repository completion | A starting policy must be selected for a specific harness, task contract, verifier, and budget |
| Anthropic and Theorem production workflow | Prove properties of compiled OSS-Fuzz binaries under a token budget | 239 entry points across 123 libraries were proved. Newer models and shared proofs reduced token use. | Real-code proof completion, cost, reuse, and patch integrity define the frontier target |

## DafnySynth: positive transfer across models and data scales

The dafny-annotator study holds the training recipe and 1,500-step budget fixed
while varying the fraction of human-written DafnyBench data and whether the
environment includes verifier-filtered DafnySynth annotations. It evaluates the
resulting models on the same 83 held-out methods whose human annotations have
been removed.

Adding DafnySynth improves seven of eight matched comparisons in the published
table and ties the eighth. The mean gain is 15.8 percentage points across Llama
3.1 8B and CodeLlama 7B. The benefit appears at 0%, 25%, 50%, and 100% of the
human-written training pool rather than depending on one data scale. The full
eight-arm environment order has 73.2% pairwise agreement across the two
starting models.

The pinned repository provides a second audit from its released result JSONs.
It contains six fraction-matched comparisons rather than the paper's eight
because no pure-DafnySynth result file is present. Five comparisons improve and
one ties, with a 15.65-point mean gain. Several exact endpoints differ from the
paper table, so the reproducer keeps the paper and repository audits separate.
Their shared direction is the useful result: at matched training steps and
human-data fraction, the measured verified augmentation consistently avoids
reducing held-out verification success in this grid.

This is positive retrospective external evidence, not a prospective Anarres
selection. It strengthens the case for measuring verifier survival, annotation
coverage, and target relevance before committing a formal-verification
training budget.

## VeruSyn: target-matched training data

VeruSyn reports one matched Qwen2.5-Coder-32B SFT pipeline with three candidate
training environments:

- Part 1, dominated by small synthetic algorithmic proofs
- Part 2, agent trajectories from real-system proof tasks
- the combined VeruSyn dataset

The retrospective practical rule chooses Part 1 for VerusBench algorithmic
proofs and the combined dataset for VeruSAGE system proofs. Across
Accuracy@1, @5, @10, and @100, this rule chooses the observed best arm in seven
of eight panels. It loses two points at VeruSAGE Accuracy@1, where Part 2 leads
the combined dataset 9% to 7%. It is correct for the other seven panels and has
0.25 points of mean allocation regret.

The eight panels are nested within two benchmark contexts and reuse trained
models across sampling budgets. They are decision views, not eight independent
training experiments. The rule is retrospective and needs a new frozen panel
before it can support a prospective selection claim.

## Re:Form: verifier success is an insufficient selector

Re:Form compares verification reward, subset reward, and subset reward with
entropy and KL regularization at five model scales. At every scale from 0.5B to
14B, selecting the environment with the highest verifier success chooses the
verification-reward arm. The subset-reward arm has the strongest specification
superiority at every scale.

The raw-verification rule is therefore correct in 0 of 5 scale panels and
incurs 14.78 points of mean specification-superiority regret. This result is a
direct reward-integrity warning. A candidate can become easier for the verifier
to accept by producing weak specifications without becoming more useful for
proving the intended program behavior.

## Formal Disco: generation diversity transfers downstream

Formal Disco measures verified program diversity through feature entropy and
uses specialized initiator, repair, and extension workers. The specialized
workflow verifies 29.8% of LLM calls compared with 23.0% for a monolithic
agent. Its verified programs are also substantially larger and cover broader
program features.

Under the same Qwen2.5-Coder-32B SFT pipeline, Formal Disco data reaches 43.0%
Pass@1 and 59.1% Pass@32 on VerusBench. SAFE reaches 40.9% Pass@1 and plateaus
at 51% from Pass@16 onward. The comparison supports verified feature coverage
as a candidate-environment measurement.

The positive transfer is broader than the SAFE comparison. Relative to the
same base model, Formal Disco training improves Dafny annotation Pass@16 from
19.5% to 40.4%, Verus annotation Pass@1 from 8.7% to 43.0%, and Dafny lemma
proving from 4.5% to 25.5% at Pass@1 and from 20.7% to 39.8% at Pass@32. The
generation ablation also connects a measurable source property to the resulting
bank: documentation snippets raise tracked Dafny feature coverage from 26 to
all 30 features. These comparisons remain retrospective and use different
tasks and sampling budgets, so the reproducer preserves each endpoint rather
than pooling them into one effect.

## Vericoding: support depends on policy and language

The Vericoding release contains 55,397 outcomes over 6,336 tasks, nine models,
and three verification languages. Among 6,121 tasks with outcomes from at
least eight models, 2,978 are unsolved by every reported model, 296 are solved
by every reported model, and 2,847 have both successes and failures.

This is cross-policy disagreement rather than repeated sampling from one
policy. It does not measure downstream utility. It does show that candidate
qualification must be repeated for the intended starting policy and
verification language instead of treating task difficulty as fixed.

## Repository-level policy evidence

The released repository studies provide a stronger policy screen than a single
local qualification. LeanLean publishes comparator-checked outcomes, cost, and
duration for six policies over 64 repositories. Opus 5 with Claude Code has the
highest mean compression and 64 valid submissions, while GPT-5.6 Luna with
Codex has the lowest reported mean cost. GPT-5.6 Sol is faster than Opus 5 but
has lower compression and higher reported mean cost.

Vero uses a different objective: complete every specification in a repository
within 90 minutes. GPT-5.5 xhigh with Codex leads both modes, fully solving 27
of 43 code-and-proof repositories and 25 of 43 proof-only repositories. The
Forall VeriSoftBench release adds 1,300 task records across 13 configurations,
but its reported acceptance, retained artifacts, axiom audits, and independent
checks have different coverage and must remain separate.

The same release also identifies a usable boundary regime without new
inference. GPT-5.6 Sol at xhigh reasoning through Codex accepts 97 of the 100
retained tasks under a Pass@8 protocol. Fifteen tasks are first solved on
samples 2--6, establishing at least one unsuccessful sample before a successful
sample for the same policy and task. These tasks span ArkLib, clean, the Lean
Formal Reasoning Program, the Leroy compiler-verification course, and VCV-io.
They provide a source-pinned panel for nondegenerate policy qualification. The
release withholds the individual failed samples and per-sample token cost, so
it cannot by itself estimate signal density, effective coverage, or downstream
training utility.

These sources rule out a universal model ranking. Leanstral, for example,
returns valid LeanLean submissions on 53 repositories but has zero strict
success in the separately released Anarres Vero development measurement.
GPT-5.6 Sol remains one executable, source-supported Vero qualification policy.
Later protocols may select a different model from source-pinned evidence.
After process containment is qualified, a small development-only panel should
compare candidate policies under one matched Vero contract before repeated
environment measurement.

## Anthropic-aligned evaluation contract

The production target has four parts:

1. **Real code and maintained properties.** Begin with open-source libraries
   and developer-authored fuzz entry points rather than isolated theorem text.
2. **Machine-checked guarantees.** Compile the program, identify the exact
   semantics revision, and require the proof kernel to accept the result.
3. **Finite-budget utility.** Measure completion as a function of generated
   tokens, wall time, and proof-checking cost. Anthropic's 36-task comparison
   uses three independent attempts per task at a five-million-token budget.
4. **Integrity and reuse.** Audit program patches, preserve failed attempts,
   and measure whether reusable proof components reduce cost. Anthropic reports
   a 17% token reduction from a shared proof workspace.

These criteria define the next prospective panel. The candidate environment
should vary task or proof context while holding the starting policy, proof
checker, semantics, token budget, and target entry points fixed.

## Reproduce

```bash
cd experiments/cyber/formal-verification/public-evidence
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

The reproducer recomputes the DafnySynth augmentation audit, VeruSyn decision
quality, the Re:Form falsification, the Formal Disco comparison, and the
Vericoding support counts from compact source-linked facts.

## Files

- [`data/anthropic-oss-fuzz.json`](data/anthropic-oss-fuzz.json): production
  proof and efficiency facts
- [`data/dafny-synth.json`](data/dafny-synth.json): matched verified-augmentation
  comparisons across two models and multiple human-data fractions
- [`data/verusyn.json`](data/verusyn.json): target-matched candidate panels
- [`data/reform.json`](data/reform.json): reward-environment outcomes
- [`data/formal-disco.json`](data/formal-disco.json): generation and downstream
  comparisons
- [`data/vericoding.json`](data/vericoding.json): compact policy-support facts
- [`data/policy-support.json`](data/policy-support.json): repository-level
  policy, harness, cost, and validity evidence
- [`results/summary.json`](results/summary.json): deterministic derived result
- [`scripts/reproduce.py`](scripts/reproduce.py): standard-library analysis
- [`test_reproduce.py`](test_reproduce.py): scientific-integrity checks
- [`SOURCES.json`](SOURCES.json): pinned provenance and redistribution limits
- [`MANIFEST.sha256`](MANIFEST.sha256): release-file hashes

## Boundaries

The sources vary different objects. VeruSyn and Formal Disco study training
data, Re:Form studies reward design, Vericoding studies inference support,
LeanLean studies proof compression, Vero studies complete repository closure,
and Anthropic studies production proof construction. Their native outcomes
remain separate. The combined evidence motivates an environment-selection
workflow, but it does not establish one universal selector, one universal
starting policy, or a valid reason to pool their scores.
