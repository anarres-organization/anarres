# Normalization and study-weighting audit

Finance post-training papers report accuracy, exact match, rubric scores, and
other source-specific outcomes on different numerical scales. Pooling those raw
points would make a large-range benchmark dominate a smaller-range benchmark.
The bridge therefore defines utility from zero to one within each source-native
decision panel. The best reported arm receives one, the worst receives zero,
and intermediate arms retain their relative position.

The panel boundary follows the decision available before training. Model,
target, and budget variants remain grouped under their source. No statistic is
normalized across unrelated papers.

## Weighting levels

The main machine-readable result reports two aggregations:

1. panel-weighted metrics give every reported decision panel equal weight
2. study-macro metrics first aggregate within a source and then give each study
   equal weight.

Study-macro metrics are the stricter summary of independent evidence because
papers contribute different numbers of tables, models, and targets. This follows
the broader recommendation to compare methods across datasets using the dataset
as the repeated unit rather than treating every nested score as independent
([Demšar, 2006](https://www.jmlr.org/papers/v7/demsar06a.html)). Performance
profiles provide a related precedent for relative, problem-level benchmarking
across heterogeneous tasks ([Dolan and Moré,
2002](https://arxiv.org/abs/cs/0102001)).

## Results

Under leave-one-source-out evaluation, the fixed practical rule has the
following performance:

| Aggregation | Pair ordering | Mean normalized regret | Top-choice credit |
|---|---:|---:|---:|
| Panel weighted | 60.0% | 0.390 | 46.7% |
| Study macro | 70.5% | 0.216 | 65.1% |

The more-data baseline reaches 53.3% ordering and 0.507 regret under panel
weighting, and 58.8% ordering and 0.418 regret under study-macro weighting. The
practical rule has lower regret in eight of ten held-out studies. A two-sided
exact sign test gives $p=0.109$, which records a consistent direction without
claiming conventional statistical significance from ten sources.

The conclusion also survives rank normalization. With outcomes replaced by
within-panel ranks, the practical rule reaches 70.5% study-macro ordering and
0.206 regret, compared with 58.8% and 0.428 for more data. Pair ordering is
unchanged because monotone within-panel normalization preserves every candidate
comparison.

## Interpretation

The original 12-panel audit selected ten reported winners with its quality-aware
rule. That result remains the initial evidence cut. The 90-panel analysis is
more demanding because it adds six independently recovered sources, new model
families and targets, policy-relative curriculum ablations, and a source-level
holdout. Its result is expressed through ordering and regret rather than a
single winner count.

These retrospective checks establish useful baselines and expose where transfer
weakens. They do not validate a finance allocator. Following the decision-first
evaluation used by DataDecide, the prospective panel must compare curve or score
prediction with the actual allocation decision and strong simple rules
([Magnusson et al., 2025](https://arxiv.org/abs/2504.11393)).
