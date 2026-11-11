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
64.1% of candidate pairs and has 0.304 mean normalized regret, compared with
56.0% and 0.489 for choosing more data. Its regret is also below the fifth
percentile from 200 within-panel shuffled-pairing controls. The grouped ridge
has lower magnitude error but weaker allocation performance than the rule. The
exploratory seven-coordinate ridge gives the best study-macro calibration at
0.400 RMSE. The full ridge reaches 71.8% study-macro pair ordering and 0.220
regret, while the practical rule remains strongest for decisions.

Equal-study weighting strengthens the comparison. The practical rule reaches
74.9% pair ordering, 72.5% top-choice credit, and 0.170 regret, compared with
58.2%, 37.6%, and 0.421 for more data. It has lower regret in thirteen of sixteen
held-out studies, ties in one, and loses in two. The same ordering survives
replacement of min-to-max utility with within-panel ranks. The exact two-sided
sign-test value is 0.007 across the fifteen non-tied studies. This is a
retrospective breadth test, not evidence from a frozen selector. The full
normalization and weighting rationale is recorded in
[`NORMALIZATION_AUDIT.md`](NORMALIZATION_AUDIT.md).

The direction does not depend on the two sources that report only one decision
panel. Restricting the audit to fourteen multi-panel studies yields 72.0% pair
ordering and 0.194 regret for the practical rule, compared with 58.7% and 0.424
for more data. Removing any single source also preserves the practical rule's
regret advantage, with a study-macro gap of 0.233 to 0.272. These sensitivities
prevent a small or unusually favorable table from driving the result.

A publication-date sensitivity fits the learned models on seven studies released
in 2024--2025 and scores nine sources released in 2026. The full ridge reaches
72.4% study-macro pair ordering and 0.248 regret, compared with 57.3% and 0.434
for more data. The fixed practical rule reaches 71.8% ordering and 0.200 regret.
Publication order reduces direct outcome reuse but does not make this a
prospective test because the shared semantic schema was assembled after these
results were public.

The result is also stable to ordinary modeling choices. Removing any one
coordinate from the practical rule leaves study-macro ordering between 72.3%
and 75.6% and regret between 0.167 and 0.215. Varying the ridge penalty from
0.5 to 16 leaves full-model ordering between 71.8% and 72.9%, with regret from
0.196 to 0.224. The relationship is therefore not carried by one semantic
coordinate or one regularization value.

## Frozen source-level holdout

We next froze the shared representation and its candidate rankings before
extracting results from SNFinLLM, an independently reported Chinese financial
model absent from feature design and fitting. The test changes model family,
language, data pipeline, and evaluation targets. It therefore asks whether the
semantic treatment coordinates transfer to a new experimental program.

The frozen rule and both ridge models correctly predict that continued financial
pretraining outperforms the original general base on FinEval and FinanceIQ. They
do not predict the later stage effects. SFT trails continued pretraining on both
shared benchmarks, and DPO improves only one of seven comparable targets over
SFT. Across all seven target panels, the frozen ranking receives 41.2% pairwise
ordering credit, 14.3% top-choice credit, and 0.783 normalized regret. The
uninformed more-data baseline ties all candidates because comparable volume is
unreported, giving 50.0%, 42.9%, and 0.504 respectively.

This result narrows the transferable claim. Target-aligned domain adaptation is
predictable from the current representation, while later post-training stages
require a coordinate for objective--target alignment. DPO should receive quality
credit only when its preference signal is connected to the evaluation target.
The full freeze, extracted outcomes, scoring code, and result are in
[`heldout-snfinllm/`](heldout-snfinllm/).

A target-conditional revision was then frozen on staged adaptation for Japanese
financial documents. It gets 4 of 8 meaningful task-level directions correct.
The domain-adaptation direction holds in aggregate, but individual finance tasks
regress, the full path loses to a skip-stage ablation on two of three meaningful
finance targets, and the visual-stage prediction has no matching visual outcome.
The complete audit is in
[`heldout-japanese-multimodal/`](heldout-japanese-multimodal/).

## Strict task-level reliability tier

The broad bridge includes sources whose target relationship is only partially
reported. A stricter audit admits panels only when every candidate has an
explicit target-alignment measurement and the model and target are identified.
This leaves 79 panels, 241 arms, and seven studies. The already-fixed practical
rule orders 81.6% of candidate pairs with 0.162 normalized regret, compared
with 63.1% and 0.444 for choosing more data. With equal study weighting it
reaches 83.6% ordering and 0.098 regret. It has lower regret in six studies,
ties in one, and loses in none.

The score margin adds a calibrated abstention option. With each threshold
selected from the other six sources, the 0.85 training-precision operating point
orders 90.4% of 235 decided held-out pairs while retaining 76.1% coverage. Its
equal-source accuracy is 89.6%, and every source retains decisions. Data volume
reaches 61.0% accuracy on 100 decisions from one source and abstains on the
other six under the same procedure. The full sensitivity is included in the
[`strict task-level audit`](strict-task-level/README.md).

The strict audit is the current high-confidence tier because its decision unit
is a candidate--target pair rather than a stage-level label. It remains
retrospective and requires an excluded-source test. The complete record is in
[`strict-task-level/`](strict-task-level/).

The same fixed rule also provides a useful regression-risk signal. We compare
165 treatments with their explicit study-matched baselines across 44 panels and
eight sources. Five sources contain both regressions and improvements, allowing
within-source discrimination to be measured. The rule reaches 0.815
source-macro ROC AUC, compared with 0.575 for data volume alone. Source-macro
performance is primary because one study contributes most of the contrasts.
This secondary audit shows that the representation can flag task-level downside
as well as rank candidate utility, while remaining retrospective. The released
result is [`results/regression_risk_summary.json`](results/regression_risk_summary.json).

That excluded-source test was frozen on numerical faithfulness in financial
summarization. Its content-alignment prediction fails: at matched volume,
financial QA and numeracy training raises overt hallucination from 64.6% to
90.8%. The base model also remains much safer than finance-language adaptation.
The result shows that content alignment must be separated from alignment with
the target's behavioral contract, including grounding and abstention. The full
freeze and score are in
[`heldout-numerical-hallucination/`](heldout-numerical-hallucination/), and the
revised research specification is
[`TARGET_CONDITIONAL_V4.md`](TARGET_CONDITIONAL_V4.md).

We then apply that pre-existing V4 representation to FinAcumen, an excluded
source that varies deterministic financial tools, conditional experience
memory, and memory contents under shared backbones. The representation recovers
33 of 33 scored candidate orderings across 16 nested panels with zero normalized
regret. It correctly orders the full memory-field ablation and predicts the
intervention direction across Qwen, GLM, GPT, and Gemini backbones. Four
comparisons between memory baselines remain unranked because their remaining
implementation differences are outside the representation. These rows provide
one retrospective source-level test rather than independent replications. The
contract, source-native outcomes, and score are in
[`heldout-finacumen/`](heldout-finacumen/).

A second V4 test freezes a safety-constrained decision before extracting the
numerical FinHarmBench table. FiRSD qualifies for Llama3-8B-Instruct and
AdaptLLM-Finance-chat-7B. It reduces attack success, stays within the benign
helpfulness guardrail, and retains at least 95% of average external capability.
The same intervention is rejected for WiroAI-Finance-Gemma-9B because benign
accuracy falls 7.69 points, beyond the frozen five-point limit. The result shows
how one model-agnostic contract can produce different model-level decisions
without making model identity a feature. The freeze and score are in
[`heldout-finharmbench/`](heldout-finharmbench/).

FinToolSyn then tests the same capability-contract representation in an
agentic tool environment. The study holds the Qwen3-8B training contract fixed
while varying reverse or forward dialogue synthesis and static or dynamic tool
retrieval. All nine high-confidence directional comparisons are correct, as
are both best-candidate decisions and all three improvement or regression
calls. Reverse synthesis improves tool calling while regressing on the balanced
average and non-tool behavior. The audit abstains from comparisons that require
an unmeasured tradeoff between starting-policy retention and forward
supervision. The source record, predictions, outcomes, and score are in
[`heldout-fintoolsyn/`](heldout-fintoolsyn/).

LongFinanceQA provides an outcome-separated component test in financial
long-context reasoning. We froze six directional hypotheses after reading only
the paper's abstract, then opened its component tables. Four hypotheses have
matched controls. Across their 25 reported task-band comparisons, 24 follow the
frozen direction. Intermediate reasoning improves every overall context band,
11 of 12 multi-source comparisons, and every single-source comparison. Full
PAI also outperforms its property-extraction ablation in every reported band
and in the aggregate. Retrieval and summarization are not separately ablated,
so those predictions remain unscored. The freeze, table extraction, scorer,
and result are in [`heldout-longfinanceqa/`](heldout-longfinanceqa/). This is
one source-level test rather than 25 independent studies.

CDF-GC adds an excluded-source test of finance continual-pretraining data
selection across Llama-3.2-1B and Qwen2.5-0.5B. The pre-existing
capability-contract representation predicts that complexity- and
diversity-aware selection should lead the finance target while continual
pre-training without a retention mechanism can weaken general capability.
Twenty-one of 22 scored directions are correct. CDF-GC is the best finance
candidate for both backbones, while the starting model leads general retention
on Qwen and trails CDF-GC by 0.5 points on Llama. The four panel-level choices
give 3/4 best-candidate accuracy and 0.096 normalized regret. The full source
record and score are in [`heldout-cdf-gc/`](heldout-cdf-gc/).

A derived alignment/interference coordinate does not improve the original
sixteen-study source holdout. Against the corrected baseline, the fixed rule
falls from 74.9% to 74.0% pairwise ordering with unchanged regret. The ridge
falls from 71.8% to 71.0% ordering and has worse magnitude error, despite a
0.003 reduction in regret. We therefore retain the corrected earlier bridge and
move the next analysis to task-level re-encoding. The diagnostic is recorded in
[`results/target_conditional_diagnostic.json`](results/target_conditional_diagnostic.json).

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
python scripts/analyze_expanded_bridge_corrected.py
python scripts/render_expanded_summary.py
python -m unittest test_expanded_bridge.py test_expanded_bridge_corrected.py
python heldout-snfinllm/freeze_predictions.py
python heldout-snfinllm/score_holdout.py
python -m unittest heldout-snfinllm/test_freeze.py heldout-snfinllm/test_score.py
python heldout-japanese-multimodal/score_holdout.py
python -m unittest heldout-japanese-multimodal/test_score.py
python scripts/analyze_target_conditional_diagnostic.py
python -m unittest test_target_conditional_diagnostic.py
python strict-task-level/score.py
python -m unittest strict-task-level/test_score.py
python strict-task-level/score_selective.py
python strict-task-level/test_selective.py
python scripts/analyze_regression_risk.py
python test_regression_risk.py
python heldout-numerical-hallucination/score_holdout.py
python -m unittest heldout-numerical-hallucination/test_score.py
python heldout-finacumen/score_holdout.py
python -m unittest heldout-finacumen/test_score.py
python heldout-finharmbench/score_holdout.py
python -m unittest heldout-finharmbench/test_score.py
python heldout-fintoolsyn/score_holdout.py
python heldout-fintoolsyn/test_score.py
python heldout-longfinanceqa/score_holdout.py
python heldout-longfinanceqa/test_score.py
python heldout-cdf-gc/score_holdout.py
python heldout-cdf-gc/test_score.py
```

The script writes [`results/summary.json`](results/summary.json) and a manifest
of its inputs and outputs. The current expanded analysis is
[`results/expanded_summary_corrected.json`](results/expanded_summary_corrected.json),
with an independent
[`results/EXPANDED_CORRECTED_MANIFEST.sha256.json`](results/EXPANDED_CORRECTED_MANIFEST.sha256.json)
covering its mapping, sources, inputs, scripts, and result. The earlier
[`results/expanded_summary.json`](results/expanded_summary.json) remains
available because it entered the frozen source-holdout chronology. Any result
used to design a future test must remain labeled retrospective until it is
frozen and evaluated on untouched outcomes.
