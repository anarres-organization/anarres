# Predicting MLIP post-training utility for phonons

**Status:** the complete development and prospective sequence is scored. The
study contains 16 equal-cost environments, 32 training trajectories, and 4,000
physical phonon evaluations. Development model selection produced promising
held-out-environment results, but the frozen learned predictor failed on the
four prospective environments. Prespecified deterministic baselines selected
the best prospective environment at every budget. The released audit traces
the miss to an unsupported extrapolation by the selected signal-density model.

## Research question

Given one pretrained interatomic potential, a fixed post-training budget, and a
named phonon target, can measurements made before post-training predict which
configuration distribution will produce the greatest physical improvement?

This experiment fine-tunes an interatomic potential on energies, forces, and
stresses, then evaluates the resulting model on harmonic phonons and dynamical
stability. This fixed workflow measures physical behavior beyond accuracy on
the post-training labels.

The released study supports both pre-outcome measurement and scored-result
inspection. The CLI exports continuous profiles for all 16 candidate
environments, reports the frozen environment-selection and target-regression
protocol, and verifies the artifact chain from measurements through the
prospective score. The frozen forecast remains unchanged.

## Source and target separation

The construction reservoir is the public OMat24 1M split. It contains PBE
energy, force, and stress labels across rattled structures, relaxation frames,
and molecular-dynamics configurations. The target is the independently
released Alexandria PBE phonon benchmark from *Universal machine learning
interatomic potentials are ready for phonons*. That release contains 9,958
materials and preserves both dynamically stable and unstable systems.

Material identity requires a stricter separation than dataset name alone. Most
Alexandria PBE materials also occur in the Materials Project trajectories used
to pretrain common foundation potentials. The official Nequix/PFT audit
identifies 91 Alexandria IDs absent from MPtrj. We reserve those materials for
the claim-bearing study and assign them, by outcome-blind hash, to 16 checkpoint-
qualification, 25 development, and 50 prospective targets. The complete 9,958-
material release remains useful for retrospective comparison but does not define
the prospective claim.

The shared PBE+U level of theory supports compatibility, while qualification
also records pseudopotentials, energy references, stress conventions, element
support, and structural overlap between the OMat24 reservoir and the target.
Examples that fail this contract remain separate or are excluded by a rule
fixed before candidate construction.

Candidate construction excludes every OMat24 record with the same reduced
composition as any frozen target. This chemistry-level rule is deliberately
broader than structural identity and can remove unrelated polymorphs. It avoids
using a distorted, molecular-dynamics, or relaxation-derived configuration from
the target composition while preserving more than 99.98% of the reservoir.

## Research-first progression

The study advances through five gates.

1. **Qualify the sources.** Pin the OMat24 and Alexandria artifacts, verify
   record counts and checksums, recover units and metadata, and audit material
   identity and level-of-theory compatibility.
2. **Qualify the starting model.** Compare a small prespecified checkpoint
   shortlist on support, fine-tuning behavior, inference cost, curvature access,
   and headroom on the 16-material qualification split. This gate selects one
   common checkpoint without using any candidate-environment training outcome.
3. **Measure and freeze candidates.** Construct a broad bank of equal-cost
   OMat24 distributions, measure each under the starting model, and select
   development and prospective environments from their coordinate geometry.
4. **Run matched post-training.** Train every selected environment with the
   same initialization, loss, trainable parameters, optimizer, processed-atom
   budget, checkpoint schedule, and seed policy.
5. **Score the held-out decision.** Fit compact predictors with complete
   development environments held out, freeze the prospective curves and
   allocation rule, then open the untouched environment outcomes.

A failed gate produces a bounded qualification result. Candidate thresholds,
environment membership, and evaluation fixtures are not repaired after
post-training outcomes are observed.

[`PANEL_REGENERATION_PYPROJECT.toml`](PANEL_REGENERATION_PYPROJECT.toml)
preserves the workspace project definition recorded by the byte-identical
panel regeneration receipt. The active workspace may add domain packages
without changing that locked solver record.

[`DECISION_AND_REGRESSION_PROTOCOL.json`](DECISION_AND_REGRESSION_PROTOCOL.json)
fixes the next decision before candidate training. It records a literature-
derived baseline ranking, the development-to-prospective fitting sequence, and
the metrics used to separate curve prediction from allocation quality. It also
defines a target-level regression as phonon-frequency error that increases by
more than the five-percent practical-equivalence boundary relative to the
common starting checkpoint. Stability and workflow-validity regressions remain
separate endpoints. The regression model uses only starting-checkpoint,
candidate, and target measurements available before candidate training.

## Candidate bank

Candidate distributions are assembled from one pinned OMat24 reservoir. The
bank crosses source regime with outcome-blind selection rules rather than
assigning one universal direction to coverage. Planned source regimes include
the three rattled Boltzmann-sampling temperatures, relaxation stages, AIMD
temperatures, and NVT or NPT trajectories. Planned selection rules include:

- deterministic hash-uniform sampling
- local chemical-environment coverage
- frozen latent-representation coverage
- starting-model force-error or disagreement strata
- curvature-oriented displacement and strain coverage
- target-affinity selection against a calibration-only phonon split
- prespecified hybrids of signal, coverage, and target affinity.

Recent matched-budget OMat24 evidence motivates this design. At roughly 6.5
million training atoms, local-environment coverage leads on bulk MatPES energy,
force, and stress outcomes, while latent-space coverage leads on the
corresponding non-bulk outcomes. Coverage type and target affinity therefore
remain separate measured coordinates.

Each final candidate satisfies a common processed-atom budget and exact
neighbor-edge cost. Material identities are split before configurations are
sampled. Pairwise overlap, chemical-system support, prototype support, force
regime, and source composition are serialized before training.

The measurement pool contains 10,000 hash-selected records from each of eight
physical source families. Rattled full and subsampled shards are treated as one
family at each Boltzmann temperature. A four-record parent cap prevents long
trajectories from dominating. The resulting 80,000 records contain 2.04 million
atoms and 77,677 distinct parents. This pool balances record count for
measurement; claim-bearing training environments will instead match processed
atoms and report neighbor-edge cost.

## Starting-model shortlist

The clean shortlist contained MACE-MP-0b3 and Nequix-MP-1. Both are
MIT-licensed PBE+U models pretrained on MPtrj rather than OMat24, and both
support the 89-element inorganic domain. OMat24-trained checkpoints are strong
deployment baselines but are not eligible as the primary starting point because
they have already trained on the candidate reservoir. Nequix additionally
provides analytical energy Hessians, which permits a direct curvature diagnostic.
The checkpoint gate uses only the qualification targets and operational
criteria. Candidate post-training outcomes do not enter the choice.

Nequix-MP-1 is the selected checkpoint. The completed comparison and model
hashes are recorded in
[`CHECKPOINT_QUALIFICATION.json`](CHECKPOINT_QUALIFICATION.json).

## Pre-training measurements

The compact primary representation contains quantities available before
candidate post-training:

- usable energy, force, and stress signal per processed atom
- effective coverage over frozen local environments and model representations
- force, displacement, strain, and source-regime coverage
- curvature error or disagreement on the qualification structures
- target affinity to the calibration-only phonon panel
- measurement reliability across independent candidate views
- atoms, neighbor edges, wall time, memory, and reference-label cost.

Ensemble disagreement remains a challenger. Curvature is retained as a named
measurement because recent phonon fine-tuning results show that low pointwise
energy, force, and stress error need not imply an accurate potential-energy
Hessian. It enters the primary representation only if it is reliable across
independent views, improves complete-environment holdouts, and changes a
prespecified decision.

## Outcomes

The primary outcomes are computed on the frozen MPtrj-unseen Alexandria PBE
panel:

- phonon-frequency error on valid modes
- dynamical-stability classification
- imaginary-mode rate and maximum imaginary frequency
- phonon density-of-states distance
- relaxation success and structural error.

Energy, force, and stress error are mechanism diagnostics. They do not replace
the physical target. Curve prediction and allocation are scored separately
using whole-curve error, pairwise ordering, interval coverage, best-environment
decisions, and allocation regret against random, fixed-environment, coverage-
only, signal-only, and target-affinity-only rules.

## Compute qualification

The complete 9,958-material benchmark is retained as a retrospective reference.
Claim-bearing training curves use the 25-material development and 50-material
prospective panels from [`TARGET_ROLES.json`](TARGET_ROLES.json). Their
composition was frozen from material identity alone before checkpoint scoring,
candidate construction, or candidate training.

The physical workflow follows the released Alexandria implementation. It
relaxes the unit cell, reuses each reference supercell and primitive matrix,
evaluates 0.01 Angstrom finite displacements, removes net force drift, and
symmetrizes the resulting force constants. The qualification timing establishes
the cost of scoring each later checkpoint without changing either target panel.

The bounded checkpoint qualification established the released phonon workflow,
runtime, and starting model. Full candidate training begins only after the
candidate bank, overlap exclusions, environment memberships, seed policy, and
evaluation matrix are frozen within the available compute and storage budget.

[`materialize_candidate_environment.py`](materialize_candidate_environment.py)
turns a frozen candidate into an ASE-LMDB training database. It indexes the
measured 80,000-record pool, preserves the serialized membership order, and
verifies the candidate's membership hash and atom budget before writing any
training data. This keeps the data consumed by fine-tuning identical to the
environment described by the released pre-training measurements.

[`TRAINING_QUALIFICATION_PROTOCOL.json`](TRAINING_QUALIFICATION_PROTOCOL.json)
records the next gate. Three learning rates are tested on one discarded
measurement-only candidate, with no phonon target used for selection. The
qualified contract then trains each final environment for four matched passes
with two data-order seeds and saves one checkpoint per pass. The accompanying
Nequix patch exposes the existing loader seed and per-epoch checkpoint state
without changing the upstream loss or optimizer.

[`TRAINING_QUALIFICATION_RESULT.json`](TRAINING_QUALIFICATION_RESULT.json)
closes that gate. All three learning rates produced finite gradients and
reloadable checkpoints under the frozen E/F/S contract. Relative to the
starting checkpoint's 5.256 held-out loss, the reloaded checkpoints reached
5.153, 5.030, and 4.813 at learning rates $10^{-5}$, $3\times10^{-5}$, and
$10^{-4}$. The prespecified rule therefore selects $10^{-4}$. The discarded
candidate is absent from the final panel, and no phonon target or final-candidate
training outcome enters this choice.

[`STARTING_CHECKPOINT_TARGETS.json`](STARTING_CHECKPOINT_TARGETS.json) records
the pre-training target features for all 25 development and 50 prospective
materials. Each record includes starting frequency error, dynamical-stability
classification, signed distance to the released stability boundary, and
workflow validity under one shared model and phonon contract. These are model
inputs for later regression prediction, not post-training outcomes.

[`FINAL_TRAINING_CONTRACT.json`](FINAL_TRAINING_CONTRACT.json) binds the frozen
panel, target roles, starting-target features, qualification result, Nequix
patch, and configuration generator. It fixes four equal-cost passes, two data-
order seeds, checkpoints after every pass, and the development-to-prospective
sequence.

[`TARGET_REGRESSION_FEATURES.json`](TARGET_REGRESSION_FEATURES.json) records
1,200 candidate-target feature rows without using candidate-training outcomes.
They combine each target's starting-checkpoint state with chemical support and
nearest-neighbor affinity to each candidate environment.

[`DEVELOPMENT_MODELING_PROTOCOL.json`](DEVELOPMENT_MODELING_PROTOCOL.json)
binds those features to the complete-environment cross-validation, model
selection, uncertainty, allocation-baseline, and regression-control rules. The
development matrix contains 2,400 physical evaluations across 12 environments,
two seeds, four checkpoints, and 25 targets.

[`AGGREGATE_UTILITY_FIT.json`](AGGREGATE_UTILITY_FIT.json) selects the
signal-density response surface. In leave-one-environment-out evaluation, it
achieves 0.071 THz curve RMSE, 85.6% pairwise ordering accuracy, and 0.005 THz
mean allocation regret. Exact best-environment recovery is 0/4, so curve
prediction and decision quality remain separate results.

[`TARGET_REGRESSION_FIT.json`](TARGET_REGRESSION_FIT.json) selects the full
numeric target model. It reaches 0.845 ROC AUC, 0.911 average precision, and
0.161 Brier score when predictions from complete held-out environments are
pooled. The environment-macro ROC AUC is 0.597, which reports discrimination
within each held-out environment before averaging across the 12 folds. Starting
frequency error alone reaches 0.149 pooled ROC AUC under the same split.

[`PROSPECTIVE_TRAINING_AUTHORIZATION.json`](PROSPECTIVE_TRAINING_AUTHORIZATION.json)
binds four utility curves, 16 budget points, and 200 target-regression
probabilities before prospective training. The selected model predicts
`rattled-relax__low_signal` at every pass, while the deterministic allocation
baselines select `aimd-from-PBE-3000-npt__target_affinity`. The held-out run
therefore tests a decision on which the learned predictor and simple rules
disagree.

## Prospective result

[`PROSPECTIVE_OUTCOMES.json`](PROSPECTIVE_OUTCOMES.json) records all 1,600
prospective evaluations across four environments, two training seeds, four
checkpoints, and 50 untouched materials. Every environment reduces aggregate
phonon utility relative to the common starting checkpoint. The target-affinity
AIMD environment is least harmful at all four budgets.

[`PROSPECTIVE_PREDICTION_SCORE.json`](PROSPECTIVE_PREDICTION_SCORE.json) scores
the frozen forecasts. The learned aggregate predictor reaches 0.130 THz curve
RMSE, 45.8% pairwise ordering accuracy, 0/4 best-environment decisions, and
0.135 THz mean allocation regret. Each applicable deterministic baseline
selects the target-affinity AIMD environment at all four budgets and has zero
regret. The target-level regression model reaches 0.494 ROC AUC on 200
environment-material pairs. Regression prevalence is 89.5%, so its 0.881
average precision does not indicate useful discrimination.

[`POST_PROSPECTIVE_AUDIT.json`](POST_PROSPECTIVE_AUDIT.json) preserves this
failed test and examines its boundary. The selected model learned a negative
signal-density coefficient from development data. Its predicted winner has
signal density 21.8% below the development minimum, and that environment
accounts for 80.2% of prospective squared curve error. A support guard would
therefore have abstained at every budget. This guard was specified only after
the prospective result and is recorded as an exploratory sensitivity, not a
prospective success. An exploratory leave-source-family-out audit also
identifies `rattled-relax` as the weak development fold: its 0.211 THz RMSE is
more than twice the error of every other source family. All four prospective
curves lie below zero, so a no-training option would have been optimal at every
budget. The next test must freeze support-aware abstention, include no training
as an allocation option, and expand the development panel to cross source
regime with signal density before evaluating another candidate family.

## Qualification completed

[`SOURCE_QUALIFICATION.json`](SOURCE_QUALIFICATION.json) records the first
source gate. The pinned OMat24 archive has SHA-256
`789ecc1306575a1652806b339265d7659c57282eeb1b3e3b54ba0e1154938b81` and
contains 1,009,850 training records over 18,803,341 atoms. Its eleven source
regimes match the official 1M split counts.

The Alexandria metadata and displacement archive have SHA-256 values
`5875695dc44166cf4f09888485c4cfebee03494f65b3e1b3b4b4381620e5d752` and
`bdc9f8e93c3d2d11e3c73fcf2c0dd4b0050adae863204c7276eec2e6e0bf6db3`.
All 9,958 metadata identities have displacement records, totaling 354,696
extended-XYZ files. The target contains 8,189 dynamically stable and 1,769
unstable materials under the released PBE definition. A sampled displacement
record contains periodic lattice, species, positions, forces, energy, and
stress fields.

These checks establish artifact identity and structural completeness. The
released OMat24 and MPtrj checkpoints use PBE+U, while the Alexandria PBE
recalculation was designed for compatibility with PBE-trained universal
potentials. Energy-reference and stress-convention compatibility remain gates
before candidate training.

[`CHECKPOINT_QUALIFICATION.json`](CHECKPOINT_QUALIFICATION.json) records the
second gate. MACE-MP-0b3 and Nequix-MP-1 each completed all 16 MPtrj-unseen
qualification materials under the released Alexandria workflow. Nequix-MP-1 was
selected by the frozen primary metric, with 0.344 THz mean frequency MAE versus
0.552 THz for MACE-MP-0b3. It also classified dynamical stability correctly on
16/16 materials, compared with 15/16 for MACE. MACE was faster, but the
frequency-error gap exceeded the prespecified five-percent equivalence band, so
runtime did not enter the decision. This comparison selects a common
initialization and does not estimate candidate-environment utility.

[`OMAT24_TARGET_OVERLAP_AUDIT.json`](OMAT24_TARGET_OVERLAP_AUDIT.json)
records the candidate-reservoir identity gate. The frozen 91-target panel has 90
unique composition and space-group descriptors. The stricter composition-only
rule excludes 109 of 1,009,850 OMat24 training records across 77 parent IDs; 23
of these records also match the target space group. Every remaining record uses
an element supported by Nequix-MP-1, leaving 1,009,741 eligible records.

[`MEASUREMENT_POOL_SUMMARY.json`](MEASUREMENT_POOL_SUMMARY.json) records the
outcome-blind measurement pool. The complete 80,000-record manifest is retained
by its SHA-256 hash. A repeated construction run from the pinned native source
under the recorded environment produced the same bytes. The native manifest is
not committed, so a checkout verifies its recorded identity rather than
independently rebuilding it. Neither training labels nor target outcomes enter
membership.

The exact-record materialization and model-input path also passed a bounded
smoke test. It copied the first 64 frozen records from each source family,
yielding 512 records and 13,248 atoms with finite energy, force, and stress
labels and unique source identities. Nequix-MP-1 evaluated the complete subset
at 33.8 records per second including compilation, with force MAE 0.232 eV per
Angstrom under the planned zero-energy-weight, force-and-stress loss contract.
The materialization, validation, and inference summaries are recorded in
[`MEASUREMENT_SMOKE_512.json`](MEASUREMENT_SMOKE_512.json),
[`MEASUREMENT_SMOKE_512_VALIDATION.json`](MEASUREMENT_SMOKE_512_VALIDATION.json),
and
[`MEASUREMENT_INFERENCE_SMOKE_512.json`](MEASUREMENT_INFERENCE_SMOKE_512.json).
This qualification establishes the measurement transport and runtime. It does
not compare candidate environments or use a phonon target outcome.

[`FULL_MEASUREMENT_VALIDATION.json`](FULL_MEASUREMENT_VALIDATION.json) records
the complete starting-model measurement gate. All 80,000 records and 2,035,803
atoms have contiguous identities, finite measurements, matching atom counts,
and one common Nequix-MP-1 hash. The eight source families span signal density
from 5.26 to 17.37 per processed atom and normalized effective signal coverage
from 0.016 to 0.401. The measurement files remain represented by their
individual SHA-256 hashes rather than being added to the repository.

[`CANDIDATE_BANK_DRAFT.json`](CANDIDATE_BANK_DRAFT.json) constructs six
outcome-blind selectors within each physical source family: hash-uniform, low
signal, high signal, structural coverage, target affinity, and a joint score.
Every one of the 48 candidates contains exactly 50,000 atoms from unique parent
structures. Across the bank, signal density spans 1.75--32.26 and effective
signal coverage spans 0.014--0.897. Neighbor-edge cost varies from 24.6 to 59.5
per atom, so the final development and prospective panel must tighten or match
this coordinate before memberships are frozen. The draft uses no candidate
training outcome and no development or prospective phonon outcome.

[`verify_candidate_bank.py`](verify_candidate_bank.py) independently rebuilds
the draft from all 80,000 native measurement records. The released audit
recovers every candidate identity, ordered record membership, and membership
hash exactly; recomputed floating coordinates agree within $1.3\times10^{-13}$.

[`FINAL_COST_MATCHED_PANEL.json`](FINAL_COST_MATCHED_PANEL.json) freezes 16
training environments at exactly 50,000 atoms and 2,100,000 Nequix neighbor
edges each. The panel contains two candidates from every source family and
represents every selector two or three times. Twelve environments are assigned
to development, while four environments from distinct sources and selectors
remain prospective. The split uses only pre-training coordinates and frozen
hash rules. Candidate-training and protected phonon outcomes remain sealed.
Regeneration from the recorded native inputs under the locked Python, NumPy,
SciPy, platform, and solver environment produced identical bytes. The MILPs
can admit multiple solutions, so this byte-identity claim is scoped to that
environment. The compact
[`PANEL_REGENERATION_RECEIPT.json`](PANEL_REGENERATION_RECEIPT.json) records the
command, input identities, code and lock hashes, environment, and reproduced
artifact hash. Because the native measurement shards are represented by hashes
rather than committed, a checkout can verify the receipt but cannot rerun the
panel construction without those files. The frozen artifact has SHA-256
`b5d26ea2dbecac0e530e80d470b6079a7ebee46600633f119eb6d94b9048dd52`.

## CLI profiles

[`export_environment_profiles.py`](export_environment_profiles.py) projects
the frozen panel measurements into content-addressed Anarres
profiles. It verifies the exact source, model, target-role, overlap,
measurement, and candidate-bank artifacts before writing any output. The
profiles expose only measurements made before candidate training. Phonon
outcomes, forecasts, and candidate rankings remain in their native study
records.

After `make setup`, install the native command and the study-local adapter from
the repository root:

```bash
cargo install --path crates/anarres-cli --locked
uv tool install \
  ./experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter

anarres adapter doctor materials
anarres materials status --repository .
anarres inspect \
  experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter/fixtures/omat24-qualification-slice-v1
anarres qualify \
  experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter/fixtures/omat24-qualification-slice-v1
anarres materials protocol --repository . --json
anarres materials results --repository . --json
anarres materials profile \
  --repository . \
  --output-dir .anarres/materials-mlip \
  --candidate-id aimd-from-PBE-1000-npt__high_signal \
  --candidate-id aimd-from-PBE-1000-npt__target_affinity

anarres qualify \
  .anarres/materials-mlip/aimd-from-PBE-1000-npt__high_signal.profile-input.json
anarres measure \
  .anarres/materials-mlip/aimd-from-PBE-1000-npt__high_signal.profile-input.json \
  --output .anarres/materials-mlip/high-signal.profile.json
anarres measure \
  .anarres/materials-mlip/aimd-from-PBE-1000-npt__target_affinity.profile-input.json \
  --output .anarres/materials-mlip/target-affinity.profile.json
anarres design \
  .anarres/materials-mlip/high-signal.profile.json \
  .anarres/materials-mlip/target-affinity.profile.json
anarres validate \
  .anarres/materials-mlip/high-signal.profile.json \
  .anarres/materials-mlip/target-affinity.profile.json
```

The native source fixture contains two OMat24 configurations and the
complete atomistic-bank contract. Qualification checks structure validity,
energy, force, and stress units, source and material identities, atom and
neighbor-edge totals, the Nequix checkpoint and calculator revisions, and the
Alexandria evaluation exclusions. The fixture is limited to source
qualification. Its metadata pins the complete 80,000-record measurement bank
through the released construction script, selection parameters, overlap audit,
and resulting manifest digest. It also pins the upstream OMat24 archive by URL,
size, license, and SHA-256 digest.

The portable adapter does not run the Nequix pre-training probe. That probe
requires the native GPU, ASE-LMDB, and checkpoint runtime used by the study.
The checked-in profile exporter remains the supported path for the completed
80,000-record measurements. Source qualification does not read candidate
training outcomes.

Omitting `--candidate-id` exports all 16 final candidates. The corresponding
[measurement convention](../../../../docs/conventions/materials-mlip-candidate-measurement-v2.md)
defines every coordinate, unit, estimator, and edge case. The earlier
[development convention](../../../../docs/conventions/materials-mlip-candidate-measurement-v1.md)
remains available for the 48-candidate measurement bank.

`anarres materials protocol` reports the frozen outcome-blind baseline,
development-to-prospective fitting sequence, selection metrics, regression
endpoints, negative controls, and bound artifact hashes. `anarres materials
results` verifies and reports the scored prospective test. It keeps the frozen
result separate from the exploratory support audit.

The adapter can be invoked from outside the checkout by passing the repository
explicitly with `--repository`. Its `profile` command preserves the original
pre-training measurement boundary, while `results` opens only the released
prospective score and its labeled post-test audit. The generic installation and
execution contract is documented in the [CLI guide](../../../../docs/cli.md).

## Primary sources

- [OMat24 dataset and paper](https://huggingface.co/datasets/facebook/OMAT24)
- [Alexandria PBE phonon benchmark](https://alexandria.icams.rub.de/data/phonon_benchmark/)
- [Universal machine learning interatomic potentials are ready for phonons](https://doi.org/10.1038/s41524-025-01650-1)
- [MACE foundation models and fine-tuning code](https://github.com/ACEsuit/mace)
- [Nequix and phonon fine-tuning](https://github.com/atomicarchitects/nequix)
- [PFT: Phonon Fine-tuning for Machine Learned Interatomic Potentials](https://proceedings.mlr.press/v306/koker26a.html)
- [Atoms that Matter](https://arxiv.org/abs/2610.14392) and its [released workflow](https://github.com/em819/omat24-chemenv-subset)

Exact revisions, content hashes, licenses, and qualification results are
recorded in this directory as each gate closes.
