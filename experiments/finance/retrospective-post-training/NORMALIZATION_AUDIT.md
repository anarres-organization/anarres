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
| Panel weighted | 64.3% | 0.304 | 59.8% |
| Study macro | 75.3% | 0.170 | 72.5% |

The more-data baseline reaches 56.0% ordering and 0.489 regret under panel
weighting, and 58.2% ordering and 0.421 regret under study-macro weighting. The
practical rule has lower regret in thirteen of sixteen held-out studies, ties in
one, and loses in two. A two-sided exact sign test over the fifteen non-tied
studies gives $p=0.007$. This records breadth across published studies while
remaining a retrospective test of a semantically encoded rule.

Two sources contribute one decision panel each. Excluding both leaves fourteen
multi-panel studies, where the practical rule reaches 72.5% ordering and 0.194
regret versus 58.7% and 0.424 for more data. Removing any one source from the
complete bridge preserves the rule's lower study-macro regret, with an advantage
between 0.233 and 0.272.

The conclusion also survives rank normalization. With outcomes replaced by
within-panel ranks, the practical rule reaches 75.3% study-macro ordering and
0.168 regret, compared with 58.2% and 0.428 for more data. Pair ordering is
unchanged because monotone within-panel normalization preserves every candidate
comparison.

Model roles remain separate. The exploratory seven-coordinate ridge has the
lowest study-macro source-holdout RMSE at 0.403. The full-feature ridge improves
candidate ordering to 72.9% and lowers regret to 0.212. The fixed practical
rule has the strongest decision metrics but is not calibrated as a utility
scale. These models answer different questions and are reported together.

## Interpretation

The original 12-panel audit selected ten reported winners with its quality-aware
rule. That result remains the initial evidence cut. The 149-panel analysis is
more demanding because it adds twelve independently recovered sources, new model
families and targets, policy-relative curriculum ablations, data-mixture and
reward interventions, and a source-level holdout. Its result is expressed
through ordering and regret rather than a single winner count.

These retrospective checks establish useful baselines and expose where transfer
weakens. They do not validate a finance allocator. Following the decision-first
evaluation used by DataDecide, the prospective panel must compare curve or score
prediction with the actual allocation decision and strong simple rules
([Magnusson et al., 2025](https://arxiv.org/abs/2504.11393)).

## Time and influence sensitivities

A publication-date split fits the ridge models on seven studies from 2024--2025
and scores nine sources released in 2026. On the later sources, the full ridge
reaches 72.8% study-macro ordering and 0.248 regret, while more data reaches
57.3% and 0.434. The practical rule reaches 72.2% ordering and 0.200 regret.
This split is a chronological sensitivity rather than a prospective test because
the shared semantic representation was designed after all outcomes were public.
