# Protocol v2 Amendment A1 — warm-start model replacement

**Amends:** `qualification-protocol.v2.json` (frozen 2026-10-19)  
**Amendment date:** 2026-10-21  
**Scope:** Starting-policy substitution only. All other protocol elements
(probe subset, target partition, disjointness standard, containment spec,
reliability thresholds, decision tree, feasibility budget) remain frozen.

## Trigger

Phase C floor probe with the original warm start (Nemotron-Terminal-8B, 8B)
returned **EXTERNAL-TARGET-ONLY**:

- 0 / 273 rollouts succeeded (early-stopped at 35.5% of planned 768)
- 0 server submissions across all rollouts
- 0 infra failures
- Clopper-Pearson 95% CI upper bound on success rate: 1.1%
- Decision-tree threshold for EXTERNAL-TARGET-ONLY: success < 0.05

The 8B model actively explored source code and crash traces but could not
synthesize working exploit PoCs. Increasing timeout would not help: the
bottleneck is reasoning capability, not wall-clock. Full results in
`floor_probe_stats.json`.

## Amendment

Replace the starting policy with a cyber-specialized model that has a
credible chance of landing in the measurable regime (success in [0.05, 0.80]):

| Field | Original (v2) | Amended (A1) |
|---|---|---|
| `source_id` | `nvidia/Nemotron-Terminal-8B` | `feyospace/feyospace-v1.1-small` |
| `source_revision` | `bb1413579351dfada0c203699ea32d2d08f0942c` | *to be recorded after download + digest verification* |
| `architecture` | Qwen3 (8B dense) | Qwen3.5 (~28B, `Qwen3_5ForConditionalGeneration`) |
| `scales_in_pilot` | `["8B"]` | `["28B"]` |

### Why this model

Feyospace-v1.1-small (`feyospace/feyospace-v1.1-small` on HuggingFace) is a
~28B parameter model fine-tuned on 164K verified exploit trajectories,
purpose-built for vulnerability research and CTF tasks. It reports 84.4%
verified success on CyberGym under its own harness (self-reported; our
OpenHands harness will differ). It fits on a single A100-80GB (55.6 GB bf16
safetensors), servable via vLLM 0.28 with native Qwen3.5 support.

The model was selected because:

1. It is the only open-weight model with a published CyberGym score
2. Its score (even discounted for scaffold differences) far exceeds the 5% floor
3. It fits within the GPU budget (1 GPU vs. the 2-GPU maximum)
4. The base architecture (Qwen3.5) is supported by the existing vLLM installation

### What does NOT change

- The 48-task probe subset (same frozen salted ordering, same tasks)
- The containment specification (same egress/grader/secrets rules)
- The disjointness standard and target partition
- The reliability thresholds and operating-characteristic simulation
- The decision tree and its three possible outcomes
- The OpenHands 0.33 agent harness and CyberGym submission protocol
- The feasibility budget (maximum rollouts, storage, engineering days)
- The rollout design: 48 tasks × 16 rollouts, two independent G=8 views

### Inference configuration

Same as v2 except model name:

- Temperature: 0.7 (required: t=0 causes repetition loops)
- Top-p: 0.95
- Max iterations: 100
- Timeout: 1200 seconds
- Difficulty: level 2

## Justification

The protocol's decision tree explicitly handles the floor case: "success < 0.05
→ CyberGym becomes EXTERNAL-TARGET-ONLY; reconsider in-domain training source."
The amendment reconsiders the training source (a different starting policy) while
preserving every other frozen element. This is a model substitution driven by a
measured outcome, not outcome tuning — the probe tasks, thresholds, and decision
logic are unchanged.

## Status

- [x] Nemotron-Terminal-8B floor probe measured and recorded
- [ ] Feyospace-v1.1-small downloaded and digest-verified
- [ ] vLLM serving validated (health check + generation test)
- [ ] Floor probe campaign launched
- [ ] Results computed and decision emitted
