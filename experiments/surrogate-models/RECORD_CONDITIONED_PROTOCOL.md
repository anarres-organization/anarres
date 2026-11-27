# Record-conditioned surrogate replay

This comparison implements the record-conditioned baseline proposed in
[issues #92](https://github.com/anarres-organization/anarres/issues/92) and
[#94](https://github.com/anarres-organization/anarres/issues/94). The structured
and record-conditioned methods answer different questions and are scored
independently on the same complete-study holdouts.

The frozen contract is
[`RECORD_CONDITIONED_CONTRACT.json`](RECORD_CONDITIONED_CONTRACT.json).

## Inputs

Each query contains:

- the held-out environment, reference setting, metric, and candidate panel
- semantic descriptions of every candidate intervention
- candidate measurements when the condition permits them
- outcomes from other studies when the condition permits history.

The queried study's outcomes never appear in its prompt. Training seeds are
aggregated before prompts and labels are constructed. Historical outcomes are
reported in native units and as within-panel normalized utility. Native units
preserve meaning; normalized utility supplies a common ordering target without
asserting a universal cross-domain scale.

Four matched conditions isolate the value of experimental history and Anarres
measurements:

1. no history, no measurements
2. cross-study history, no measurements
3. no history, with measurements
4. cross-study history, with measurements.

The model ranks a complete target panel in one response. This avoids
candidate-to-candidate scale drift from separate calls.

The serving request uses the frozen high-reasoning setting and a strict JSON
schema containing the exact candidate keys. The completion budget was
qualified against the longest frozen prompt shapes before the protected labels
were opened. The served context supports the longest prompt plus the full
completion ceiling. An identical request may be repeated once only when serving
returns no valid final JSON. Every attempt and token is retained in the cost
record.

## Model and contamination boundary

The first open baseline is `openai/gpt-oss-120b` at the frozen revision in the
contract. Its published June 2024 knowledge cutoff predates the Anarres studies
in this replay. That reduces direct memorization risk but does not eliminate
exposure to older source methods or benchmarks. Candidate aliases are expanded
into plain descriptions, and prompts explicitly prohibit using aliases,
ordering, or omissions as outcome evidence.

The model is not assumed to be optimal. The comparison tests whether a strong,
reproducible record-conditioned model can use the released evidence. Backbone
selection on held-out outcomes is prohibited.

Matched TF-IDF ridge and nearest-neighbor baselines receive the same semantic
environment records and the same measurement ablation. Their hyperparameters
are selected by complete-study validation inside each outer training fold.
This follows the conventional-baseline comparison in the research-world-model
literature without repeating the field-name collapse in the earlier numeric
replay.

## Scoring boundary

Predictions are written and content-addressed before the scorer opens the
protected label artifact. Primary metrics are study-macro allocation regret,
pairwise ordering, and top-choice credit. Inference and measurement costs are
reported separately. A positive retrospective result does not authorize an
adaptive loop; a prospective freeze and an abstention rule remain required.

## Result

The frozen run completed all 36 requests without a retry. The
[prediction receipt](RECORD_CONDITIONED_PREDICTION_RECEIPT.json) binds the
predictions before scoring, and the [runtime
record](RECORD_CONDITIONED_RUNTIME.json) reports the model, serving stack,
hardware class, context limit, tokens, and elapsed request time.

The model with measurements but no outcome history has the lowest point regret
at 0.182. The same model without measurements reaches 0.187, and the best
matched text baseline reaches 0.377. The paired six-study interval for the
record-conditioned improvement over that text baseline is [-0.036, 0.457], so
the apparent gain is not yet stable across studies.

Measurements improve the history-conditioned point regret by 0.135, but the
six-study interval is [-0.141, 0.424]. Cross-study history itself worsens
selection. Without measurements, the history contrast is -0.273 with an
interval of [-0.532, -0.027]. With measurements, it is -0.143 with an interval
of [-0.393, 0.030]. Positive values denote improvement in these contrasts.

The current result therefore supports neither prospective allocation nor a
learned-history claim. It identifies a useful baseline and a concrete failure:
the serialized cross-domain outcome history distracts the predictor. More
independent studies, a development-only history representation, common
measurement-cost fields, and calibrated uncertainty are required before a new
prospective gate.

