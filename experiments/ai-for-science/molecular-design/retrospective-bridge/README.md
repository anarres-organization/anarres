# Retrospective molecular-design bridge

**Status:** seven public evidence objects are normalized and source-audited.
Three decision audits cover early optimization across 23 held-out oracle tasks,
acquisition policies across nine held-out library-architecture contexts, and
target-specific acquisition across 50 held-out molecules. The bridge is
retrospective and leaves the sealed RxnFlow candidate panel unchanged.

This bridge asks how experience, acquisition, representation, and finite
oracle budget change molecular-design outcomes across published studies. It
follows the same research-first pattern used in the legal, robotics, and
materials workstreams: recover exact numerical evidence, preserve each native
outcome, compare only matched decisions, and keep retrospective results
separate from prospective selection.

## Inclusion boundary

A study enters the bridge when its intervention, budget, numerical outcomes,
and source provenance can be recovered without figure digitization. The seven
current objects answer related but distinct questions:

- [**Antoniuk et al. (2026)**](https://doi.org/10.1038/s41524-025-01924-8)
  compare JANUS with and without closed-loop active learning on a final
  500-molecule DFT evaluation. The active-learning arm also uses three prior
  acquisition batches totaling 51,453 DFT attempts. The final comparison is
  therefore an endpoint comparison rather than a total-cost-matched one.
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
- [**van Tilborg and Grisoni (2024)**](https://doi.org/10.1038/s43588-024-00697-2)
  release active-learning trajectories for six acquisition policies, three
  model architectures, and three primary molecular libraries. The bridge uses
  540 repeated runs to test acquisition decisions on held-out libraries.
- [**Schleinitz et al. (2025)**](https://doi.org/10.1021/jacs.4c15902)
  release target-specific acquisition trajectories for 50 complex molecules.
  The bridge reconstructs 14,998 repeated runs across ten acquisition methods
  and evaluates each target by leaving its outcomes out of model selection.

The objects are analyzed separately under their published intervention classes.
Their outcomes remain downstream result records and stay outside Anarres
environment profiles built from measurements made before training.

## Prediction contract

[`prediction_contract_v1.json`](data/prediction_contract_v1.json) applies one
decision format across the seven objects without pooling unlike outcomes. A
panel fixes the source, target context, downstream contract, endpoint, and
budget. Native outcomes are oriented so larger is better and min-max normalized
only within that panel. Predictive evaluations hold out a complete scientific
context and report pairwise ordering, panel-normalized regret, and top-choice
credit. Continuous inputs are standardized inside the training fold, and
measurement, oracle, training, and evaluation costs remain separate.

Three objects support held-out prediction audits. PMO is a charged temporal
decision because its pilot values are early downstream outcomes. The van
Tilborg audit holds out complete molecular libraries and uses measurements from
the initial labeled batch. The regioselectivity audit holds out complete target
molecules and uses target structure plus acquisition outcomes from other
targets. The other four objects retain their intervention evidence but remain
outside the predictor because costs, model contracts, or outcome-blind
coordinates are not comparable.

The pinned RxnFlow `explore` templates define the synthesis action space. They
are source-construction assets rather than predictor coordinates. Candidates
derived from those templates enter the prospective analysis only after the
frozen independent-probe measurements are available.

## Main findings

### Charged temporal decision audit

The PMO trajectories support a real candidate decision with explicit cost. At
the 1,000-call pilot budget, a rule combining each method's training-fold prior
with its task-specific pilot AUC changes the fixed-method decision on 18 of 23
held-out tasks. It reaches 84.3% pairwise ordering and 0.078 mean normalized
regret, compared with 81.8% and 0.099 for the training-fold-selected fixed
method. An uninformed tie reaches 50.0% ordering and 0.479 regret.

Measuring every released replicate through 1,000 oracle calls and completing
every method tied for selection uses 14.2% of exhaustive evaluation cost. The
paired pilot signal beats 1,000 within-panel shuffles on both ordering and
regret, giving the minimum attainable permutation fraction of 0.001. The result
uses early downstream outcomes, so it establishes temporal decision value rather than
prediction from measurements available before optimization. The complete
folds, costs, controls, and later pilot budgets are recorded in
[`pmo_decision_ladder_v1.json`](data/pmo_decision_ladder_v1.json).

### Cross-study mechanism evidence

The active-learning comparison provides the closest external data-acquisition
intervention. On the final 500-molecule evaluation, JANUS with active learning
raises the top multi-property score from 3.56 to 5.24 and the DFT-stable
fraction from 6% to 22% relative to JANUS alone. The preceding acquisition cost
remains part of the intervention and prevents a total-cost-matched claim.

The replay comparison is heterogeneous across objectives. Replay improves AUC
Top-10 on 12 PMO tasks, reduces it on 10, and ties on one. The mean matched
difference is 0.0179, while the median is 0.0036. A useful mechanism at the
aggregate level can therefore remain target dependent.

Saturn and t-SMILES add two compatibility checks. The best augmentation depth
changes across RNN, decoder-transformer, and Mamba architectures, and the
preferred molecular representation depends on both the endpoint and training
duration. These panels support policy- and contract-relative measurement rather
than one fixed ranking of molecular-design experience.

The held-out-library audit makes that compatibility result quantitative. A
method-by-architecture model reaches 83.7% pairwise ordering and 0.138 mean
normalized regret across nine held-out library-architecture contexts, compared
with 63.0% and 0.224 for a training-fold-selected fixed method. Adding the
released initial-batch graph summaries lowers ordering to 80.0% and does not
reduce regret. Architecture compatibility transfers in this panel, while these
graph summaries do not yet provide additional decision value. A paired
bootstrap over the three complete held-out libraries places the primary rule's
mean regret between 0.067 and 0.278. Its regret difference from the fixed rule
still crosses zero, reflecting the limited number of independent libraries.

The regioselectivity panel provides a complementary graph-structured decision.
A nearest-target rule uses only each target's Morgan fingerprint and outcomes
from the most similar training target. It selects a best acquisition method on
62% of 50 held-out targets and reaches 0.213 mean normalized regret, compared
with 42% and 0.297 for the training-fold-selected fixed method. Its 58.8%
pairwise ordering remains below the fixed method's 60.2%, so molecular analogy
improves the top decision without improving the complete ranking.
A nested similarity-weighted sensitivity reaches 60.2% ordering and 0.259
regret. It improves both metrics over the fixed-method baseline, but remains
weaker than the nearest-target rule on top-choice credit and regret. Structural
transfer is therefore present but sensitive to the prediction rule.
Across 20,000 complete-target bootstrap resamples, the nearest-target rule has
a 90.7% frequency of lower regret than the fixed rule, but the 95% interval for
the regret difference is $[-0.209, 0.039]$. The improvement in best-choice credit
is more stable, with a 95% difference interval of $[0.06, 0.34]$. These
intervals keep target-level uncertainty visible rather than treating the 45
pairwise comparisons within each molecule as independent observations.

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

python scripts/build_pmo_decision_ladder.py \
  --pmo /tmp/pmo.json \
  --output /tmp/pmo-decision-ladder.json

python scripts/normalize_vantilborg_active_learning.py \
  --source-csv /path/to/traversing_chem_space/figures/data/fig3.csv \
  --output /tmp/vantilborg.json

uv run --with rdkit==2026.9.2 python \
  scripts/normalize_reisman_regioselectivity.py \
  --archive /path/to/clean_run.zip \
  --output /tmp/reisman.json

python scripts/build_prediction_contract.py \
  --data data \
  --output /tmp/prediction-contract.json

python scripts/audit_decision_uncertainty.py \
  --data data \
  --output /tmp/decision-uncertainty.json
```

The PMO and regioselectivity archives remain external artifacts. The repository
includes compact normalized records for all seven objects and a combined
summary.
