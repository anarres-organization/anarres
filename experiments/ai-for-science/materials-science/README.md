# Predictable post-training for atomistic materials models

Atomistic datasets can be expensive to label and train on, while equal-size
subsets can produce different physical outcomes. This program asks a concrete
question:

> Can measurements made before post-training predict which atomistic training
> environment will produce the greatest improvement for a specified model,
> physical target, and compute budget?

## Results and current work at a glance

| Study | Status | Public result or current gate |
| --- | --- | --- |
| [Supervised phonon selection](phonon-environment-selection/) | Complete | The frozen signal-plus-coverage rule missed the best candidate at all three PBE budgets, establishing that the initial measurements were insufficient. |
| [Independent PBEsol transfer](phonon-environment-selection/pbesol-transfer/) | Complete | The transferred ordering selected the best candidate at two of three budgets, while no post-trained candidate improved absolute Top-100 stability over the starting checkpoint. |
| [Retrospective materials bridge](retrospective-bridge/) | Validated | Sixteen public studies provide 804 matched decisions and 3,002 candidate arms. A separate harm audit reaches 0.708 source-macro ROC AUC and captures 41.8% of adverse choices in the highest-risk 20% of pairs. |
| [MLIP phonon study](mlip-phonon-environment-selection/) | Candidate bank under domain review | The starting model and target roles are frozen, 80,000 structures have been measured, and 48 equal-atom candidate environments have been constructed without opening any candidate training outcome. |

## Current external-review handoff

The MLIP phonon study is the current prospective workstream. Its next decision
is which 12 development and four prospective environments to freeze from the
48-candidate draft. Domain review is focused on four questions: whether the
source families cover the physical regimes that matter for phonons, whether
composition-level target exclusion is appropriate, whether both processed
atoms and neighbor edges should define matched cost, and whether the proposed
target-affinity and curvature measurements capture the relevant transfer
mechanism. The complete measurement gate and candidate coordinates are linked
from the [study page](mlip-phonon-environment-selection/).

## Purpose

This page defines the materials-science research program in Anarres. The
program began with a supervised phonon-scoring study over an already
labeled DFT reservoir. Its next phase focuses on universal machine-learned
interatomic potentials (MLIPs). These models approximate the potential-energy
surface of an atomic system and enable structural relaxation, molecular
dynamics, response-property calculation, and candidate screening at scales that
are impractical with direct quantum calculations.

The scientific object remains

$$
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D),
$$

where $E$ is a distribution over atomistic configurations, $\pi_0$ is a
common pretrained potential, $C$ is a matched training or reference-label
budget, and $D$ is a frozen physical target. The aim is to forecast environment
utility for a named model, target, and budget, with no assumption that one
materials dataset is universally optimal.

Claim-bearing runs require a versioned study contract after source,
level-of-theory, split, starting-model, measurement, and evaluation
qualification.

The first prospective research loop is complete in
[`phonon-environment-selection/`](phonon-environment-selection/). It uses a
released phonon-scoring model and DFT post-training pool to compare random,
model-relative signal, coverage, and joint selection under sealed external
evaluation. Its prospective
[`pbesol-transfer/`](phonon-environment-selection/pbesol-transfer/) follow-up
tests whether the PBE environment ordering transfers to an independently
frozen PBEsol workflow. These supervised studies establish the measurement and
decision workflow before the broader interatomic-potential experiment below.

The supporting [`retrospective-bridge/`](retrospective-bridge/) reconstructs
804 matched decisions and 3,002 candidate arms from sixteen public studies. It
tests recurring measurements under source-specific grouped holdouts and then
holds out each complete study. Directionally aligned signal, coverage, and
target-relevance concepts transfer better than an uninformed rule. A separate
relative-harm audit holds out 13 complete studies and tests whether the same
measurements identify environments that underperform a matched reference. The
fixed semantic score reaches 0.708 source-macro ROC AUC and recovers 41.8% of
adverse choices in the highest-risk 20% of pairs. Flexible fitted models remain
weaker than the compact scores in both audits. These results narrow the
prospective hypothesis without opening the sealed phonon evaluation. Additional
studies remain outside the predictor. They
quantify random-subset variability, show architecture-dependent environment
rankings, recover a sampling-rule reversal between scratch retraining and
fine-tuning, compare pretrained fine-tuning with random initialization on
matched surface datasets, and show how training-structure size changes phonon
accuracy under several adaptation regimes. A catalysis audit further shows that
MD and bond-breaking configurations have different value under scratch training
and foundation-model fine-tuning. A matched-budget OMat24 audit finds that
interpretable environment coverage leads on bulk MatPES outcomes, while
pretrained latent-space coverage leads on non-bulk outcomes.

## Why materials science is a distinct domain test

Atomistic post-training changes the structure of the environment-utility
problem. A training example may contain one energy, three force components per
atom, and a stress tensor. Configurations from the same relaxation trajectory
are correlated, and downstream performance depends on chemistry, geometry,
displacement from equilibrium, strain, force regime, and level of theory.

A low average energy or force error does not imply reliable phonons, reaction
barriers, defects, dynamics, or stability decisions. The target physical task
therefore has to be fixed before the environment is selected.

The shared workflow is:

```text
starting atomistic model + physical target + compute budget
    -> qualify sources, labels, units, and reference calculations
    -> measure candidate configuration distributions under the starting model
    -> forecast target-specific improvement and uncertainty
    -> freeze development and prospective environments
    -> fine-tune under matched atom and update budgets
    -> evaluate on a disjoint physical target panel
    -> score prediction and environment-selection quality
```

## Frontier relevance

The plan builds on current public work in atomistic foundation models, materials
generation, task-level evaluation, and reinforcement learning. These components
have different roles and should not be treated as one benchmark.

| Component | Evidence of relevance | Role in the study |
| --- | --- | --- |
| [M3GNet](https://arxiv.org/abs/2202.02450) | Universal graph interatomic potential trained on Materials Project relaxation trajectories | Scientific baseline and evidence that energies, forces, and stresses provide complementary supervision |
| [MACE-MP](https://github.com/ACEsuit/mace) | Open equivariant foundation potential with an active fine-tuning ecosystem | Proposed first starting-model family, subject to qualification |
| [OMat24](https://arxiv.org/abs/2410.12771) | More than 110 million open DFT calculations emphasizing structural and compositional diversity | Candidate source for off-equilibrium and diverse inorganic configurations |
| [Atoms that Matter](https://arxiv.org/abs/2610.14392) | EnvTok, DIRECT, and four random OMat24 subsets trained at roughly 6.5 million atoms | Matched-budget evidence that the value of coverage depends on the physical target distribution |
| [UMA / FAIRChem](https://github.com/facebookresearch/fairchem) | Multi-domain atomistic foundation model trained across materials, molecules, and catalysts | Frozen frontier comparator and later transfer test |
| [Matbench Discovery](https://arxiv.org/abs/2308.14920) | Task-level benchmark for thermodynamic-stability decisions | Evidence that generic regression error can disagree with the downstream decision |
| [MatterGen](https://arxiv.org/abs/2312.03687) | Property-conditioned generative model for inorganic materials | Later generator family rather than the first utility study |
| [Open Catalyst](https://opencatalystproject.org/) | Large public DFT datasets for surfaces, adsorbates, and catalyst discovery | Second target family and pathway-oriented replication |
| [OMatGRPO](https://arxiv.org/abs/2610.03880) | GRPO over a crystal generator with documented reward exploitation and DFT checks | Proposed materials-RL extension |

This evidence establishes scientific and methodological relevance. It does not
establish that the planned environment predictor works. Every source version,
license, checkpoint, data transformation, and evaluation implementation must be
qualified before use.

## Broader MLIP target: phonons and dynamical stability

The implementation and current qualification state are tracked in
[`mlip-phonon-environment-selection/`](mlip-phonon-environment-selection/).

The first claim-bearing target is harmonic phonon and dynamical-stability
prediction. Phonons are physically important for vibrational and thermal
behavior and probe local curvature of the potential-energy surface rather than
only equilibrium energies.

This target is informative because current universal potentials can perform well
on equilibrium energy and force metrics while producing poor or imaginary
phonon modes. The open study [*Universal machine learning interatomic potentials
are ready for phonons*](https://www.nature.com/articles/s41524-025-01650-1)
provides a PBE-compatible DFT benchmark over approximately 10,000
semiconductors. Separate work on [systematic softening in universal
MLIPs](https://www.nature.com/articles/s41524-024-01500-6) links errors in
phonons, barriers, defects, surfaces, and high-energy states to biased sampling
near equilibrium.

The phonon target is a first diagnostic, not a universal definition of materials
utility. A separately frozen replication should target catalytic transition
states or reaction barriers after the first environment-utility loop is
complete.

## Broader MLIP starting model and comparators

The qualified shortlist contained MACE-MP-0b3 and Nequix-MP-1, two PBE+U
potentials pretrained on MPtrj rather than the OMat24 candidate reservoir.
Nequix-MP-1 is the selected common starting checkpoint. It achieved lower
phonon-frequency error on the frozen 16-material qualification split and
provides analytical energy Hessians for the planned curvature diagnostic. The
selection used no candidate-environment training outcome.

Recent work on [frozen transfer learning for foundation
potentials](https://www.nature.com/articles/s41524-025-01727-x) shows that
partially frozen fine-tuning can reach task-specific accuracy with a fraction
of the original reference data. MACE remains a qualified comparator, while a
pinned UMA checkpoint is reserved for a later external transfer test under its
own model and task-embedding contract.

## Broader MLIP data sources and target separation

The source registry should qualify Materials Project relaxation trajectories,
OMat24, and any derived displaced or strained structures. A PBE phonon dataset
remains evaluation-only.

The study separates five roles:

1. **Construction reservoir:** source configurations from which candidate
   environments are assembled.
2. **Measurement views:** independent samples used to estimate pre-training
   coordinates and reliability.
3. **Target calibration:** a small split used only for prespecified
   target-affinity measurements.
4. **Development evaluation:** target structures used to fit and compare compact
   predictors.
5. **Prospective evaluation:** untouched target structures and environments used
   only after the predictor and decision rule are frozen.

Material identity is split before trajectory frames are sampled. Exact
structure, reduced formula, chemical system, prototype, and structural
similarity are audited across partitions. Starting-model pretraining exposure is
reported separately from fine-tuning leakage; a public foundation model may have
seen related Materials Project structures even when the fine-tuning experiment
is internally disjoint.

## Broader MLIP candidate environments

Candidate environments are equal-budget mixtures drawn from one frozen source
reservoir. They may vary:

- early, middle, and converged relaxation frames
- equilibrium, lightly displaced, and strongly off-equilibrium structures
- unstrained and cell-strained configurations
- low-force and high-force regimes within frozen validity bounds
- broad and target-neighbor chemical systems
- broad and target-neighbor structural prototypes
- random, diversity-selected, uncertainty-selected, and
  target-affinity-selected acquisition;
- the balance of energy, force, and stress-bearing configurations.

Coverage is not assigned one universal direction. Released OMat24 comparisons
show that local-environment coverage can lead on bulk outcomes while latent-
space coverage leads on non-bulk outcomes at the same training-atom budget.
The candidate bank therefore crosses coverage type with target affinity and
retains both as measured coordinates rather than treating either selector name
as an ordered feature.

These are predictive contrasts, not isolated causal interventions. Chemistry,
geometry, force regime, and source can remain coupled even when their continuous
measurements are reported separately.

The current measurement-only draft contains 48 equal-atom candidate
distributions. Before fine-tuning, the study will select 12 development and four
prospective environments that span the measured coordinates, limit pairwise
overlap, preserve multiple source families, and avoid one source label acting
as a proxy for every coordinate.

## Broader MLIP pre-training measurements

Every primary coordinate must be computable before claim-bearing fine-tuning and
must pass independent-view reliability and collinearity checks.

### Primary operational coordinates

- **Admitted supervision density $\rho$:** usable energy, force, and stress
  gradient mass per atom and per unit of acquisition or training cost.
- **Effective coverage $H$:** concentration-adjusted support over frozen local
  atomic-environment embeddings, elements, chemical systems, prototypes, and
  force regimes.
- **Reliability $R$:** agreement of the coordinates across independent views
  of the same candidate distribution.
- **Cost $K$:** processed atoms, neighbor edges, wall time, memory, and
  equivalent reference-label cost.

### Nested challengers

- **Target affinity $\alpha_D$:** similarity between candidate-environment
  gradient or representation sketches and the target calibration split.
- **Curvature coverage $\kappa$:** support across displacement magnitude,
  force norm, strain, and prespecified local-curvature proxies.
- **Epistemic disagreement $Q$:** disagreement among a pinned ensemble of
  frozen potentials.

Curvature coverage is motivated by a documented potential-energy-surface
failure, but it remains a challenger until it adds environment-level predictive
value. No challenger enters the primary predictor because it improves an
in-sample regression. It must be reliable, improve held-out-environment
prediction, and change at least one prespecified decision.

## Broader MLIP experiment

The initial experiment uses 12 development and four prospective environments,
two training seeds, and three matched budgets. Every run uses:

- the same starting checkpoint
- one pinned energy-force-stress loss and observable weighting
- the same trainable parameter groups
- the same optimizer, precision, batching, and checkpoint schedule
- matched processed-atom and optimizer-update budgets
- the same disjoint physical evaluation panel.

A third seed is reserved for decision-critical near ties or anomalous variance;
it is not selected after seeing which result is preferable.

Compact predictors are fit with entire environments held out. The study does not
train a high-capacity neural utility model on 12 independent environments.
Regularization and model selection remain inside each development fold.

## Evaluation and forecast scoring

The primary downstream outcomes are physical task metrics:

- phonon-frequency error on valid modes
- dynamical-stability classification and imaginary-mode rate
- phonon density-of-states distance
- geometry-relaxation success and structural error
- catastrophic relaxation or molecular-dynamics failure rate.

Energy, force, and stress error remain supporting diagnostics. They cannot
replace the target metric.

Prediction and decision quality are reported separately:

- whole-curve RMSE, MAE, bias, and interval coverage on held-out environments
- improvement-sign and budget-dependent pairwise ranking
- correct best-environment decisions at prespecified budgets
- allocation regret against random, source-only, difficulty-only,
  target-similarity-only, uncertainty-only, and fixed-environment baselines;
- risk-coverage behavior when predicted differences are small
- environment, target-structure, and training-seed uncertainty as distinct
  quantities.

The primary prospective test freezes the selector on the 12 development
environments and evaluates the four untouched environments without refitting.
Low retrospective error alone is insufficient.

## Qualification gates

Qualification uses construction and development data only. It cannot inspect
prospective post-training outcomes or replace environments based on downstream
utility.

Before post-training begins, the launch packet must establish:

1. **Source identity and license.** Record stable versions, source licenses,
   dataset identities, preprocessing code, and content hashes.
2. **Reference compatibility.** Record units, pseudopotentials, exchange-
   correlation functionals, Hubbard corrections, energy references, and stress
   conventions. Incompatible labels remain in separate strata.
3. **Identity separation.** Audit exact structures, materials, chemical systems,
   prototypes, and structural similarity across all partitions.
4. **Starting-model headroom.** The common checkpoint is neither at the floor nor
   saturated on the target objective.
5. **Policy-relative signal.** Independent measurement views contain enough
   valid and nondegenerate configurations to estimate the coordinates.
6. **Measurement reliability.** Primary coordinates meet frozen agreement
   thresholds across views.
7. **Panel geometry.** The selected environments span the intended coordinates
   without severe collinearity or excessive overlap.
8. **Training stability.** One broad, one curvature-rich, and one deliberately
   weak environment complete a bounded pilot under the same contract.
9. **Evaluation fidelity.** The target pipeline reproduces a published baseline
   within a frozen tolerance.
10. **Cost feasibility.** The complete environment, seed, and budget design fits
    the compute and storage allocation with operational headroom.

A failed gate produces a bounded qualification result. It does not authorize
post-hoc threshold changes or outcome-informed fixture replacement.

## Materials-RL extension

After the atomistic fine-tuning study establishes a reliable utility loop, a
second study should examine rollout environments for crystal-generation RL.

The first implementation candidate is
[OMatGRPO](https://github.com/paprakash/OMatGRPO), which applies group-relative
policy optimization to the continuous lattice and coordinate channels and the
discrete composition channel of OMatG. Its released study documents several
reward exploits, including single-element structures that satisfied a community
metric without producing new compounds.

The extension asks whether pre-RL measurements predict which composition and
prototype distribution produces the greatest independently verified discovery
utility under a fixed reward and generation budget. Candidate environments may
vary chemical-system support, element count, prototype family, reference-hull
support, frozen-potential disagreement, and target-property region.

The main panel keeps the reward, relaxation method, generator, RL objective, and
evaluation fixed. Reward design is a separate ablation because changing the
rollout distribution and reward semantics together would make utility difficult
to interpret.

The primary outcome is DFT-confirmed yield of stable, novel compounds under a
sufficiently supported reference hull. Supporting analyses include a frozen-
composition control, reward swaps, a second-potential check, prespecified DFT
spot checks, and explicit audits for sparse-hull exploitation, single-element
repacking, invalid relaxation, displacement exploits, and mode collapse.

[CrystalGym](https://github.com/chandar-lab/crystal-gym) may provide a bounded
direct-DFT qualification environment. Full-panel use requires its reset path,
throughput, and reproducibility to pass the same gates.

## Pathway replication

Catalysis is the first pathway-oriented replication. Unlike general solid-state
synthesis, catalytic systems expose intermediates, transition states,
activation barriers, and reaction networks that can be represented and checked
computationally.

The [Open Catalyst 2020 dataset](https://arxiv.org/abs/2010.09990) contains more
than one million DFT relaxations across surfaces and adsorbates.
[OC20NEB/CatTSunami](https://arxiv.org/abs/2405.02078) adds DFT nudged-elastic-
band calculations for transition-state evaluation. A later study can vary
training mixtures over surfaces, adsorbates, reaction families, and
transition-state neighborhoods while holding a frozen reaction-barrier target.

General solid-state synthesis planning is not part of the first experiment.
Structure proposal, computational stability, and an experimentally executable
synthesis route are different claims. Expanding to automated-lab actions
requires experimental observability, reaction-condition metadata, safety
controls, and an independent validation partner.

## Safety and evidence boundary

Materials generation can propose toxic, explosive, environmentally damaging, or
otherwise sensitive compounds. Early studies use public inorganic datasets and
target general physical properties rather than hazardous functionality.
Released artifacts should document composition filters, restricted targets,
reference limitations, and the difference between computational candidates and
experimentally validated materials.

Sixteen environments can establish feasibility and support one prospective
decision. They cannot validate a universal law for materials discovery,
atomistic simulation, catalysis, or synthesis. The first result should be stated
in terms of the frozen starting model, source family, physical target, and
compute range.

The immediate deliverables are:

- a source, version, license, and level-of-theory registry
- a content-addressed partition and contamination report
- a starting-model and target qualification report
- at least 40 measured candidate-environment specifications
- a frozen 12-development/4-prospective panel
- matched fine-tuning and physical-evaluation contracts
- compact prediction, decision, uncertainty, and cost results
- a prospective score record that preserves the chronology of every freeze.

The public claim remains proportional to the evidence. The study either shows
that measurements made before fine-tuning improve a real atomistic-environment
decision, or it identifies which measurements fail and what information a
useful selector still requires.
