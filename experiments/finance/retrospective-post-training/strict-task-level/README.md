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

## Reproduce

```bash
python score.py
python -m unittest test_score.py
```

The script writes [`SCORE.json`](SCORE.json) and
[`MANIFEST.sha256.json`](MANIFEST.sha256.json).
