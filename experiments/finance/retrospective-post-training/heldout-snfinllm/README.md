# Frozen source-level holdout: SNFinLLM

This audit tests the shared finance representation on an independently reported
study that did not enter feature design or model fitting. The representation is
frozen in [`FREEZE.json`](FREEZE.json) before outcome-table extraction.

The study stages financial continued pretraining, supervised instruction tuning,
and direct preference optimization on a Chinese financial language model. Its
model family, language setting, and training pipeline differ from the sources
used to construct the bridge.

The audit proceeds in three steps:

1. recover candidate identities and treatment descriptions without extracting
   evaluation scores
2. encode the candidates under the frozen mapping and serialize predictions
3. extract every comparable reported outcome and score ordering and regret.

No SNFinLLM outcome will be added to the fitted bridge before the holdout is
scored. The final record will preserve task-specific regressions and distinguish
target-domain outcomes from general-capability checks.
