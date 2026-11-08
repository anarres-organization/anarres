# Literature screening record

This record distinguishes studies that support a comparable intervention panel
from adjacent evidence that informs task design but cannot yet enter the model.
The search covers finance reasoning, long-context analysis, agentic workflows,
data curation, SFT, and reinforcement learning.

## Encoded studies

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

## Relevant studies not yet encoded

These studies remain in the evidence map, but are excluded from the current fit
until their intervention identities and comparable outcomes can be recovered.

- [FinLCR](https://www.amazon.science/publications/finlcr-scaling-financial-long-context-reasoning-via-curriculum-reinforcement-learning)
  studies difficulty-aware curriculum RL across context lengths. Exact
  candidate-level outcomes and a public task manifest still require recovery.
- [QianfanHuijin](https://arxiv.org/abs/2512.24314)
  reports progressive financial SFT, reasoning RL, agentic RL, and general RL.
  The stages change objectives and capabilities together, so the headline
  progression is not yet a matched environment-allocation panel.
- [DianJin-R1](https://arxiv.org/abs/2504.15716)
  provides a finance SFT-to-GRPO recipe. QuantEval supplies a later controlled
  data-scale and stage ablation on the released model, which is the comparison
  currently encoded.
- [Samaya Sterling](https://samaya.ai/blog/rl-post-trained-agentic-model)
  reports finance-research SFT and offline GRPO with expert grading. The
  training questions are internal, so candidate membership and public
  remeasurement are unavailable.

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
