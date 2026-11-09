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
[`data/recovered_panels.json`](data/recovered_panels.json) contains 137
additional panels and 491 arms from twelve audited primary sources. It covers
cross-task mixtures over five model families, real and synthetic data at fixed
sample counts, finance-specific trajectory selection, five-seed
self-distillation ablations, and a complete two-stage data-processing
factorial across nine model families. It also adds controlled curriculum and
policy-relative difficulty-filtering ablations for long-context financial RL,
finance-data mixture and GRPO interventions, selective knowledge fusion, and a
judge-independent business-outcome audit of financial-advice GRPO. A
same-checkpoint preference-alignment ablation from FINDAP adds finance and
general-capability outcomes, including the reported regressions. FinLMM-R1
adds reward-component ablations and a financial multimodal data-scaling curve.
Source-native treatment fields remain explicit instead of forcing missing
quantities into a common numeric feature.

The semantic conversion is recorded in
[`FEATURE_MAPPING.md`](FEATURE_MAPPING.md). The expanded analysis combines the
recovered layer with the earlier exact-table panels, then evaluates transfer by
held-out source, model, and target. Study labels, model labels, target labels,
and arm names are excluded from the predictive representation.

## Normalization and model

For each panel, the script maps the worst reported arm to zero and the best to
one, preserving intermediate differences. This prevents a benchmark with a
wider numerical range from dominating the fit. The bridge then evaluates fixed
rules and ridge models using only source-reported treatment properties such as:

- target fit and source breadth
- data volume and human-labeled share
- quality, retention, and refinement controls
- verifier alignment and policy-relative selection
- feedback locality, rollout efficiency, and curriculum progression.

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

The expanded bridge contains 149 source-native decision panels, 538 arms, and
sixteen independent studies. Outcomes are normalized only within each panel.
Under leave-one-source-out evaluation, an interpretable treatment rule orders
64.3% of candidate pairs and has 0.304 mean normalized regret, compared with
56.0% and 0.489 for choosing more data. Its regret is also below the fifth
percentile from 200 within-panel shuffled-pairing controls. The grouped ridge
has lower magnitude error but weaker allocation performance than the rule. The
exploratory seven-coordinate ridge gives the best study-macro calibration at
0.403 RMSE. The full ridge reaches 72.9% study-macro pair ordering and 0.212
regret, while the practical rule remains strongest for decisions.

Equal-study weighting strengthens the comparison. The practical rule reaches
75.3% pair ordering, 72.5% top-choice credit, and 0.170 regret, compared with
58.2%, 37.6%, and 0.421 for more data. It has lower regret in thirteen of sixteen
held-out studies, ties in one, and loses in two. The same ordering survives
replacement of min-to-max utility with within-panel ranks. The exact two-sided
sign-test value is 0.007 across the fifteen non-tied studies. This is a
retrospective breadth test, not evidence from a frozen selector. The full
normalization and weighting rationale is recorded in
[`NORMALIZATION_AUDIT.md`](NORMALIZATION_AUDIT.md).

The direction does not depend on the two sources that report only one decision
panel. Restricting the audit to fourteen multi-panel studies yields 72.5% pair
ordering and 0.194 regret for the practical rule, compared with 58.7% and 0.424
for more data. Removing any single source also preserves the practical rule's
regret advantage, with a study-macro gap of 0.233 to 0.272. These sensitivities
prevent a small or unusually favorable table from driving the result.

A publication-date sensitivity fits the learned models on seven studies released
in 2024--2025 and scores nine sources released in 2026. The full ridge reaches
72.8% study-macro pair ordering and 0.248 regret, compared with 57.3% and 0.434
for more data. The fixed practical rule reaches 72.2% ordering and 0.200 regret.
Publication order reduces direct outcome reuse but does not make this a
prospective test because the shared semantic schema was assembled after these
results were public.

Transfer is stronger when a study is known and the held-out group is a new
model or target. The full ridge reaches 76.9% study-macro pair ordering and
0.152 regret under model holdout, and 74.1% ordering and 0.162 regret under
target holdout. The compact ridge remains better calibrated under source
holdout but gives up some ordering and decision accuracy.
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
