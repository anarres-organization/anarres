# Retrospective finance post-training audit

This audit asks whether recurring properties of finance training data and reward
design predict which published intervention performs best. It follows the same
research-first pattern as the legal and robotics evidence maps: preserve native
decision sets, normalize outcomes only within a comparable panel, and evaluate
rules under grouped study holdouts.

The analysis is retrospective. Every outcome was public before the feature
schema was assembled. It can identify recurring relationships, useful
measurements, and strong baselines. It cannot validate a prospective finance
selector.

## Evidence panels

[`data/panels.json`](data/panels.json) records 12 decision panels from four
public studies:

- ODA-Fin data-composition and verifier/diversity ablations
- Fino1 chain-of-thought filtering and RL-method ablations
- retention-aware SFT, merging, and hard-example RL on FINESSE-Bench
- QuantEval data-scale and SFT-to-GRPO progressions.

Each row is one reported trained intervention or its starting-policy control.
Targets within a row remain nested outcomes rather than independent training
runs. The source registry records the exact paper version, title, authors, and
table used. [`SCREENING.md`](SCREENING.md) records relevant studies that were
not admitted and the evidence needed to reconsider them.

The literature expansion adds a source-recovered layer before refitting.
[`data/recovered_panels.json`](data/recovered_panels.json) contains 95
additional panels and 391 arms from ten audited primary sources. It covers
cross-task mixtures over five model families, real and synthetic data at fixed
sample counts, finance-specific trajectory selection, five-seed
self-distillation ablations, and a complete two-stage data-processing
factorial across nine model families. It also adds controlled curriculum and
policy-relative difficulty-filtering ablations for long-context financial RL,
finance-data mixture and GRPO interventions, selective knowledge fusion, and a
judge-independent business-outcome audit of financial-advice GRPO.
Source-native treatment fields remain explicit instead of forcing missing
quantities into a common numeric feature.

The semantic conversion is recorded in
[`FEATURE_MAPPING.md`](FEATURE_MAPPING.md). The expanded analysis combines the
recovered layer with the earlier exact-table panels, then evaluates transfer by
held-out source, model, and target. Study labels, model labels, target labels,
and arm names are excluded from the predictive representation.

## Normalization and model

For each panel, the script subtracts the panel's starting-policy score and
divides by the largest absolute observed change in that panel. This preserves
within-panel ordering while preventing a benchmark with a wider numerical range
from dominating the fit. A fixed ridge model uses only source-reported treatment
properties:

- reasoning-data quality control
- retention control
- verifier alignment
- policy-relative difficulty
- out-of-domain augmentation
- raw-volume-only adaptation
- SFT and RL stage indicators
- reported data fraction when available.

Leave-one-study-out evaluation keeps every panel from the held-out paper outside
the fit. A transparent quality-aware rule and a more-training rule are reported
beside the ridge model. These features are an exploratory encoding of published
interventions, not pre-RL measurements such as usable signal density or
effective coverage.

## Initial result

The quality-aware rule selects the reported best intervention in 10 of 12
panels, compared with 6 of 12 for choosing the arm with the most training. Its
mean normalized regret is 0.039, but its uncalibrated scores have poor magnitude
error. The leave-one-study-out ridge model reduces normalized RMSE to 0.573 and
selects 8 of 12 winners, with 0.177 mean normalized regret.

This is a useful but bounded result. Across these studies, reasoning-quality
controls, retention, verifier alignment, and policy-relative difficulty carry
more decision information than training volume alone. The fitted model does not
yet turn those study-level descriptions into a uniformly better selector. The
prospective operations panel must therefore compare against the quality-aware
rule, preserve task-specific regressions, and measure policy-relative signal
directly rather than treating this retrospective encoding as a validated law.

This result is now a baseline for the expanded bridge rather than the main
finance conclusion. The broader evidence asks which measurable properties of
composition, source alignment, supervision, data quality, and training budget
transfer across independently published finance decisions.

## Expanded source-recovered result

The expanded bridge contains 107 source-native decision panels, 438 arms, and
fourteen independent studies. Outcomes are normalized only within each panel.
Under leave-one-source-out evaluation, an interpretable treatment rule orders
62.6% of candidate pairs and has 0.340 mean normalized regret, compared with
55.7% and 0.486 for choosing more data. Its regret is also below the fifth
percentile from 200 within-panel shuffled-pairing controls. The grouped ridge
has lower magnitude error, with 0.464 RMSE, but weaker allocation performance
than the rule, with 0.405 regret.

Equal-study weighting strengthens the comparison. The practical rule reaches
74.9% pair ordering, 70.4% top-choice credit, and 0.175 regret, compared with
58.4%, 36.8%, and 0.411 for more data. It has lower regret in eleven of fourteen
held-out studies, ties in one, and loses in two. The same ordering survives
replacement of min-to-max utility with within-panel ranks. The exact two-sided
sign-test value is 0.022 across the thirteen non-tied studies. This is a
retrospective breadth test, not evidence from a frozen selector. The full
normalization and weighting rationale is recorded in
[`NORMALIZATION_AUDIT.md`](NORMALIZATION_AUDIT.md).

The direction does not depend on the two sources that report only one decision
panel. Restricting the audit to twelve multi-panel studies yields 71.5% pair
ordering and 0.205 regret for the practical rule, compared with 58.9% and 0.413
for more data. This sensitivity prevents a small, easy intervention table from
driving the study-macro result.

Transfer is stronger when a study is known and the held-out group is a new
model or target. The ridge reaches 76.8% study-macro pair ordering and 0.155
regret under model holdout, and 74.3% ordering and 0.176 regret under target
holdout.
This gap is scientifically important. Recurring treatment measurements carry
substantial information within an experimental program, while transfer to a
new paper remains harder. The prospective finance test must therefore use an
independently assembled candidate set and compare against the practical rule,
more-data, and uninformed baselines.

## Reproduce

```bash
python scripts/reproduce.py
python test_reproduce.py
python scripts/build_recovered_panels.py
python scripts/analyze_expanded_bridge.py
python scripts/render_expanded_summary.py
python -m unittest test_expanded_bridge.py
```

The script writes [`results/summary.json`](results/summary.json) and a manifest
of its inputs and outputs. The expanded analysis writes
[`results/expanded_summary.json`](results/expanded_summary.json) and an
independent [`results/EXPANDED_MANIFEST.sha256.json`](results/EXPANDED_MANIFEST.sha256.json)
covering its mapping, sources, inputs, script, and result. Any result used to
design the prospective panel must remain labeled retrospective until it is
frozen and tested on untouched training outcomes.
