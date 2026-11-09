# Retrospective materials environment bridge

**Status:** source qualification and normalization in progress. This is
retrospective evidence, not a prospective forecast.

This bridge asks whether recurring measurements of a materials training
environment predict downstream utility across published studies. It follows the
same progression as the legal and robotics bridges: recover numerical
intervention panels, preserve each study's native outcome, normalize only
within matched decisions, test compact rules under grouped holdouts, and use a
separate sealed experiment for prospective evaluation.

## Inclusion boundary

A study enters the fitted bridge only when all of the following are recoverable:

1. the candidate pool and downstream learning task
2. two or more environment or selection arms at matched label or training cost
3. numerical arm-level outcomes from a table, source-data file, or released
   evaluation artifact
4. the information available when the environment was chosen
5. enough provenance to reproduce the extracted panel

Papers can remain important scientific context without entering the fitted
bridge. Figure digitization is not used when the underlying numerical values
cannot be independently checked.

## Panel definition

A decision panel fixes the study, candidate pool, target property or physical
observable, downstream model, evaluation distribution, and training budget.
Only the environment or selection rule changes within a panel. Native errors
are converted to utility by reversing their sign, then normalized within the
panel. Identifiers such as study, database, material system, and method name
define grouped holdouts and are never predictive features.

The shared semantic coordinates are:

- model-relative information or uncertainty
- structural or compositional coverage
- target relevance
- measurement accessibility
- label and training exposure
- missingness of each measurement

These coordinates are intentionally broader than the phonon study's eventual
model-specific measurements. The retrospective bridge tests which concepts
recur across studies. It does not assume that one coefficient vector transfers
unchanged between property prediction, interatomic potentials, and phonons.

## Qualified evidence

Sixteen sources enter the predictive bridge. Together they contain 828 matched
decision panels and 2,990 candidate arms. Nine additional sources audit
selection uncertainty, model–environment compatibility, and training-regime
dependence without entering the predictor.

- **Li et al. (2023)** release learning curves for random sampling, query by
  committee, random-forest uncertainty, and XGBoost uncertainty across multiple
  databases, properties, and downstream models. The primary cut uses RMSE at
  2%, 10%, and 20% of each source pool. Outcome-informed pruning remains outside
  the predictive cut.
- **Hänseroth et al. (2026)** release matched 2,000-label training artifacts for
  three universal-potential configuration generators across seven chemically
  distinct systems. The downstream architecture and first-principles budget are
  fixed, making this a direct environment-generator decision.
- **Hänseroth and Dreßler (2026)** release exact errors for trajectory strides
  10 and 100 at the same DFT-label count. The bridge reconstructs 336 matched
  decisions across seven materials, three budgets, scratch training and
  fine-tuning, five frameworks, and separate energy and force endpoints. The
  wider trajectory span wins 213 panels and loses 123, showing a useful but
  material-dependent coverage effect. Reference-trajectory generation cost is
  recorded separately from the matched final label and training budgets.
- **Kulichenko et al. (2023)** independently repeat four active-learning
  environments and cross-test their resulting glycine potentials on all four
  held-out environment distributions. The complete matrix separates coverage
  during data generation from downstream error on a specified target.
- **Dale et al. (2026)** compare random sampling with six uncertainty-based
  acquisition policies across property, omitted-element, and label-budget
  contexts. Twenty-three panels contain all seven arms. Exact released
  histories expose one trajectory per arm, so the bridge does not infer the
  five-repetition error bars reported in the paper.
- **Bi and Elena (2026)** release five-seed outcomes for coverage, response,
  and control selectors at three retained-data budgets on Carbon and pooled
  rMD17. The 24 matched panels preserve four force endpoints but treat the two
  datasets as the scientific holdout groups. Their full-data response witness
  is recorded as a retrospective comparator with a higher measurement cost.
- **Wong and Yang (2026)** release naive and iterative fine-tuning datasets and
  checkpoints at five matched cumulative budgets. We evaluate all ten models
  on the same independent DFT test set and measure both environments with the
  common released starting potential before using any fine-tuned outcome.
- **Baghishov et al. (2026)** release 50 realizations of random, leverage, and
  block-leverage selection at nine matched configuration budgets. Energy and
  force errors are evaluated separately because regular leverage targets the
  energy descriptor row, while block leverage includes force-component rows.
- **Qi et al. (2024)** compare manual and coverage-stratified DIRECT sampling
  at nearly identical 185,877- and 185,670-configuration budgets. Six panels
  cross two held-out environment families with energy, force, and stress error.
  The target-matched arm wins every panel, while DIRECT's broader coverage
  gives lower error when results are averaged across both targets.
- **Zaverkin et al. (2024)** compare random, uncertainty-selected, and
  uncertainty-biased acquisition at a common 512-configuration cap. Eight
  panels cover alanine dipeptide and MIL-53(Al) with three or five independent
  runs per arm. Their adaptive acquisition cost is recorded separately from
  the matched final training-set size.
- **Espinosa Castañeda et al. (2026)** release complete acquisition curves for
  four computed-data repositories and one experimental thermoelectric dataset.
  The bridge reconstructs 256 decisions over targeted and untargeted properties,
  five campaign seeds, and two downstream models. Full-campaign RMSE-AUC keeps
  the 1% acquisition schedule and fixed 10% test sets matched within each panel.
- **Wang et al. (2026)** report exact three-draw learning curves for entropy-
  driven and random-MD environments at four matched configuration budgets on
  carbon, silicon, and NaCl. Forty-five panels retain energy, force, and stress
  separately across common in-distribution tests and independent equilibrium
  and thermal-MD tests. Broad coverage transfers reliably for energy, while
  carbon force and stress expose the importance of target-distribution match.
- **Varga-Umbrich et al. (2026)** report exact transfer gains for pretrained
  representation kernels and committee acquisition across three reactive-
  chemistry datasets. The bridge reconstructs 36 method-versus-random
  decisions over energy and force metrics. Method-specific targets prevent
  direct comparison among acquisition families, so each remains a binary panel.
- **Kim et al. (2026)** release five independent training seeds for three
  equal-size distilled-water environments that vary density and temperature
  support. Twelve shared thermodynamic states are scored from exact RDF arrays
  using the paper's similarity equation. Density-diverse training wins nine
  states, while no-variance training wins three high-density states.
- **Liu et al. (2026)** release five independent ACE fits for six label
  environments on the same 1,139-configuration tungsten support. A threshold
  validated on separate DFT datasets uses about 4% DFT-labeled atomic
  environments and nearly matches the best energy and force arms on an
  independent test set. The comparison holds training exposure fixed while
  recording reference-label cost separately.
- **Lee et al. (2026)** compare random, DIRECT, and initial-aware LCMD sampling
  for sodium-oxide potentials under scratch retraining and fine-tuning. Exact
  diffusivity values reverse the preferred strategy across regimes: LCMD wins
  after scratch retraining, while DIRECT wins after fine-tuning. DIRECT uses
  8,879 DFT labels rather than 8,000, so these panels remain an auxiliary audit;
  normalizing improvement by label count preserves both decisions.
- **Hwang et al. (2026)** release exact learning curves for fine-tuning and
  training from scratch on unary Au, binary RuO$_2$, and ternary BiVO$_4$
  surfaces. Eighteen matched panels cross nine common training-set sizes with
  energy and force RMSE. Fine-tuning wins every panel, but the changed
  initialization and update path make this a training-regime audit rather than
  a fixed-trainer environment comparison.
- **Karimitari et al. (2026)** report exact reaction-energy and activation-
  barrier errors for three from-scratch and six MACE-MH-1 fine-tuning
  environments. MD and contour configurations sharply improve scratch training,
  while their value changes after foundation-model initialization and OMAT
  replay. Different data volumes and update contracts keep the six aggregate
  panels outside the matched-cost predictor.
- **Grandel et al. (2026)** compare primitive-cell, small-supercell, and
  large-supercell fine-tuning data across four adaptation regimes and 53
  materials. Large supercells give the lowest median phonon error in all four
  regimes. Each arm uses ten configurations per material, but the structures
  contain different numbers of atoms, so the four aggregate panels remain a
  cost-sensitive audit outside the matched-cost predictor.
- **Zhang et al. (2023)** compare entropy-targeted and random acquisition at
  the same 1,954-material training-set size. Four panels combine bulk and shear
  modulus with random forest and gradient boosting, using the 30 released fits
  per arm on one common 4,898-material test set.
- **Svahn et al. (2026)** release three random subset realizations at both small
  and medium cluster-data budgets under a common MACE seed. Across eight
  pure-solvent endpoint panels, changing only the selected cluster identities
  shifts absolute density error by as much as 0.070 g/cm$^3$ and absolute
  diffusion error by as much as $9.80\times10^{-6}$ cm$^2$/s. No released
  pre-training measurement distinguishes these subsets, so they quantify
  unresolved selection variability rather than predictor accuracy.
- **Niblett et al. (2025)** release four training environments, five-member
  committees, and common physical evaluations for MACE and DeePMD. The best
  environment for EC/DEC force error changes from OPLS under DeePMD to Full
  under MACE, and DeePMD active learning changes the stability ordering again.
  Because the environments contain 203--935 configurations, these panels
  establish architecture and adaptation dependence without entering the
  matched-cost predictor.
- **Kim et al. (2026)** release an exact cross-domain ablation over MPtrj,
  SPICE, a 0.1% domain-bridging set, and selective task regularization. The
  combined strategy reduces molecular PBE force MAE from 0.157 to 0.048
  eV/Å while retaining similar crystal PBE error. Data membership and the
  optimization contract change together, so the eleven arms audit
  compatibility between data and training without entering the fixed-trainer
  predictor.
- **Moerman et al. (2026)** compare interpretable local-environment coverage,
  pretrained latent-space coverage, and four random OMat24 subsets at a common
  budget of roughly 6.5 million atoms. Six exact MatPES panels separate bulk
  and non-bulk energy, force, and stress outcomes. EnvTok leads all three bulk
  panels, while DIRECT leads all three non-bulk panels, showing that broad
  coverage remains target dependent even at matched training cost. The four
  random subsets retain substantial outcome variation. Because no continuous
  pre-outcome measurement is shared across the six arms, this study audits
  selector behavior and uncertainty without entering the pooled predictor.
- **Kuner et al. (2025)** compare a common MACE architecture trained on
  MP-ALOE, MatPES, and their deduplicated union. MatPES gives the lowest
  equilibrium cohesive-energy error, MP-ALOE gives the most stable
  extreme-temperature NVT trajectories, and the union gives the best static
  compression and high-pressure NPT results. This target-dependent reversal
  is a direct data-environment effect, but the training sets contain different
  numbers of configurations. The four panels therefore remain a
  cost-sensitive audit outside the matched-cost predictor.
- **Schäfer and Kästner (2026)** compare standard molecular dynamics with
  enhanced representation-based sampling in a liquid-water active-learning
  loop. Both arms use the same starting data, model, acquisition rule, sampling
  duration, and number of newly labeled configurations at every iteration.
  The paper reports lower force error and diffusion closer to the shared
  reference for ERBS throughout the run. Exact outputs are public, but the
  relevant metrics are stored inside an 82.6 GB compressed archive member.
  This study remains pending exact extraction rather than entering through
  figure digitization.

These sources are first evaluated separately. Their measurements describe
different objects: acquisition uncertainty, generator mismatch, sampled
configuration coverage, and policy semantics. A pooled analysis can map them
to shared concepts only after source-specific grouped holdouts establish what
each measurement predicts on its native support.

The ZIF SOAP study is currently pending. Its article reports a random-baseline
force MAE of 0.077 eV/Å at 1,000 configurations on the unseen `dia` topology,
while Supporting Table S3 reports 0.066 eV/Å for the same named comparison. No
value from that comparison enters the bridge until the discrepancy is resolved.

The broader audit also covers frozen transfer learning, ASSYST, FALCON,
replica-exchange nested-sampling active learning, information-matched potential
design, fine-tuning-strategy comparisons, and a common unary benchmark for
universal interatomic potentials. These studies strengthen the scientific
basis for candidate construction, adaptation, target-aware measurement, and
evaluation. They remain outside the fitted bridge because exact arm outcomes
are unavailable or the candidate arms change model architecture, label cost,
training weights, or the optimization contract. A four-system active-learning
preprint is excluded until its announced code release and feature provenance
can be verified.

[`SOURCES.json`](SOURCES.json) records the complete eligibility audit, exact
revisions, checksums, licenses, and exclusion reasons.

## Initial grouped-holdout results

The first audit fits each source on its own support, holding out entire task or
material contexts. Outcomes are normalized only within matched decisions.

| Source | Practical rule: ordering / regret | Ridge: ordering / regret | Main finding |
| --- | ---: | ---: | --- |
| Li et al. | 70.7% / 0.326 | 74.8% / 0.066 | The ridge predicts ordering, but a training-fold-selected fixed method reaches the same 0.066 regret. |
| Hänseroth et al. | 61.9% / 0.373 | 61.9% / 0.373 | Lower generator zero-shot force error selects the best arm in four of seven systems. |
| Hänseroth and Dreßler | 63.4% / 0.366 | 62.5% / 0.375 | Wider trajectory coverage helps across most matched decisions, but the preferred stride remains material dependent. |
| Kulichenko et al. | 58.3% / 0.003 | 75.0% / 0.204 | A direct target-coverage rule makes the better allocation decisions on four targets. |
| Dale et al. | 49.7% / 0.479 | 51.8% / 0.549 | Acquisition-policy descriptors do not predict the held-out contexts. |
| Bi and Elena | 48.8% / 0.363 | 76.2% / 0.168 | Semantic coordinates recover cross-dataset ordering, while a fixed selector retains slightly lower regret. |
| Wong and Yang | 80.0% / 0.200 | 100.0% / 0.000 | Starting-potential errors predict the energy winner, but iterative fine-tuning also wins at every budget. |
| Baghishov et al. | 83.3% / 0.000 | 100.0% / 0.000 | Matching energy or force coverage to the evaluation target selects the best method at all nine budgets. |
| Qi et al. | 100.0% / 0.000 | 0.0% / 1.000 | Target-distribution matching selects all six winners; two holdout groups are too few to fit the interaction. |
| Zaverkin et al. | 81.0% / 0.002 | 80.2% / 0.030 | Coverage and model-relative acquisition transfer across three physical contexts at a fixed 512-configuration cap. |
| Espinosa Castañeda et al. | 70.8% / 0.157 | 69.5% / 0.183 | Target match and diversity transfer across five complete datasets, while a fixed policy retains lower regret. |
| Wang et al. | 87.8% / 0.122 | 91.1% / 0.089 | Coverage plus target match transfers across three systems; a fixed entropy preference remains slightly better because most panels favor entropy. |
| Varga-Umbrich et al. | 77.8% / 0.125 | 79.2% / 0.111 | Pretrained representation kernels transfer across three reactive datasets, with paired random comparisons preserving method-specific targets. |
| Kim et al. | 66.7% / 0.250 | 72.2% / 0.250 | Density coverage selects nine of twelve thermodynamic states; the three misses occur where no-variance training narrowly leads at high density. |
| Liu et al. | 56.7% / 0.000 | 83.3% / 0.001 | The independently validated uncertainty threshold nearly matches the best energy and force arms while using about 4% DFT-labeled atomic environments. |
| Zhang et al. | 100.0% / 0.000 | 100.0% / 0.000 | Entropy-targeted coverage wins all four released model–target panels; only two target holdout groups are available. |

Ordering is pairwise accuracy and regret is mean panel-normalized allocation
regret. The results show where measurements carry predictive information and
where method labels or calibration choices do not.
[`source_specific_analysis.json`](source_specific_analysis.json) contains the
complete metrics and fold-selected regularization values.

## Cross-study semantic audit

The pooled audit maps native measurements to five oriented concepts: model-
relative signal, structural coverage, target relevance, measurement
accessibility, and exposure. Each coordinate is normalized within its source
using candidate measurements alone. Source, material, method, and environment
identities are excluded, and every reported prediction holds out one complete
study.

An equal-weight semantic score reaches 67.8% panel-weighted pairwise ordering
with 0.270 normalized regret, compared with 50.0% and 0.447 for an uninformed
tie. Giving each source equal weight yields 73.7% ordering and 0.191 regret. A
ridge fit reaches 66.6% panel-weighted ordering and 0.277 regret. The fixed
direction of the recurring measurements transfers slightly better than one
coefficient vector fitted across heterogeneous tasks. This is the present
retrospective result, not evidence for a universal materials law.

At the study level, the equal-weight score improves pairwise ordering over the
uninformed tie in 15 of 16 held-out sources and reduces allocation regret in 14
of 16. Dale et al. and Li et al. remain the regret reversals, which keeps
uncertainty calibration and source-specific failure modes visible.

[`pooled_semantic_analysis.json`](pooled_semantic_analysis.json) records the
full leave-one-source-out metrics, including every held-out study. Sources
without measured pre-outcome coordinates remain outside the fit.

Retrospective performance can justify a compact hypothesis and expose
confounds. The sealed PhononScore study remains the prospective test.
