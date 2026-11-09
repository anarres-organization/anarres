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
| Panel weighted | 62.6% | 0.340 | 52.4% |
| Study macro | 74.9% | 0.175 | 70.4% |

The more-data baseline reaches 55.7% ordering and 0.486 regret under panel
weighting, and 58.4% ordering and 0.411 regret under study-macro weighting. The
practical rule has lower regret in eleven of fourteen held-out studies, ties in
one, and loses in two. A two-sided exact sign test over the thirteen non-tied
studies gives $p=0.022$. This records breadth across published studies while
remaining a retrospective test of a semantically encoded rule.

Two sources contribute one decision panel each. Excluding both leaves twelve
multi-panel studies, where the practical rule reaches 71.5% ordering and 0.205
regret versus 58.9% and 0.413 for more data. The corresponding study-level
comparison has nine wins, two losses, and one tie.

The conclusion also survives rank normalization. With outcomes replaced by
within-panel ranks, the practical rule reaches 74.9% study-macro ordering and
0.174 regret, compared with 58.4% and 0.422 for more data. Pair ordering is
unchanged because monotone within-panel normalization preserves every candidate
comparison.

## Interpretation

The original 12-panel audit selected ten reported winners with its quality-aware
rule. That result remains the initial evidence cut. The 107-panel analysis is
more demanding because it adds ten independently recovered sources, new model
families and targets, policy-relative curriculum ablations, data-mixture and
reward interventions, and a source-level holdout. Its result is expressed
through ordering and regret rather than a single winner count.

These retrospective checks establish useful baselines and expose where transfer
weakens. They do not validate a finance allocator. Following the decision-first
evaluation used by DataDecide, the prospective panel must compare curve or score
prediction with the actual allocation decision and strong simple rules
([Magnusson et al., 2025](https://arxiv.org/abs/2504.11393)).
