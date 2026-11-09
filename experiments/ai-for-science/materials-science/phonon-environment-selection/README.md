# Prospective selection of phonon post-training data

**Status:** first prospective loop complete. All 24 candidate runs and both
reference checkpoints passed the label-blind prediction gate before the two
external manifests were opened. The frozen signal + coverage prediction missed
the best candidate at all three budgets; [`RESULTS.md`](RESULTS.md) reports the
complete result and the post-outcome composition audit.

The follow-up [`pbesol-transfer/`](pbesol-transfer/) study freezes the complete
PBE-derived ordering before opening a 1,000-structure PBEsol panel. The ordering
selects the best candidate at two of three budgets, while none of the
post-trained candidates improves on the starting checkpoint's absolute Top-100
stable rate. This separates partial decision transfer from absolute improvement
under a new functional and workflow.

## Research question

This study asks whether measurements made under a pretrained phonon model can
choose a fixed-budget DFT post-training set before any candidate model is
trained. The decision is practical: given a labeled high-fidelity reservoir and
a limited post-training budget, should training prioritize model-relative
signal, coverage of materials space, or both?

The first loop uses the public PhononScore release. It starts from the released
MatterSim-pretrained checkpoint and draws candidates only from the 7,809
DFT-PBE structures assigned to gradient training. The 411 released internal
validation structures retain their original checkpoint-selection role. The
formula-disjoint DFT-PBE and MP20 external panels remain sealed until the
candidate memberships, point prediction, training contract, and evaluation
contract are frozen.

This supervised study of dynamical-stability scoring provides the first
low-cost materials test in Anarres. The planned interatomic-potential study
will then test the framework with physical phonon and relaxation outcomes.
Because the signal measurement uses labels from the construction reservoir,
this experiment studies training-data allocation rather than prospective DFT
label acquisition. A future acquisition study requires a separately validated
label-free uncertainty measure.

## Research-first progression

The study advances through five gates.

1. **Qualify the public source.** Pin the source revision and archive, verify
   record identities and roles, audit formula overlap, and document licenses
   and redistribution limits.
2. **Measure the starting model.** Run the released pretrained checkpoint over
   the gradient-training pool. Record per-structure loss components, inference
   cost, atom count, and a frozen structure representation. Repeat the
   measurement where stochasticity is present.
3. **Freeze a candidate bank.** Construct nested equal-budget rankings for a
   deterministic random baseline, model-relative signal, representation
   coverage, and their hybrid. Serialize memberships, hashes, overlap, atom
   counts, the point prediction, and an abstention rule before training.
4. **Run matched post-training.** Train each candidate with two fresh seeds at
   256, 512, and 1,024 structures. Use the same starting checkpoint, internal
   validation set, optimizer, update schedule, and checkpoint rule. Report
   processed structures, atoms, graph edges, wall time, and accelerator time.
5. **Open and score the external panels.** Evaluate every expected run before
   comparing candidates. Report curve error, pair ordering, best-candidate
   decisions, regret, seed variation, and the complete cost of measurement,
   training, and evaluation.

No later stage can repair an earlier contract after external outcomes are
opened. A failed reliability, identity, or completeness gate produces an
abstention or a new versioned experiment rather than an edited candidate set.

## Frozen candidate decision

The candidate families follow recurring choices in materials active learning:
random sampling, informativeness, diversity, and their combination. Their exact
operational definitions are fixed in the candidate freeze artifact.

| Candidate | Pre-training information | Intended comparison |
| --- | --- | --- |
| Hash-uniform | Record identity only | Outcome-blind random baseline |
| Signal | Starting-model loss and stability-boundary error | Whether larger available update signal improves post-training |
| Coverage | Frozen structure representations and composition | Whether broad support improves formula-disjoint transfer |
| Signal + coverage | Both measurements under fixed weights | Whether informativeness and support are jointly useful |

Each rule must produce one deterministic ranking whose 256- and 512-structure
sets are prefixes of its 1,024-structure set. The freeze will constrain
processed-atom cost as well as structure count or report any residual mismatch
before training. Full-data post-training and the unmodified starting checkpoint
are scientific references, not size-matched candidate arms.

The frozen point prediction is that the joint rule will provide the best
external DFT utility per processed atom at all three budgets. The complete
predicted ordering is signal + coverage, signal, coverage, then hash-uniform.
This prediction is preserved here as the pre-outcome decision. It was incorrect
at all three budgets and is scored without revision in [`RESULTS.md`](RESULTS.md).

## Outcomes and decision quality

The primary external panel is the released balanced DFT-PBE set of 1,000
formula-disjoint structures. The primary metrics are:

- Top-100 dynamically stable rate at the released $-0.1$ THz threshold
- ranking quality and calibration across the full DFT panel
- minimum-frequency regression error as a supporting diagnostic
- post-training utility relative to the common pretrained checkpoint.

The 6,400-structure MP20 panel is a secondary cross-source test. Results will be
reported by generator source before any pooled average. Candidate utility is
evaluated both as a learning curve and as a finite-budget decision. Practical
value requires decision quality in addition to curve fit.

## Qualification completed so far

The pinned archive contains 8,221 DFT post-training records: 7,809 gradient
training, 411 checkpoint validation, and one unused rounding record. The
gradient-training pool contains 6,886 reduced formulas and 81 elements. At the
released stability threshold, 1,146 training structures are unstable and 6,663
are stable.

The archive SHA-256 matches the checksum published at the pinned source
revision. Its extracted DFT manifest is internally consistent with the label
file and CIF inventory. The byte-level manifest digest differs from the digest
recorded in the upstream split audit, so Anarres records both values and relies
on the verified whole-archive digest plus its own content audit. This difference
remains an open provenance discrepancy, while the record-level content audit
passes.

The pretrained checkpoint was measured over all 7,809 eligible structures in
373.6 seconds on CPU. An independent 128-structure repeat under the upstream
DGL 2.1 contract produced a maximum absolute signal difference of
$2.98\times10^{-7}$ and minimum embedding cosine similarity above
0.99999999999998. The frozen candidates remain within 1.81% of the
hash-uniform arm's processed-atom count at every budget. Their pairwise overlap
also passes the prespecified gate. [`FREEZE.json`](FREEZE.json) records the
exact memberships, prediction, hashes, and audits; [`MEASUREMENT_METADATA.json`](MEASUREMENT_METADATA.json)
records the complete-sweep identity and timing.
[`LAUNCH_MANIFEST.json`](LAUNCH_MANIFEST.json) binds the 12 candidate-budget
splits to the 24 planned seed runs without exposing source labels or structures.
All 24 runs now have sealed completion records. The resulting training manifest
has canonical digest
`ab700aafcdf595363e5ad05b818d36f9baad069b1d2fb64459050bd01cf75eb1`.
[`EVALUATION_CONTRACT.json`](EVALUATION_CONTRACT.json) fixes the label-blind
prediction gate, checkpoint-specific normalization, panel metrics, decision
rules, and cost accounting before either external manifest is opened.
[`RESULTS_SUMMARY.json`](RESULTS_SUMMARY.json) contains the compact scored
surface, generator-stratified secondary results, reference metrics, and the
retrospective candidate-composition audit.

The PhononScore code is MIT licensed and bundles ALIGNN under its original
license. The archive is publicly released for reproduction, but its landing
page does not state a standalone dataset license. Materials Project identifies
its core data as CC BY 4.0. Anarres therefore does not redistribute source CIFs
or labels and will publish only source pointers, record identities where
permitted, derived measurements, contracts, and result summaries.

## Evidence motivating the design

Materials-data research consistently separates informativeness, diversity, and
representativeness when selecting expensive reference calculations. Reviews of
atomistic data generation also emphasize that random sampling can miss rare
physical regimes, while uncertainty-only selection can narrow support. The
comparison above tests those choices under a common pretrained model and a
formula-disjoint target rather than assuming that one heuristic is universally
best.

Primary sources:

- [PhononScore paper](https://arxiv.org/abs/2607.08518) and
  [released code](https://github.com/xqh19970407/PhononScore)
- [PhononScore data record](https://doi.org/10.5281/zenodo.21157982)
- [Data Generation for Machine Learning Interatomic Potentials and
  Beyond](https://doi.org/10.1021/acs.chemrev.4c00572)
- [From electrons to phase diagrams with machine learning
  potentials](https://doi.org/10.1038/s41524-024-01441-0)

## Reproduction

[`SOURCES.json`](SOURCES.json) records the pinned inputs and current
qualification state. [`PROTOCOL.json`](PROTOCOL.json) fixes the measurement,
candidate families, training seeds, evaluation, and cost accounting before
starting-model scoring. After obtaining the public archive, reproduce the local
source audit with:

```bash
python scripts/audit_source.py \
  --data-root /path/to/phononscore_data_20261104 \
  --out /tmp/phonon_source_audit.json
```

The committed [`SOURCE_AUDIT.json`](SOURCE_AUDIT.json) contains only aggregate
metadata and hashes. It does not contain external labels or source structures.
Validate the measurement protocol with:

```bash
python scripts/validate_protocol.py
```

After installing the pinned upstream environment, measure a smoke subset or the
complete eligible pool with:

```bash
python scripts/measure_starting_model.py \
  --upstream-repo /path/to/PhononScore \
  --data-root /path/to/phononscore_data_20261104 \
  --out /path/to/starting_model_measurements.jsonl \
  --device cpu
```

The runner verifies the frozen checkpoint and manifest digests before inference.
It writes one derived record per eligible training structure and never reads an
external evaluation directory.

After the full sweep and its 128-record repeat pass satisfy the measurement
gate, freeze the nested candidates with:

```bash
python scripts/freeze_candidates.py \
  --measurement /path/to/starting_model_measurements.jsonl \
  --repeat-measurement /path/to/repeat_measurements.jsonl \
  --out /path/to/FREEZE.json
```

The freezer exits without an artifact when repeatability, nesting, atom-count
matching, or overlap requirements fail.

[`RUNBOOK.md`](RUNBOOK.md) gives the complete source-to-score execution order,
including the boundary between label-blind prediction and outcome scoring.
