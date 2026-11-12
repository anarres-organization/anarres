# Retrospective molecular-design bridge

**Status:** five public evidence objects are normalized and source-audited. The
bridge is retrospective and does not alter the sealed RxnFlow candidate panel.

This bridge asks how experience, acquisition, representation, and finite
oracle budget change molecular-design outcomes across published studies. It
follows the same research-first pattern used in the legal, robotics, and
materials workstreams: recover exact numerical evidence, preserve each native
outcome, compare only matched decisions, and keep retrospective results
separate from prospective selection.

## Inclusion boundary

A study enters the bridge when its intervention, budget, numerical outcomes,
and source provenance can be recovered without figure digitization. The five
current objects answer related but distinct questions:

- [**Antoniuk et al. (2026)**](https://doi.org/10.1038/s41524-025-01924-8)
  compare JANUS with and without closed-loop active learning at a common
  500-molecule DFT budget. The released acquisition data contain 61,659
  molecules from the initial dataset and three acquired batches.
- [**InVirtuoGen**](https://github.com/invirtuolabs/InVirtuoGen_results)
  compares experience replay with no replay across all 23 PMO objectives. The
  matched seed-0 panel contains 23 direct comparisons, while the replay arm
  provides three runs per objective.
- [**Saturn**](https://doi.org/10.1038/s42256-026-01200-4) reports 18
  architecture-by-augmentation conditions over ten runs and ten raw replicates
  for four methods across five protein targets.
- [**t-SMILES**](https://doi.org/10.1038/s41467-024-49388-6) reports 21 JNK3
  conditions that vary molecular representation, augmentation, transfer
  learning, and training duration.
- [**PMO**](https://github.com/wenhao-gao/mol_opt) releases 2,875 raw
  optimization traces spanning 25 methods and 23 objectives. The bridge
  reconstructs AUC Top-10 at five oracle budgets.

The objects are analyzed separately under their published intervention classes.
Their outcomes remain downstream result records and stay outside Anarres
environment profiles built from measurements made before training.

## Main findings

The active-learning comparison provides the closest external data-acquisition
intervention. At the same final DFT budget, JANUS with active learning raises
the top multi-property score from 3.56 to 5.24 and the DFT-stable fraction from
6% to 22% relative to JANUS alone.

The replay comparison is heterogeneous across objectives. Replay improves AUC
Top-10 on 12 PMO tasks, reduces it on 10, and ties on one. The mean matched
difference is 0.0179, while the median is 0.0036. A useful mechanism at the
aggregate level can therefore remain target dependent.

The PMO trajectories show how much early budget is needed to recover final
method orderings. Evaluating every method to 10% of its final budget identifies
8 of 23 final winners with 75.4% pairwise ordering accuracy. At 50%, those
values rise to 14 of 23 and 91.2%. This descriptive trajectory audit leaves the
cost of probing every method uncharged. An allocation-policy test would include
that cost in the decision budget.

Saturn and t-SMILES add two compatibility checks. The best augmentation depth
changes across RNN, decoder-transformer, and Mamba architectures, and the
preferred molecular representation depends on both the endpoint and training
duration. These panels support policy- and contract-relative measurement rather
than one fixed ranking of molecular-design experience.

## Relationship to the prospective study

The [RxnFlow reaction-environment study](../reaction-environment-selection/README.md)
remains the claim-bearing environment-selection experiment. It fixes one
starting molecular graph policy, target, trainer, replay contract, and matched
budget while changing only candidate-bank membership. This bridge broadens the
evidence across targets, mechanisms, and model families. The comparison between
the operational and graph-aware candidate banks remains the prospective test.

## Reproduction

[`SOURCES.json`](SOURCES.json) pins every external artifact by URI, revision or
SHA-256 digest, media type, size, and license. The normalizers accept local
copies of those artifacts and never download data implicitly. The checked-in
release files are covered by [`MANIFEST.sha256`](MANIFEST.sha256).

```bash
python scripts/normalize_antoniuk_active_learning.py \
  --table-html /path/to/antoniuk-table-2.html \
  --source-csv /path/to/41524_2025_1924_MOESM2_ESM.csv \
  --output /tmp/antoniuk.json

python scripts/normalize_invirtuo_replay.py \
  --repository /path/to/InVirtuoGen_results \
  --output /tmp/invirtuo.json

python scripts/normalize_saturn_source_data.py \
  --source-dir /path/to/saturn-source-data \
  --output /tmp/saturn.json

python scripts/normalize_tsmiles_table.py \
  --table-html /path/to/tsmiles-table-2.html \
  --output /tmp/tsmiles.json

python scripts/normalize_pmo.py \
  --results-dir /path/to/pmo-results \
  --archive /path/to/results.tar.gz \
  --output /tmp/pmo.json \
  --workers 8
```

The PMO archive expands to about 1.7 GB and remains an external artifact. The
repository includes compact normalized records for the four smaller sources
and a combined summary for all five objects.
