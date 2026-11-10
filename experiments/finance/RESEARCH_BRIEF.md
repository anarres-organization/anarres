# Predicting which finance training environments will work

Finance agents are moving from document retrieval toward workflows that reconcile
records, investigate exceptions, prepare accounting entries, and act through
controlled tools. The open research question is no longer only whether an agent
can complete one task. It is whether we can predict which training experience
will improve that agent before committing a large post-training budget.

Anarres studies that decision directly:

> Given a starting policy and a fixed training budget, which measurable finance
> environment will produce the most held-out improvement while preserving
> material controls?

## What is complete

### Published intervention evidence

The source-recovered bridge contains 538 intervention and control arms across
149 comparable decision panels from sixteen finance post-training studies. Every
study is held out in turn for the strictest retrospective test.

![Expanded finance evidence bridge](retrospective-post-training/figures/expanded_evidence_bridge.svg)

Under leave-one-study-out evaluation, an interpretable measurement rule orders
64.1% of candidate pairs with 0.304 mean normalized regret. Choosing more data
orders 56.0% with 0.489 regret. The measurement rule also falls below the fifth
percentile of regret from 200 within-panel shuffled-pairing controls. A grouped
ridge predicts outcome magnitude better but allocates less reliably across a
new study. When the study is known, ridge transfer to a held-out model reaches
76.9% pair ordering and 0.152 regret. Transfer to a held-out target reaches
74.1% and 0.162. The difference between within-program transfer and new-study
transfer defines the current boundary.

With each study receiving equal weight, the expanded rule reaches 74.9% pair
ordering and 0.170 regret, compared with 58.2% and 0.421 for more data. It has
lower regret in thirteen of sixteen studies, ties in one, and loses in two.
Removing any one source preserves the direction. A publication-date sensitivity
fits the learned relationship on seven studies from 2024--2025 and evaluates
nine 2026 sources, where the full ridge reaches 72.4% ordering and 0.248 regret.
These checks strengthen the retrospective relationship without converting it
into a prospective result. Removing any one coordinate from the practical rule
or varying ridge regularization over a 32-fold range preserves the main
ordering advantage.
Within-panel rank normalization preserves the direction. The
[normalization audit](retrospective-post-training/NORMALIZATION_AUDIT.md)
records both weighting levels and the paired source comparison.

A strict task-level audit narrows the evidence to seven studies in which every
candidate has an explicit relationship to the evaluation target. Across 79
panels and 241 arms, the fixed practical rule reaches 81.6% pair ordering and
0.162 regret, compared with 63.1% and 0.444 for more data. With equal study
weighting it reaches 83.6% ordering and 0.098 regret. This is the strongest
current evidence for a model-agnostic relationship, although it remains
retrospective and still needs an excluded-source test.

A source-held-out confidence filter raises ordering accuracy to 90.4% over 235
decided pairs while retaining 76.1% coverage. Thresholds are learned from the
other six sources in every fold, and equal-source accuracy is 89.6%. This adds
an explicit abstention action when candidate scores are too close for the
available evidence.

The fixed rule also predicts whether an intervention will regress relative to
its study-matched baseline. Across 165 treatment contrasts, it reaches 0.815
source-macro ROC AUC on the five sources with both regressions and improvements,
compared with 0.575 for data volume alone. This adds regression risk as a second
released outcome alongside candidate ordering.

The first excluded-source test of that stricter relationship examines numerical
faithfulness in financial summarization. Its prediction fails. Financial QA and
numeracy training increases overt hallucination from 64.6% to 90.8% at matched
volume, while the untouched base remains substantially safer than either
finance-adapted model. This result separates content alignment from alignment
with the target's behavioral contract. A revised representation now records
grounding, abstention, and output constraints explicitly before another source
is tested.

The evidence suggests that task alignment, reasoning-data quality, capability
retention, verifier design, policy-relative difficulty, and data composition
carry more decision information than volume alone. Because every outcome was
already public, this remains retrospective evidence rather than prospective
validation.

### Frozen transfer to untouched sources

We froze the shared representation and candidate rankings before extracting
results from SNFinLLM, an independently reported Chinese financial model that
did not enter feature design or fitting. The frozen methods correctly predict
that continued financial pretraining improves on the original base across both
public benchmarks. They do not predict the effects of later SFT and DPO. SFT
trails continued pretraining on the two shared benchmarks, while DPO improves
one of seven comparable targets over SFT and reduces the other six.

Across seven target panels, the frozen ranking receives 41.2% pairwise ordering
credit, 14.3% top-choice credit, and 0.783 normalized regret. This result
identifies a specific missing coordinate. Data quality and objective--target
alignment must be represented separately, because a generic preference stage
does not imply that its feedback improves the target being predicted. The full
freeze and scoring record are available in the
[source-level holdout](retrospective-post-training/heldout-snfinllm/README.md).

A second freeze tests a target-conditional revision on staged adaptation for
Japanese financial documents. Financial text adaptation improves the aggregate
JP Fin Harness score, but two of five subtasks regress. The full staged path
improves fraud detection while trailing the skip-stage ablation on industry
classification and finance knowledge. One visual-stage prediction is unscorable
because every reported benchmark uses text input. The frozen claims are correct
on 4 of 8 meaningful task-level directions.

Together, the holdouts identify the same boundary from different pipelines.
Domain adaptation can transfer in aggregate while individual tasks move in
opposite directions. A broad derived interference coordinate does not improve
the original sixteen-study leave-one-source-out result, so it is not added to
the fitted bridge. The next representation must encode treatment alignment,
interference, and retention at task level.

### Executable workflow qualification

Four stateful finance workflows passed strict generator checks across five seeds
each. All 20 workflow-seed trials passed deterministic-oracle, null-agent,
negative-control, handbook-citation, and state-identity checks. This qualifies a
source for prospective construction. It does not reveal which training mixture
will work best.

### Domain selection

The primary operational target is reconciliation and controlled exception
handling. These tasks have exact records, planted breaks, asymmetric error costs,
reviewable evidence, and explicit approval or escalation rules. They also match
the direction of current finance-agent systems. [Ramp Accounting
Bench](https://labs.ramp.com/accountingbench) evaluates agents across ledgers,
bank statements, invoices, and reconciliation workbooks. [Anthropic's finance
agents](https://www.anthropic.com/news/finance-agents) emphasize close workflows,
tool permissions, audit logs, and human review. [Bank of England and FCA survey
evidence](https://www.bankofengland.co.uk/report/2026/artificial-intelligence-in-uk-financial-services-2026)
places most deployed financial agents in decision-support roles and finds that
Operations and IT is the largest area of reported AI use.

This priority is also reflected in current systems and public benchmarks.
Anthropic includes ledger reconciliation, month-end close, statement audit,
KYC, and valuation review among its finance-agent templates. Ramp emphasizes
reconciliation, journal entries, accruals, variance analysis, and controlled
spend workflows. OpenAI's Endex case study highlights financial-model
reconciliation and source-linked discrepancy detection. FinBalance and
FORCE-Bench provide public evaluation designs for document-grounded accounting,
ERP research, and evidence-backed finance work.

The broader [agent-systems evidence map](agent-systems-evidence/README.md)
adds Finch, FinMaster, RealFin, AgenticFinBench, FinNextAssist, DealTrace, and a
controlled tool-surface ablation. Together they show why the prospective task
must measure evidence, calculation, workflow orchestration, recovery, and
controls in addition to final-answer accuracy.

## The next tests

The first excluded-source test of the capability-contract representation uses
FinAcumen's controlled financial-tool and experience-memory interventions. The
representation recovers all 33 scored candidate orderings across 16 nested
panels and several backbones. This result supports the model-agnostic task
description, but it remains one retrospective source. A second test freezes a
safety-constrained decision before extracting FinHarmBench's numerical table.
It accepts the intervention for two models and rejects it for WiroAI because
benign helpfulness falls beyond the fixed guardrail. The next source should
test a new workflow contract and continue reporting decisions, regressions,
and abstention separately.

FinToolSyn provides that agentic-finance test. Under a shared Qwen3-8B training
contract, it varies reverse or forward dialogue synthesis and static or dynamic
tool retrieval. The pre-existing capability-contract representation gets all
nine high-confidence directions correct, selects the best candidate on both
targets where it makes a selection, and correctly predicts three improvement
or regression directions. In particular, reverse synthesis improves tool-call
performance while reducing the balanced average and non-tool score relative to
the base. The audit abstains where the source-native non-tool metrics support
different orderings.

The executable accounting panel remains the prospective extension. Four
stateful workflows have passed source qualification, but no model has yet
qualified as a non-degenerate starting policy. Training begins only after the
chosen policy reliably uses tools and produces enough outcome variation to
support a real environment decision.

That comparison will include:

1. a source-proportional mixture
2. a size-matched static-difficulty mixture
3. a policy-relative usable-signal mixture
4. a policy-relative mixture with an explicit workflow-coverage constraint.

The primary outcome is held-out executable completion. Reconciliation precision,
exception recall, ledger consistency, evidence provenance, approval violations,
unauthorized state changes, tool cost, and generated tokens remain separately
visible. A high aggregate score cannot erase a material-control failure.

An additional panel extends the same decision to post-trade reconciliation and
exception handling. FINOS Common Domain Model provides lifecycle semantics,
while RecBench, TradeOpsSim, and FinRCA-Bench inform the data and evaluation
contract. None is yet admitted as the claim-bearing generator. The post-trade
panel begins only after its discrepancy generator and precision-first evaluator
pass the same deterministic-oracle, negative-control, identity, and licensing
gates.

## Why this result would matter

Finance-agent teams currently compare models, prompts, tools, skills, and task
sets through expensive end-to-end runs. A validated environment-utility model
would add an earlier decision point: measure candidate experience under the
starting policy, estimate its finite-budget return, and train only after the
selection and uncertainty are recorded.

The present evidence supports domain adaptation while exposing a boundary for
later post-training stages. Task-level re-encoding is now the decisive
retrospective test. The prospective accounting comparison then asks whether the
resulting measurements change a real allocation decision relative to transparent
quality-aware and volume-based baselines.

## Questions for finance practitioners

The study is designed to incorporate domain knowledge before the prospective
contract is frozen. The most useful input concerns:

- which reconciliation or exception families consume the most review effort
- which false matches, missed breaks, or unsupported actions carry material cost
- which evidence and approvals are required before an action is permitted
- which workflow boundaries should remain separate evaluation endpoints
- what improvement would justify the cost of measuring candidate environments.

These questions refine the task and control contract. They do not expose or
change held-out outcomes after training begins.

## Inspect and reproduce

- [Retrospective methods and interpretation](retrospective-post-training/README.md)
- [Frozen source-level holdout](retrospective-post-training/heldout-snfinllm/README.md)
- [Target-conditional source holdout](retrospective-post-training/heldout-japanese-multimodal/README.md)
- [Strict task-level transfer audit](retrospective-post-training/strict-task-level/README.md)
- [Numerical-faithfulness source holdout](retrospective-post-training/heldout-numerical-hallucination/README.md)
- [Financial tools and experience-memory source holdout](retrospective-post-training/heldout-finacumen/README.md)
- [Financial safety capability-contract holdout](retrospective-post-training/heldout-finharmbench/README.md)
- [Agentic tool-environment holdout](retrospective-post-training/heldout-fintoolsyn/README.md)
- [Capability-contract representation](retrospective-post-training/TARGET_CONDITIONAL_V4.md)
- [Machine-readable panels](retrospective-post-training/data/panels.json)
- [Source-recovered expansion](retrospective-post-training/data/recovered_panels.json)
- [Machine-readable results](retrospective-post-training/results/summary.json)
- [Corrected expanded grouped results](retrospective-post-training/results/expanded_summary_corrected.json)
- [Agent-systems evidence map](agent-systems-evidence/README.md)
- [Prospective protocol](environment-selection/README.md)
- [Qualified-source record](environment-selection/PREFLIGHT.json)
- [Post-trade panel specification](environment-selection/POST_TRADE_PANEL_SPEC.md)

```bash
cd experiments/finance/retrospective-post-training
python scripts/reproduce.py
python scripts/render_summary.py
python scripts/build_recovered_panels.py
python scripts/analyze_expanded_bridge.py
python scripts/analyze_expanded_bridge_corrected.py
python scripts/render_expanded_summary.py
python test_reproduce.py
```

The source registry pins paper versions, repository revisions, licenses, and the
evidence admitted from each source.
