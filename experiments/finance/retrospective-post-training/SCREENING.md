# Literature screening record

This record distinguishes studies that support a comparable intervention panel
from adjacent evidence that informs task design but cannot yet enter the model.
The search covers finance reasoning, long-context analysis, agentic workflows,
data curation, SFT, and reinforcement learning.

## Current fitted cut

Four studies currently meet the minimum panel contract: a shared starting
policy within each comparison, at least two reported interventions or controls,
a common evaluation target, and enough treatment detail to encode the changed
training environment.

| Study | Encoded comparison |
|---|---|
| [ODA-Fin](https://arxiv.org/abs/2603.07223v1) | raw, partial, distilled, mixed, and table-focused SFT data; verifier and answer-length RL ablations |
| [Fino1](https://arxiv.org/abs/2502.08127v3) | original QA, all chain-of-thought, filtered chain-of-thought, PPO, DPO, and GRPO |
| [Data-Centric Post-Training for Financial Reasoning](https://arxiv.org/abs/2609.10113v1) | ordinary and self-distilled SFT, model merging, hard-example GRPO, and verifier-selected GRPO |
| [QuantEval](https://arxiv.org/abs/2601.08689v3) | SFT data fractions and the subsequent GRPO stage, with knowledge and reasoning outcomes kept separate |

This first cut remains reproducible in [`data/panels.json`](data/panels.json).
It is no longer the full evidence map.

## Source-recovered expansion

A second audit recovered 137 additional decision panels and 491 candidate arms
from twelve primary sources. These rows are stored in
[`data/recovered_panels.json`](data/recovered_panels.json) before feature
mapping or model fitting. This separation prevents the treatment schema from
being changed after inspecting grouped-holdout results.

| Study | Recovered comparison | Panels | Arms |
|---|---|---:|---:|
| [Fine-tuning Smaller Language Models for Question Answering over Financial Documents](https://aclanthology.org/2024.findings-emnlp.617/) | FinQA-only, target-mixture, and full-target training across five student models and FinQA, ConvFinQA, and TATQA outcomes | 20 | 80 |
| [Synthetic Data Generation Using Large Language Models for Financial Question Answering](https://aclanthology.org/2025.finnlp-1.7/) | real versus synthetic data at fixed sample counts, distance-based selection, generation recipes, and real/synthetic mixture fractions | 20 | 55 |
| [Fin-PRM](https://arxiv.org/abs/2508.15202v2) | no training, random selection, general-domain PRM selection, and finance-specific PRM selection | 1 | 5 |
| [How Much Does the Hint Matter?](https://arxiv.org/abs/2610.36082v1) | base, SFT, full-solution OPSD, localized self-distillation, and five-seed hint-writer, KL, and rollout ablations | 2 | 9 |
| [A Factorial Ablation of a Speech-to-SFT Pipeline](https://arxiv.org/abs/2608.20394v1) | base, transcript refinement, QA refinement, and their combination across nine model families and three finance-relevant targets | 27 | 135 |
| [FinLCR](https://aclanthology.org/2026.finnlp-1.3/) | short-to-long curriculum, policy-relative difficulty filtering, their interaction, and five pass-rate windows | 8 | 46 |
| [DianJin-R1](https://arxiv.org/abs/2504.15716) | four SFT source mixtures and the subsequent CFLUE-only GRPO stage across five targets | 5 | 30 |
| [Select to Know](https://aclanthology.org/2025.findings-emnlp.565/) | selective SFT, internal-external fusion, reasoning-data sampling, reward design, and GRPO across three backbones | 7 | 21 |
| [GRPO for Financial Advice Generation](https://aclanthology.org/2026.finnlp-1.27/) | same-backbone base versus finance-reward GRPO under a judge-independent gross-profit CATE audit | 1 | 2 |
| [Constructing Synthetic Instruction Datasets](https://arxiv.org/abs/2603.01353) | synthetic-finance SFT versus financial CPT followed by SFT across two models and two Japanese finance targets | 4 | 8 |
| [FINDAP](https://aclanthology.org/2025.emnlp-main.1579/) | the same joint CPT and instruction-tuned checkpoint before and after preference alignment across similar, novel, finance, reasoning, and general-capability targets | 35 | 70 |
| [FinLMM-R1](https://arxiv.org/abs/2506.13066v1) | complete second-stage reward versus three single-component reward ablations, plus a six-level financial multimodal data-scaling curve | 7 | 30 |

Twenty of these panels hold the reported sample or rollout budget fixed. The
remaining panels retain explicit sample counts or method costs and must not be
described as equal-budget decisions. Accuracy remains separate from completion
rate, generated tokens, safety, and compliance outcomes.

The versioned source-native mapping combines these panels with the initial cut,
producing 149 panels and 538 arms from sixteen studies. The expanded audit evaluates
leave-one-source-out transfer, with nested model and target holdouts as
sensitivities. Source labels are excluded from the predictor, while stable
random fingerprints and shuffled treatment-outcome pairings remain negative
controls.

## Relevant studies not yet encoded

These studies remain in the evidence map, but are excluded from the current fit
until their intervention identities and comparable outcomes can be recovered.

- [CDF-GC](https://aclanthology.org/2025.emnlp-main.1121/)
  compares grammatical-complexity selection with random, length, perplexity,
  and full-data continual-pretraining controls. The reported 20\% selection
  arms and two backbones are promising matched panels. Admission requires a
  source-native extraction that keeps finance gain, general retention, and
  selection cost separate.
- [TELLME](https://aclanthology.org/2026.findings-eacl.84/)
  compares quiz-enhanced continual pretraining with CPT, instruction tuning,
  and instruction-pretraining baselines across several model families. Its
  finance and long-term-retention outcomes can support separate panels after
  the training mixtures and evaluation families are encoded from the primary
  tables.
- [FinToolSyn](https://aclanthology.org/2026.findings-acl.746/)
  reports controlled training ablations for forward-synthesized financial
  tool-use dialogues and dynamic tool retrieval. It is a strong candidate for
  the agentic-finance bridge once dialogue composition, retrieval conditions,
  training volume, and tool-calling outcomes are recovered arm by arm.
- [QianfanHuijin](https://arxiv.org/abs/2512.24314)
  reports progressive financial SFT, reasoning RL, agentic RL, and general RL.
  The stages change objectives and capabilities together, so the headline
  progression is not yet a matched environment-allocation panel.
- [Samaya Sterling](https://samaya.ai/blog/rl-post-trained-agentic-model)
  reports finance-research SFT and offline GRPO with expert grading. The
  training questions are internal, so candidate membership and public
  remeasurement are unavailable.
- [Mixing It Up](https://arxiv.org/abs/2410.01109v2)
  reports 220 finance fine-tuning experiments across four model families and
  nine datasets. Its main tables report the best multi-task outcome or only
  the top three mixtures for each target. Those outcome-selected summaries
  cannot yet support an unbiased candidate-selection panel. The study remains
  important evidence that task composition, general instruction data, and
  mathematics data change finance transfer.
- [FinHarmBench](https://aclanthology.org/2026.acl-industry.117/)
  reports matched safety-alignment interventions across three model families.
  The safety gains and capability measurements form a multi-objective tradeoff
  rather than one scalar utility panel, so they remain a guardrail study until
  the analysis specifies a prospective safety floor.
- [FinED-Bench](https://aclanthology.org/2026.findings-acl.1481/)
  reports one supervised-adaptation arm for financial-document error detection.
  Its remaining controlled comparisons change inference prompting rather than
  the training environment, so they do not form a post-training decision panel.

## Agent and operations evidence

Agent benchmarks identify important outcomes but do not report matched
post-training interventions. FORCE-Bench exposes accuracy and latency effects in
ERP and research workflows. AgenticFinBench separates grounding from correctness
and shows large harness effects. FinRCA-Bench separates retrieval from root-cause
reasoning in reconciliation. TradeOpsSim and Business Bench provide executable
workflow patterns. These sources shape the prospective task and evaluation
contract without entering the retrospective post-training fit.

## Admission rule

A new study enters the model only when one trained intervention remains one
independent row, its starting policy and changed treatment are identifiable, and
the compared arms share a native outcome. Targets, checkpoints, or repeated
criteria remain nested measurements. Missing training membership, seed variance,
or optimization details are recorded rather than imputed.

For sources with many targets or budgets, the panel boundary follows the
decision that could have been made before training. Models, targets, and budgets
are grouping variables, not extra independent studies. Outcome-selected best
mixtures are not admitted as if they were prospective candidates.
