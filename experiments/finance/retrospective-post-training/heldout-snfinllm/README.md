# Frozen source-level holdout: SNFinLLM

This audit tests the shared finance representation on an independently reported
study that did not enter feature design or model fitting. The representation is
frozen in [`FREEZE.json`](FREEZE.json), and candidate rankings are serialized in
[`PREDICTIONS.json`](PREDICTIONS.json) before outcome-table extraction.

The study stages financial continued pretraining, supervised instruction tuning,
and direct preference optimization on a Chinese financial language model. Its
model family, language setting, and training pipeline differ from the sources
used to construct the bridge.

The audit proceeds in three steps:

1. recover candidate identities and treatment descriptions without extracting
   evaluation scores
2. encode the candidates under the frozen mapping and serialize predictions
3. extract every comparable reported outcome and score ordering and regret.

No SNFinLLM outcome enters the fitted bridge. [`OUTCOMES.json`](OUTCOMES.json)
records all seven targets reported for at least two frozen same-lineage stages,
and [`SCORE.json`](SCORE.json) reports the source-level holdout result.

## Result

The frozen practical rule and both ridge models predict increasing utility from
the general base through continued financial pretraining, finance SFT, and DPO.
Continued pretraining improves on the original base for both public finance
benchmarks, matching the prediction. The later stages do not follow the
predicted order.
SFT trails the continued-pretraining checkpoint on both shared benchmarks, and
DPO improves one of seven targets over SFT while reducing the other six.

Across the seven comparable target panels, the frozen ranking receives 41.2%
pairwise ordering credit, 14.3% top-choice credit, and 0.783 mean normalized
regret. The more-data baseline has no observed comparable volume coordinate and
therefore abstains with tied scores. Its fractional result is 50.0% pairwise
credit, 42.9% top-choice credit, and 0.504 regret.

This holdout separates two relationships. Target-aligned continued pretraining
transfers across model family and language, while generic stage labels do not
predict whether SFT or preference optimization improves each target. The frozen
mapping also treated DPO as evidence of stronger quality control. The outcome
shows why data quality and objective--target alignment must remain separate:
preference optimization earns no quality credit unless its feedback is aligned
with the target being predicted.

The audit is a retrospective source-level holdout. The paper was already public,
but its outcome tables remained outside representation design, model fitting,
candidate encoding, and serialized predictions. It tests transfer to a new study
without claiming prospective chronology.

## Reproduce

```bash
python freeze_predictions.py
python score_holdout.py
python -m unittest test_freeze.py test_score.py
```
