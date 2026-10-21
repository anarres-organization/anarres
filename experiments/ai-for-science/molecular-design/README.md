# Predictable post-training for molecular design

## Purpose

This study asks whether measurements made before post-training can predict which
reaction-based molecular-design environments will produce the greatest
improvement for a specified starting policy, protein target, and compute budget.
It is the first planned AI for Science domain test in Anarres.

The domain is **molecular design**. It sits at the intersection of chemistry,
chemical biology, and drug discovery. Calling it biology alone would be too
broad. Calling it chemistry alone would omit the protein-targeted objective.
The first experiment is computational and does not make claims about clinical
efficacy or experimental validation.

The scientific object remains

$$
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D),
$$

where $E$ is a distribution over building blocks and reaction actions,
$\pi_0$ is a common molecular graph policy, $C$ is a matched oracle or
generation budget, and $D$ is a frozen protein-target evaluation. The aim is
not to find one universally optimal chemical environment. It is to test whether
environment utility can be forecast for a named model, target, and budget.

No claim-bearing molecular-design run is authorized by this document. Source,
reward, oracle, split, and warm-start qualification must pass before the
development and prospective contracts are frozen.

## Why molecular design is a distinct domain test

Molecular generation changes the structure of the environment-utility problem.
A policy acts on a molecular graph, valid actions depend on chemical context,
and complete trajectories describe reaction routes rather than token-only
answers. Downstream utility may depend on scaffold coverage, molecular
connectivity, reaction-family coverage, route depth, reward signal, and oracle
cost.

This makes the study more than a transfer of terminal-agent infrastructure.
Anarres must preserve the same prediction and evaluation discipline while using
measurements that reflect molecular graphs and reaction structure.

The shared workflow is:

```text
starting graph policy + protein target + compute budget
    -> qualify reaction fixtures and oracle behavior
    -> measure candidate environments under the starting policy
    -> forecast target-specific improvement and uncertainty
    -> freeze development and prospective environments
    -> post-train under matched budgets
    -> evaluate on a scaffold-disjoint target panel
    -> score prediction and environment-selection quality
```

## Frontier relevance

The plan uses current public methods for reaction-based molecular generation,
GPU-accelerated docking, graph learning, and structure-aware virtual screening.
The components have different roles and should not be treated as one benchmark.

| Component | Evidence of relevance | Role in the study |
| --- | --- | --- |
| [RxnFlow](https://proceedings.iclr.cc/paper_files/paper/2025/hash/24d36eee157559e0d2549455fba28f6a-Abstract-Conference.html) | ICLR 2025 reaction-based GFlowNet with a maintained public implementation | Molecular graph policy and reaction environment |
| [RxnFlow v2.1.0](https://github.com/SeonghwanSeo/RxnFlow/releases/tag/v2.1.0) | Current public release at the time this plan was written | Version qualified before execution |
| [HSX](https://www.biorxiv.org/content/10.64898/2026.10.01.755933v1.full) | Recent large-scale reaction-based molecular generation system built on RxnFlow | Evidence that the policy family remains relevant at larger scale |
| [Uni-Dock](https://pubs.acs.org/doi/10.1021/acs.jctc.2c01145) | GPU-accelerated molecular docking | Shared target reward and evaluation oracle |
| [LIT-PCBA](https://doi.org/10.1021/acs.jcim.0c00155) | Public virtual-screening benchmark with experimentally confirmed actives and inactives | Protein-target selection and independent evaluation construction |
| [GraphGPS](https://proceedings.nips.cc/paper_files/paper/2022/hash/5d4834a159f1547b267a05a4e2b7cf5e-Abstract-Conference.html) | General recipe combining local message passing with global attention | Focused graph-architecture comparison |
| [PyTorch Geometric](https://rlgm.github.io/papers/2.pdf) | Widely used graph-learning library | Reproducible graph batching, message passing, and GPS implementation |

This evidence establishes methodological relevance. It does not establish that
the planned environment predictor works. The exact starting policy, target,
oracle, and environment panel must still occupy a measurable and unsaturated
regime.

The stable public releases and their licenses must be re-audited when the
execution contract is frozen. A newer release is adopted only before that
freeze and only after compatibility and reward parity pass.

## Public system and target

The first study uses RxnFlow's public reaction environment. Its current release
includes a 5,000-building-block construction pool and an exploration setting
with 26 bimolecular and four unimolecular reaction templates plus compatibility
constraints. The experiment trains one common QED warm start on the uniform
construction pool and freezes it before measuring or post-training candidate
environments.

Every environment uses the same target reward computed under one frozen
Uni-Dock configuration and the same frozen protein target selected from
LIT-PCBA. Construction and
evaluation molecules are separated by
[Bemis-Murcko scaffold](https://pubmed.ncbi.nlm.nih.gov/8709122/). Task identities,
environment weights, preprocessing rules, model identity, target identity, and
content hashes are frozen before downstream outcomes are observed.

The released QED example is a training recipe, not a released pretrained
checkpoint. The common warm start must therefore be trained once, audited, and
reused across all environments.

## First experiment

The initial study contains eight equal-budget environments. Six are development
environments and two are prospective environments that remain untouched until
the selector, uncertainty rule, and abstention rule are frozen.

The environments vary interpretable properties of the reaction-based search
distribution, including:

- building-block and reaction-family mixtures
- effective scaffold and ring-system coverage
- molecular connectivity and route depth
- starting-policy reward signal and mixed-group frequency
- measurement reliability and valid-trajectory rate
- oracle cost and docking-failure rate

All environments share the same starting checkpoint, target reward, graph
action space, training algorithm, generated-molecule or oracle budget, and
evaluation panel. The primary design uses two training seeds and three matched
budgets so that the analysis measures utility curves rather than only endpoints.

The first experiment asks three questions:

1. Do candidate reaction environments produce distinguishable downstream
   utility curves under matched compute?
2. Do measurements made under the starting policy predict those differences?
3. Do graph-structural measurements improve environment selection beyond
   reward signal, reliability, and cost alone?

## Graph learning analysis

The full environment study uses RxnFlow's GINE-style message-passing encoder.
Molecules are graphs whose nodes represent atoms and whose edges represent
bonds. Reaction choices and attachment decisions depend on the current graph,
reaction identity, and compatible building blocks.

Two nested environment selectors test whether graph information adds predictive
value:

- **Operational selector:** starting-policy reward signal, reliability, valid
  trajectory rate, and oracle cost.
- **Graph-aware selector:** the operational measurements plus effective scaffold
  and ring-system coverage, molecular connectivity, reaction-family coverage,
  and route depth.

The comparison is predictive rather than causal. These environments can also
differ in chemical composition and reward distribution, so improved prediction
would show incremental value from graph-structural information without claiming
that topology alone caused the utility difference.

A focused architecture study compares the message-passing encoder with a
parameter-matched PyTorch Geometric `GPSConv` encoder on the uniform environment
at the largest prespecified budget. Both models receive the same QED pretraining
data, update budget, action interface, reward, and evaluation panel. Each model
is initialized and pretrained independently because their encoder weights are
not interchangeable. This comparison is nested within the main study rather
than multiplying all eight environments across architectures.

## Qualification gates

Qualification uses development data only. It cannot inspect prospective RL
outcomes or replace environments based on downstream performance.

Before post-training begins, the launch packet must establish:

1. **Source identity and license.** Record stable versions, source licenses,
   dataset identities, preprocessing code, and content hashes.
2. **Reaction validity.** Sampled actions obey the frozen compatibility rules,
   generated products are chemically parseable, and route construction is
   reproducible.
3. **Oracle fidelity.** Reference ligands, valid controls, invalid controls, and
   repeated docking calls behave as expected under the frozen configuration.
4. **Warm-start headroom.** The common policy is neither at the floor nor at
   saturation on the target objective.
5. **Policy-relative signal.** Independent probe views provide enough valid and
   nondegenerate trajectories to estimate the prespecified measurements.
6. **Measurement reliability.** Coordinates used by the primary selector meet
   frozen agreement thresholds across probe views.
7. **Target separation.** Construction, development, prospective, and target
   evaluation partitions are disjoint under scaffold and exact-identity checks.
8. **Failure separation.** Docking, dependency, timeout, and infrastructure
   failures remain failure classes rather than scientific reward zero.
9. **Cost feasibility.** Oracle throughput, storage, and generation cost permit
   all environments, seeds, and budgets under one matched contract.

A failed gate produces a bounded qualification result. It does not authorize
post-hoc threshold changes or outcome-informed fixture replacement.

## Measurements

The pre-RL measurement record includes:

- admitted signal density and mixed-group probability
- effective support over scaffolds, ring systems, reaction families, and routes
- graph size, degree, connectivity, and route-depth distributions
- valid action, valid product, and successful docking rates
- reward distribution and probe-view reliability
- generated-molecule count, oracle calls, wall time, and docking cost
- target affinity as a nested challenger when it can be measured independently
  of downstream RL outcomes.

Every coordinate must be computable before claim-bearing post-training. New
coordinates require a definition, reliability audit, collinearity audit, and
environment-level holdout test before entering a primary predictor.

## Evaluation and forecast scoring

The primary downstream metric is the fraction of unique generated molecules
that satisfy a frozen docking and drug-likeness criterion on the held-out target
panel. Supporting metrics include top-100 docking score, molecular and scaffold
diversity, uniqueness, reaction validity, route length, and docking-failure
rate. Known LIT-PCBA ligands provide an oracle check using enrichment factor at
1 percent and
[BEDROC](https://pubs.acs.org/doi/abs/10.1021/ci600426e) rather than a training
target.

Prediction and selection are reported separately:

- whole-curve RMSE, MAE, bias, and interval coverage on held-out environments
- improvement-sign and budget-dependent ranking accuracy
- correct best-environment decisions at prespecified budgets
- allocation regret against fixed-environment, compute-only, reward-only,
  cost-only, and graph-agnostic baselines
- risk-coverage behavior when predicted differences are small
- task, environment, and training-seed uncertainty as distinct quantities
- incremental value of the graph-aware selector over the operational selector.

Low retrospective error is insufficient. The central result is whether
measurements made before post-training support a better environment decision on
the two prospective environments than credible cheap alternatives.

## Evidence boundary and next stage

Eight environments can establish feasibility and provide an initial prospective
test. They cannot validate a universal law for molecular design, drug discovery,
or biology. The first result should be stated in terms of the frozen starting
policy, target, environment family, and compute range.

Expansion requires reproducible environment-dependent utility, reliable pre-RL
measurements, adequate uncertainty coverage, and a prospective
selection result that improves on strong operational baselines. A later study
may add protein targets, policy scales, or independent reaction systems one at a
time. It should not expand all axes before the first utility loop is complete.

The immediate deliverables are:

- a source, version, and license registry
- a frozen target and scaffold-separated partition manifest
- warm-start and oracle qualification reports
- eight content-addressed environment specifications
- development and prospective forecast records
- matched post-training and evaluation contracts
- compact prediction, decision, and uncertainty results
- a reproducible graph-aware analysis

The public claim remains proportional to the evidence. The study either shows
that pre-RL graph and reward measurements improve a real molecular
environment-selection decision, or it identifies which measurements fail and
what information a useful predictor still requires.
