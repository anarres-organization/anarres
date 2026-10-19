# Predictable post-training in cyber environments

## Purpose

The cyber program studies whether measurements made before reinforcement
learning can predict which authorized cybersecurity environments will improve a
particular model on a particular target objective at a fixed compute budget.
It is the second major domain test for Anarres after mathematics and agentic
terminal work.

The scientific object remains

\[
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D),
\]

where \(E\) is a training-environment distribution, \(\pi_0\) is the starting policy,
\(C\) is generated-action-token or equivalent interaction compute, and \(D\)
is an explicitly named target distribution. The aim is not to find one
universally optimal cyber environment. It is to predict which candidate
environment best serves a specified model, target, and budget.

Cyber is scientifically useful because it changes the structure of the problem.
Compared with the existing terminal study, cyber tasks can have sparser rewards,
deeper prerequisites, more consequential state transitions, heterogeneous
verifiers, and stricter containment requirements. A successful cyber study
would therefore test the portability of the Anarres methodology rather than
merely repeat the terminal experiment with different task names.

No claim-bearing cyber RL run is authorized by this document. Benchmark
qualification, containment, target separation, and the warm-start measurement
gate must pass first.

The program is active. The public research plan, static source audit, frontier-
relevance audit, power analysis, and qualification protocol are complete.
Fixture execution and warm-start qualification remain pending, and cyber RL is
not yet authorized.

The executable qualification checklist and preliminary source registry live in
[`qualification/`](qualification/README.md).

## Relationship to the existing Anarres program

The domains form a progression:

- **Mathematics** established that policy-relative signal density and coverage
  can help predict finite-budget utility across controlled environments and
  model scales.
- **Agentic terminal work** tests those ideas in long-horizon executable tasks
  drawn from several source and verifier families. Its frozen prospective test
  must be completed and scored without redesign.
- **Cyber** asks whether target-conditioned utility can be forecast when task
  completion depends on security prerequisites, stateful interaction, and
  verifier-specific notions of progress.
- **Later domains** such as scientific tool use and robotics will test further
  changes in reward, state, and action structure.

The shared object is utility. The shared interface includes the starting policy,
target distribution, environment specification, compute budget, validity,
policy-relative measurements, downstream learning curves, uncertainty, and
selection regret. The coefficient vector and even the useful measurements need
not be identical across domains.

The cross-domain research workflow is:

```text
starting model + target objective + compute budget
    -> qualify candidate environments
    -> measure them under the starting policy
    -> forecast target-specific improvement and uncertainty
    -> compare candidate environment specifications
    -> train under a frozen contract
    -> evaluate on an isolated target
    -> update the forecasting system
```

## Frontier relevance

Benchmark choice is anchored in capabilities evaluated by current frontier
model developers, not only in datasets that are convenient to run. The dated
official-source record and its re-audit rule are in
[`qualification/FRONTIER_RELEVANCE_AUDIT.md`](qualification/FRONTIER_RELEVANCE_AUDIT.md).

The current evidence supports different roles rather than one universal cyber
benchmark:

| Benchmark or target | Current frontier signal | Role in this program |
| --- | --- | --- |
| Historical ExploitBench | GPT-6 Astra reports 100% | Diagnostic only; not a primary frontier endpoint |
| SEC-Bench Pro | GPT-6 Astra reports 85.4% | Initial qualification candidate and possible training family |
| ExploitGym | GPT-6 Astra reports 42.4% | High-priority external frontier-transfer target |
| Recent ExploitBench vulnerabilities | GPT-6 Astra reports 39.0% on an internal June--August 2026 port | Evidence for a recent or sequestered endpoint; the internal set itself is unavailable |
| CyberGym-E2E | Public end-to-end benchmark with discovery, proof-of-concept, patching, and functionality checks | Investigation target for end-to-end defensive transfer |

These percentages come from one published model and its stated harnesses. They
establish headroom and relevance, not direct comparability with a local run.
Every result must retain the benchmark version, scaffold, token and time budget,
tool contract, mitigations, and grading revision.

Appearing in a frontier report is necessary evidence of relevance, not
sufficient evidence that a benchmark supports the experiment. The exact 8B warm
start must also occupy a measurable, unsaturated regime; the fixtures must be
reproducible; and the target must remain isolated from training and benchmark
selection. A hard external target may remain scientifically important even when
it is too sparse to serve as the first RL training source.

## Benchmark portfolio

One benchmark should not stand in for all cybersecurity capability. The broader
program therefore separates learnable training families from frontier-facing
evaluation targets. The first pilot does not implement every family. Its
qualification bakeoff is limited to CyberGym and SEC-Bench Pro as candidate
primary training families, with ExploitBench used only to test whether graded
capability signals reveal useful warm-start headroom. ExploitGym is a planned
external transfer target. CyberGym-E2E and a recent or sequestered vulnerability
panel remain investigation targets until their access, isolation, identity, and
cost contracts are qualified.

### ExploitBench: graded qualification and capability diagnostics

[ExploitBench](https://exploitbench.ai/) measures 16 deterministic capability
levels, from reaching vulnerable code through arbitrary code execution. Its
capability ladder is valuable for warm-start qualification because it can expose
measurable progress even when complete exploitation is rare. Highest-tier success
remains the strict endpoint; intermediate capabilities diagnose where learning
changes behavior.

ExploitBench currently lacks a clean held-out CVE set, according to its own
methodology. It should therefore not be presented as uncontaminated prospective
evidence without a new sequestered partition. Historical ExploitBench is also
saturated by the strongest reported frontier result, so it is not the main
frontier endpoint.

### CyberGym and SEC-Bench Pro: reproducible real-vulnerability regimes

[CyberGym](https://github.com/sunblaze-ucb/cybergym) provides a large bank of
real vulnerabilities and verifies a designated final proof of concept against
vulnerable and patched builds. The patched build must remain inaccessible to the
agent. Final-submission success, not any-of-many submission success, is the
primary outcome.

[SEC-Bench Pro](https://github.com/SEC-bench/SEC-bench-Pro) provides
automatically graded proof-of-concept tasks under several information regimes.
Repository-only, vulnerability-description, and sanitizer-assisted conditions
may supply controlled feedback interventions, provided task identity and target
separation remain fixed.

These sources are the leading candidates for the first reproducible
real-vulnerability utility study. The qualification bakeoff selects at most one
as the initial primary family. They remain separate verifier families in any
analysis and are never pooled merely to enlarge the task count.

### ExploitGym: hard external transfer

[ExploitGym](https://github.com/sunblaze-ucb/exploitgym) tests whether an agent
can turn real vulnerabilities into working exploits across userspace programs,
V8, and the Linux kernel. It is highly relevant to frontier evaluation and still
has substantial headroom. It also imposes greater containment, storage, and
execution complexity. A small untouched ExploitGym panel is therefore a later
external stress test, not the first training source. It is now the highest
priority public external target because the strongest reported frontier result
still leaves substantial headroom. Qualification must preserve the official v1
offline restrictions, intended-vulnerability judge, target mitigations, and
harness budget rather than treating top-line scores from different contracts as
interchangeable.

### CyberGym-E2E: end-to-end defensive transfer

[CyberGym-E2E](https://www.cybergym.io/cybergym-e2e/) evaluates a longer
defensive workflow: discover a vulnerability, produce a proof of concept, patch
it, preserve functionality, and verify that the target vulnerability was fixed.
Its 920-task, 139-project public benchmark exposes cumulative stages rather than
one undifferentiated success bit. This structure is relevant to interactive
training environments and can distinguish exploit discovery from remediation.

CyberGym-E2E is not added to the first bakeoff. A bounded investigation should
first establish immutable task access, license and identity coverage, containment,
reset cost, warm-start stage occupancy, and separation from the training family.
Only then can it become an external target or later training family.

### Recent or sequestered vulnerabilities

OpenAI's June--August 2026 internal ExploitBench port was constructed from
vulnerabilities disclosed after the model's knowledge cutoff and was much harder
than the historical benchmark. Because the tasks are internal, that result
cannot be reproduced directly here. It motivates a separate public protocol:
freeze an authorized panel by disclosure and acquisition timestamp, preserve
upstream identities and patches, exclude every panel task and near duplicate
from probing and training, and publish the selection rule before evaluation.

This panel is a later independent endpoint. It is not created by sampling tasks
after model outcomes are known, and it does not delay the first feasibility
bakeoff.

### CTF and stateful range tasks: coverage and later transfer

[NYU CTF Bench](https://nyu-llm-ctf.github.io/) and
[Cybench](https://arxiv.org/abs/2408.08926) cover cryptography, reverse
engineering, binary exploitation, forensics, web security, and related skills
with exact flag-based outcomes. They are useful for scaffold qualification,
training-source diversity, and a broad CTF sentinel. Their public exposure and,
for Cybench, small task count make them insufficient as the sole prospective
target.

[AgentCyberRange](https://arxiv.org/abs/2606.14295) is closer to the eventual
stateful cyber problem, including web exploitation and post-exploitation. It is
a high-value later target once reproducibility, licensing, and containment have
been verified.

CTF flags, differential crash reproduction, progressive exploitation
capabilities, and multi-host compromise are distinct scientific outcomes. They
must not be pooled into one reward scale without explicit verifier and regime
effects.

## Scope and feasibility budget

The first milestone is one qualified, authorized benchmark family, one isolated
target, and one complete measurement-to-training-to-utility loop. It is not a
general cyber platform.

Before qualification begins, freeze a feasibility budget covering engineering
time, storage, image construction, reset latency, sandbox concurrency, and total
warm-start rollouts. A benchmark leaves the first-pilot path when it exceeds
that budget, cannot satisfy containment with its existing public interface, or
requires a new general-purpose orchestration layer. It may remain a later
external test.

Infrastructure work is limited to what the scientific contract requires:

- one adapter for the selected primary family;
- deterministic fixture reset and oracle/no-op checks;
- failure typing that separates infrastructure errors from scientific reward;
- the existing isolated agent, rollout, training, and evaluation interfaces;
- immutable manifests sufficient to reproduce the experiment.

The pilot does not build adapters for every benchmark, a shared cyber range, a
new sandbox scheduler, or a generalized benchmark service. Existing benchmark
and Anarres components are reused when they pass the frozen gates. Throughput
optimization follows a measured bottleneck and cannot change the task, reward,
agent, or evaluation contract.

## Benchmark and warm-start qualification gate

Qualification uses development tasks only. It determines whether a candidate
benchmark can support the study; it does not inspect downstream RL outcomes and
does not select among environments based on post-training performance.

Before running the bakeoff, freeze numerical thresholds derived from a power and
cost analysis. At minimum, every candidate must satisfy the following conditions:

1. **Frontier relevance.** The task family measures a capability reported by
   frontier developers or a clearly justified missing capability.
2. **Measurable warm-start regime.** The exact starting policy exhibits nonzero
   success or deterministic graded progress without approaching saturation.
3. **Policy-relative variation.** Repeated rollouts produce enough mixed groups
   to estimate admitted signal density and effective coverage.
4. **Verifier fidelity.** Every admitted fixture passes its oracle, rejects a
   no-op, reproduces across resets, and records verifier provenance.
5. **Failure separation.** Sandbox, timeout, dependency, reset, and grader
   failures remain infrastructure failures rather than scientific reward zero.
6. **Headroom and precision.** The frozen evaluation has enough tasks and
   baseline headroom to resolve changes of scientific interest.
7. **Contamination control.** Training and target partitions are disjoint by
   exact task, upstream repository and revision, CVE or bug identity,
   competition, solution artifact, and near-duplicate content.
8. **Containment.** Agent egress is denied by default, vulnerable services are
   reachable only within the isolated task network, secrets and reference
   solutions are absent, and the grader is not agent-readable.
9. **Cost feasibility.** Storage, reset time, sandbox concurrency, and generated
   interaction cost permit matched-budget replicated runs.

If the warm start is at the floor, the task family may still be useful as a hard
external stress test but not as the primary target for the initial utility study.
Hints, subtasks, or richer observations may define training environments; they
must not silently weaken the frozen target evaluation.

## Measurements

The first measurement layer preserves quantities with evidence from mathematics
and terminal work:

- admitted signal density \(\rho\);
- effective coverage \(H\);
- generated action or interaction cost;
- verifier validity and infrastructure reliability;
- target affinity \(\alpha\), retained as a challenger until it demonstrates
  incremental value.

Cyber-specific candidates are recorded before being admitted to a predictor:

- prerequisite or reachability depth;
- fraction of valid episodes reaching meaningful intermediate capabilities;
- feedback density and delay;
- reset determinism and infrastructure-failure rate;
- verifier family and reward granularity;
- exploit, proof-of-concept, or flag validity;
- target-family and skill coverage.

Each new coordinate requires a definition computable before claim-bearing RL, a
reliability audit, a collinearity audit, and an environment-level holdout test.
It begins as a nested challenger rather than automatically entering the primary
law.

## First cyber experiment

The first experiment asks:

> Can measurements made under the starting policy forecast downstream
> improvement in authorized cyber environments with verifier and interaction
> structures that differ from terminal-agent tasks?

The minimal sequence is:

1. Complete and score the frozen agentic prospective experiment. Cyber
   qualification may proceed in parallel, but cyber RL does not replace or alter
   that test.
2. Run a development-only bakeoff of CyberGym and SEC-Bench Pro using the exact
   warm start, agent loop, tool budget, and containment boundary intended for
   training. Use ExploitBench only as a graded-headroom diagnostic.
3. Select one initial primary family and one isolated target using the frozen
   qualification criteria. Designate ExploitGym as the first public external
   transfer candidate, but do not integrate it until its separate safety and
   feasibility gate passes.
4. Construct four to six genuinely distinct training-environment distributions
   that vary interpretable properties rather than only source labels.
5. Measure every candidate under the warm start, audit reliability and geometry,
   and freeze the candidate identities, target, budgets, seeds, baselines,
   forecasts, uncertainty rule, and abstention rule.
6. Run a matched-budget two-seed pilot and evaluate complete utility curves on
   the isolated target. The pilot estimates effect size and feasibility; it does
   not validate a general cyber forecasting law.
7. Expand to a claim-bearing panel only if the pilot shows reproducible
   environment-dependent utility and the evaluation has adequate precision.
8. Run the untouched frontier-recognized external benchmark without using it to
   refit or select the primary result.

The first six steps test whether a tractable family supports controlled RL. The
external steps test whether the resulting environment decision matters on a
capability that remains frontier-relevant. Failure of a hard target to provide
warm-start training signal does not make it irrelevant; it changes its role from
training source to evaluation endpoint.

The pilot answers three prespecified questions: whether candidate environments
produce distinguishable downstream curves, whether policy-relative signal
density and coverage can be measured reliably, and whether variation across
environments and budgets justifies a larger study. A larger panel must contain
enough independent environments to evaluate new-environment prediction and
decision quality.

Difficulty and learning utility remain separate quantities. A hard
vulnerability may supply little usable learning signal, while a less difficult
task may produce dense but redundant updates. Starting success, capability
depth, \(\rho\), \(H\), cost, and reliability are therefore recorded separately.

### Prespecified pilot-expansion gate

Before any pilot outcome is inspected, the frozen pilot contract must assign
numerical thresholds to each condition below. The pilot expands only if all
required conditions pass:

1. **Learnable starting regime:** the warm start is neither at the floor nor at
   saturation, and enough valid groups contain reward or capability variation to
   estimate the prespecified measurements.
2. **Measurement reliability:** independent probe views meet the frozen
   agreement thresholds for the coordinates used by the primary model.
3. **Environment effect:** between-environment utility differences are large
   enough, relative to seed and task uncertainty, to support the powered larger
   study.
4. **Curve information:** more than one budget contributes decision-relevant
   information; an endpoint-only study is used instead if intermediate curves
   are not distinguishable.
5. **Experimental feasibility:** the observed valid-rollout rate, reset time,
   storage, and compute cost permit the prespecified number of independent
   environments and seeds within the larger-study budget.
6. **Verifier and containment integrity:** no unresolved leakage, oracle,
   reset, grader, or isolation failure can affect a scientific outcome.

Failure does not trigger post-hoc environment replacement or threshold changes.
It yields a bounded feasibility result and a documented decision to revise or
stop before claim-bearing expansion.

## Forecast and decision evaluation

The cyber study reports prediction and selection separately:

- whole-curve RMSE, MAE, bias, and interval coverage on held-out environments;
- improvement-sign and budget-dependent ranking accuracy;
- correct best-environment decisions at prespecified budgets;
- allocation regret against compute-only, fixed-environment, difficulty,
  pass-rate, cost, and source/verifier baselines;
- risk-coverage behavior and abstention when predicted margins are small;
- seed-level variation, infrastructure-failure rates, and target-task bootstrap
  uncertainty as distinct quantities;
- transfer to the external frontier benchmark.

Low retrospective fit error is not enough. The useful result is whether the
predictor chooses a better training environment than credible cheap alternatives
for a named target and budget.

## Path from forecasting to environment design

The cyber research progresses through three evidentiary stages:

1. **Prediction:** forecast utility and uncertainty for unseen cyber
   environments.
2. **Selection:** prospectively choose among existing authorized environments
   and beat strong operational heuristics at matched compute.
3. **Environment design:** construct a new authorized environment distribution
   for a specified target, freeze its predicted advantage, and test whether it
   improves the target more than representative and heuristic alternatives.

An environment-design experiment should include both disagreement-rich
candidates and a representative reference set. Early acquisition may combine
uncertainty, model disagreement, decision relevance, and experiment cost. More
elaborate Bayesian or neural acquisition models require substantially more
independent environment-outcome observations than the initial pilot supplies.

A small environment-construction prototype may proceed alongside measurement
once the primary family is selected. It stays inside that family's authorized
fixtures and varies a frozen set of interpretable controls, such as prerequisite
exposure, starting state, feedback granularity, or task mixture. It produces
candidate environments for measurement; it does not claim to generate optimal
worlds. The prototype must reuse the selected adapter and containment boundary,
and it pauses if supporting it delays the qualification or pilot critical path.

## Safety and release boundary

All work is restricted to authorized, isolated benchmarks and locally controlled
infrastructure. Follow the repository [security policy](../../SECURITY.md) and
the stricter requirements of each benchmark.

- Never expose a vulnerable service or submission server to the public internet.
- Deny network egress unless a frozen allowlist is scientifically required.
- Remove repository history, reference exploits, patched binaries, answer keys,
  and other leakage channels before agent access.
- Keep grader credentials and expected flags outside the agent sandbox.
- Record all reachable services and preserve task-scoped action logs.
- Review trajectories for grader access, benchmark lookup, cross-task leakage,
  sandbox escape, and reward hacking.
- Release only artifacts whose licenses and responsible-disclosure constraints
  permit publication.

Any containment failure stops the affected execution and is reported separately
from task performance. Scientific throughput never overrides the isolation
boundary.

## Immediate deliverables

Before the first cyber RL launch, this directory should contain:

- a source and license registry with immutable revisions;
- a threat model and containment specification;
- benchmark qualification criteria and power analysis frozen before probing;
- warm-start qualification results for the candidate families;
- development, prospective, and external-transfer partitions;
- fixture oracle/no-op and reset manifests;
- contamination and near-duplicate audit results;
- a compute and storage budget;
- a frozen pilot training and evaluation contract;
- compact baseline forecasts and uncertainty rules.

The launch packet must also record the frozen feasibility budget, the rejected
benchmark families and reasons for rejection, and an explicit declaration that
the chosen task family, target, and environment controls can be executed without
building additional general-purpose infrastructure.

The first public claim should be proportional to the evidence: either the
methodology forecasts and improves a real cyber environment-selection decision,
or the experiment identifies which measurements fail to transfer and what new
information is required. Both outcomes advance the cross-domain Anarres program.
