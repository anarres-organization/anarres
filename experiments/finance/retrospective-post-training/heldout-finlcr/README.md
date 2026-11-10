# FinLCR component-ablation freeze

This record freezes component-level predictions for FinLCR before opening its
PDF, ablation tables, or subset-level results. The ACL Anthology abstract was
visible before the freeze. It identifies staged context lengths and
difficulty-aware sampling and states that the combined curriculum improves
financial numerical reasoning. That disclosed headline is excluded from
scoring.

The test concerns the unseen component evidence. The capability-contract
representation predicts that staged context exposure and difficulty-aware
sampling improve their matched targets, with the clearest effects on long and
hard examples. It separately predicts retention on short or easy examples.
Every matching comparison reported by the paper will be scored. Missing
comparisons will remain unscored rather than being replaced with a looser
contrast.

The source metadata, visible evidence, and exclusions are recorded in
[`SOURCE.json`](SOURCE.json). [`CONTRACT.json`](CONTRACT.json) defines the
chronology and scoring rule, while [`PREDICTIONS.json`](PREDICTIONS.json)
contains the frozen directions.

Source: [Qiu et al., FinNLP 2026](https://aclanthology.org/2026.finnlp-1.3/).
