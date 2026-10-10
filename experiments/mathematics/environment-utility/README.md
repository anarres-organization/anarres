# Environment utility across model scale

**Status:** Study assets available. A citable research release will follow.

## Overview

Equal RL compute can improve a reasoning policy, do little, or make it worse across different mathematical prompt distributions. This study asks whether measurements collected under the starting policy can predict those differences before the corresponding RL outcomes are observed.

The concrete decision is:

> Given a starting policy and a generated-action-token budget, which measurable environment distribution will produce the most held-out improvement?

We test this question with 32 controlled Qwen3 Base trajectories from 1.7B to 14B parameters. At each scale, four policy-relative OpenR1-Math environments vary group-signal availability and the joint admission-cost profile while holding the trainer, verifier, warm start, and evaluation target fixed. The primary outcome is the change in pass@1 on a disjoint 1,000-prompt panel, measured against cumulative generated action tokens.

## Environment intervention

Here, an environment is a fixed prompt distribution under one rollout, verifier, and optimization contract. Each model scale begins with 4,000 candidate prompts measured under its own starting policy. The study selects four disjoint 256-prompt cells by crossing two controlled factors:

- **Group-signal availability:** whether repeated responses to a prompt are likely to produce reward variation and therefore a nonzero group-relative advantage.
- **Admission and response cost:** whether that signal is likely to survive the loss contract and how many generated tokens are required to obtain it.

The resulting HH, HL, LH, and LL cells are balanced on starting success, prompt length, source, problem type, parseability, and verifier validity. The cells are reconstructed at every model scale because the same prompt can be solved, unreachable, or informative for different starting policies.

Training then changes only the prompt distribution. Every cell at a given scale shares the warm start, optimizer, group size, decoding contract, verifier, horizon, and held-out panel. This isolates the effect of environment choice while the continuous measurements below replace the cell labels for prediction.

## What the study shows

- Environment choice changes held-out pass@1 by as much as 11.4 percentage points at a matched generated-token budget.
- Reward variation alone does not explain the difference. Usable signal density, ρ, and effective coverage, H, track how much learning signal survives the training contract and how broadly it is distributed.
- A model fit through 8B and frozen before the 14B outcomes predicts the untouched 14B utility curves with 2.29-point RMSE.
- A frozen uniform-mixture test marks a current limit. Transfer across model scale does not by itself guarantee transfer to a new environment composition.

The released record supports the predictive curve analysis. Simple fixed-label and crossover rules remain competitive for discrete allocation, so the evidence is strongest for forecasting utility within the controlled environment family.

## Representation

For every prompt group, the probe records the absolute leave-one-out advantage mass that survives the loss contract and the generated action tokens required to obtain it. The environment is summarized by:

```text
ρ(E) = 10⁶ × total admitted advantage mass / generated action tokens

H(E) = effective number of prompts carrying admitted mass / prompt count
```

ρ measures usable signal density. H measures how broadly that signal is distributed. Both are policy-relative and are measured before the corresponding RL outcomes.

## Experimental record

| Component | Released setting |
| --- | --- |
| Models | Qwen3 Base at 1.7B, 4B, 8B, and 14B parameters |
| Environments | Four controlled, policy-relative prompt distributions per scale |
| Training | Two trajectories per scale-by-environment cell under one fixed NeMo GRPO contract |
| Compute axis | Cumulative generated action tokens |
| Evaluation | One fixed, disjoint 1,000-prompt OpenR1-Math panel |
| Prospective tests | A recorded 8B miss, a recalibrated 14B forecast, and a frozen uniform-mixture stress test |

The directory is organized as an executable study record:

- `configs/`: training contracts.
- `data/`: environment manifests, held-out panels, and pre-RL measurements.
- `results/`: compact learning curves, mechanism analyses, forecasts, and sensitivity checks.
- `scripts/`: integrity, reconstruction, and analysis entry points.
- `MANIFEST.sha256`: content hashes for the complete record.

## Inspect the study

```bash
cd experiments/mathematics/environment-utility
python scripts/audit_study.py
python scripts/summarize_prerl.py
python scripts/reproduce_tables.py
```

The first command checks data integrity, disjointness, configuration coverage, evaluation completeness, forecast chronology, and content hashes. The second recomputes ρ and H from response-level metadata. The third rebuilds the compact result tables.

## Scope

The current evidence covers one dense model family, mathematical reasoning with deterministic verification, and one RL contract. Extending the relationship to independently constructed environments and new domains requires renewed measurement and validation.
