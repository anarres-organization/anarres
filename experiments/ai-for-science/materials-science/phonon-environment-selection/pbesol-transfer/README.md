# Prospective transfer to an independent PBEsol phonon panel

**Status:** complete. The source, 1,000-record panel, evaluation contract, and
all 24 candidate plus two reference prediction files were sealed before
outcome access. [`RESULTS.md`](RESULTS.md) reports the prospective result, and
[`SCORE.json`](SCORE.json) preserves the complete scored artifact.

## Question

The first prospective study compared four DFT post-training rules on a
formula-disjoint PBE panel. Its predicted signal + coverage ordering failed,
while coverage led at 256 and 512 structures and hash-uniform led at 1,024.
This follow-up asks a narrower question:

> Does that observed candidate ordering transfer to an independently computed,
> composition-disjoint PBEsol phonon panel?

The experiment reuses the 24 completed candidate checkpoints and the two
released reference checkpoints. It does not retrain, refit, or alter candidate
membership. The new decision is whether the earlier PBE ordering predicts
relative utility under a different DFT functional and phonon workflow.

## Public source

The panel comes from the Materials Project Phonon Database v1.1, a CC BY 4.0
release containing 26,413 PBEsol harmonic-phonon calculations. We use one
checksum-verified shard, `mp_0860001-0880000.tar`, which contains 1,530
materials. The source paper defines the minimum frequency along the band path,
a -0.1 THz positivity threshold, and the resulting phonon-stability label.

- [Dataset and files](https://doi.org/10.5281/zenodo.20196565)
- [Source paper](https://doi.org/10.26434/chemrxiv.15004632/v1)
- [Materials Project phonon workflow documentation](https://materialsproject.github.io/atomate2/user/codes/vasp.html)

## Sealed construction

Before any phonon summary or band file is read, the freezer may access only
archive paths and each material's relaxed
`06_harmonic_phonons/POSCAR.gz`. It excludes any MP identity or reduced
composition used by the PhononScore DFT post-training reservoir or its earlier
DFT-PBE test panel. One record per remaining reduced composition is selected by
a fixed SHA-256 rule, followed by the first 1,000 records under the same rule.

The starting checkpoint was trained before this PBEsol release, but its
surrogate pretraining corpus contains some of the same MP identities. We report
that overlap rather than hiding it. The confirmatory exclusion applies to the
claim-bearing DFT post-training reservoir and the previously opened DFT test
panel, while the new PBEsol outcomes remain untouched.

The qualified shard leaves 1,427 records after the joint identity and
composition exclusion, spanning 1,414 unique reduced compositions. The fixed
hash rule selects 1,000 unique compositions. Of those, 946 MP identities and
948 compositions occur in the starting checkpoint's MatterSim-labeled
pretraining corpus. This panel therefore tests transfer to new PBEsol outcomes
and a new DFT workflow, not transfer to structures wholly unseen by the starting
model.

## Frozen prediction

The point prediction copies the complete two-seed ordering observed on the
earlier PBE panel:

| DFT post-training budget | Predicted PBEsol ordering |
| ---: | --- |
| 256 | coverage > signal > signal + coverage > hash-uniform |
| 512 | coverage > hash-uniform > signal > signal + coverage |
| 1,024 | hash-uniform > coverage > signal + coverage > signal |

This is a transfer prediction, not a model selected on PBEsol outcomes. The
primary score is whether the best candidate and complete ordering transfer at
each budget. Full-curve metrics, utility relative to the starting checkpoint,
and the full-data DFT reference remain supporting analyses.

## Reproduction boundary

Run [`freeze_panel.py`](freeze_panel.py) with the checksum-verified PBEsol
shard and the pinned PhononScore archive. The script refuses to overwrite an
existing freeze, reads only relaxed structures from the PBEsol shard, and
records `external_labels_read: false`. The reproduced panel has canonical
SHA-256 `720b45ee83254609d9a9c2433d28530d511527db5339ed975c530024e0c7df00`.
[`prepare_inputs.py`](prepare_inputs.py) materializes only the frozen relaxed
structures. The shared label-blind prediction runner was used after the panel
freeze was bound to [`EVALUATION_CONTRACT.json`](EVALUATION_CONTRACT.json).

The label-blind graph cache has canonical SHA-256
`0fe96c2db803025c31ab7d174812facbf8561bb0b245972aa03df96bf9d8de35`.
Every expected prediction completed with finite outputs before label access;
the prediction-manifest digest is
`c523c85c96fa22876d181e21ffc5fd577d7c880fd62504bd31776780abb744d7`.
Only then did [`score_pbesol.py`](score_pbesol.py) open the 1,000 frozen
`summary.json.gz` members. Two independent scoring executions produced the
same byte-level result. The canonical score digest is
`f012887c7f8b1652f6d0579e9cd3c198f71c8c676a6c66f0ee33060b706fe3ff`.
