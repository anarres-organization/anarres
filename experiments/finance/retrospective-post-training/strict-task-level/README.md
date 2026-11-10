# Strict task-level finance transfer audit

This audit asks whether the shared finance representation transfers when every
candidate is encoded relative to the task on which it is evaluated. It admits a
source-native decision panel only when:

- every arm has an explicit target-alignment measurement
- the starting model and evaluation target are identified
- all arms share the source's native outcome and evaluation contract
- candidate features are defined without reading the panel outcomes.

The filter admits 79 panels, 241 candidate arms, and seven independent studies.
It spans several model families and financial targets. Model identity, source
identity, target identity, method names, and outcome values are absent from the
fixed decision rule.

## Result

The previously fixed practical rule orders 81.6% of candidate pairs and has
0.162 mean normalized regret under leave-one-study-out scoring. Choosing more
data orders 63.1% and has 0.444 regret. With each study receiving equal weight,
the rule reaches 83.6% ordering and 0.098 regret, compared with 57.6% and 0.420
for more data. It has lower regret in six studies, ties in one, and loses in
none.

A grouped ridge is better calibrated but weaker for allocation. Under
leave-one-study-out scoring it reaches 74.1% ordering and 0.228 regret. When a
complete model family is held out, it reaches 85.1% ordering and 0.130 regret.
The fixed rule itself is model agnostic and gives the same predictions under
every holdout partition.

These results identify the most reliable current relationship: explicit
target alignment, curation, verification, retention, and coverage measurements
carry across models and studies when they are defined for the task being
predicted. They do not establish transfer to candidates whose target relation
cannot be measured.

## Selective decisions

The fixed score margin also supports a decide-or-abstain rule. For each held-out
study, we choose the threshold using only the other six studies, maximizing
training-fold coverage subject to a target ordering precision. At the 0.85
training target, the rule decides 235 of 309 held-out candidate pairs. It orders
90.4% correctly at 76.1% coverage, with 89.6% accuracy after weighting each
study equally. Every held-out study retains at least one decision.

Applying the same calibration to data volume decides 100 pairs from one held-out
study, reaches 61.0% accuracy, and abstains on the other six. The complete 0.80,
0.85, and 0.90 sensitivity is recorded without selecting an operating point
from held-out outcomes. This source-held-out retrospective audit gives the
representation an explicit uncertainty action that parallels the abstention
analyses in the legal and robotics studies.

## Reproduce

```bash
python score.py
python -m unittest test_score.py
python score_selective.py
python test_selective.py
```

The script writes [`SCORE.json`](SCORE.json) and
[`MANIFEST.sha256.json`](MANIFEST.sha256.json). The selective audit writes
[`SELECTIVE_SCORE.json`](SELECTIVE_SCORE.json) and
[`SELECTIVE_MANIFEST.sha256.json`](SELECTIVE_MANIFEST.sha256.json).
