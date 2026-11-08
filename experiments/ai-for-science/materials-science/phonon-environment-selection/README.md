# Prospective selection of phonon post-training data

**Status:** source and measurement protocol qualified; starting-model
measurement and candidate freeze remain open. External test labels have not
been extracted or inspected for this study.

## Research question

This study asks whether measurements made under a pretrained phonon model can
choose a fixed-budget DFT post-training set before any candidate model is
trained. The decision is practical: given a limited number of high-fidelity
phonon calculations, should post-training prioritize model-relative signal,
coverage of materials space, or both?

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

## Planned candidate decision

The candidate families follow recurring choices in materials active learning:
random sampling, informativeness, diversity, and their combination. Their exact
operational definitions remain provisional until the released checkpoint and
representations reproduce successfully.

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

The provisional point prediction is that the joint rule will provide the best
external DFT utility per processed atom. This prediction becomes claim-bearing
only when the measurement reliability gate, candidate memberships, and all
training details are serialized in a freeze artifact.

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
must be explained or accepted explicitly in the candidate freeze.

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
  --device cuda
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
