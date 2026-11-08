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
table used.

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

## Reproduce

```bash
python scripts/reproduce.py
python test_reproduce.py
```

The script writes [`results/summary.json`](results/summary.json) and a manifest
of its inputs and outputs. Any result used to design the prospective panel must
remain labeled retrospective until it is frozen and tested on untouched
training outcomes.
