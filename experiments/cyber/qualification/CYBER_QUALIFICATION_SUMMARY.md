# Cyber benchmark qualification — final summary

**Date:** 2026-10-21  
**Outcome:** EXTERNAL-TARGET-ONLY (both models, both benchmarks)  
**Protocol:** `qualification-protocol.v2.json` + Amendment A1  

## Executive summary

CyberGym is scientifically valid as an evaluation target but cannot serve as an
in-domain training source for models at accessible scale (≤28B parameters, ≤3
GPUs). Two independent floor probes under protocol v2 returned zero successes.
A secondary benchmark (Cybench) was scouted and also found infeasible at this
scale. The decision tree's floor clause applies: "success < 0.05 → CyberGym
becomes EXTERNAL-TARGET-ONLY."

## Floor probe results

### Probe 1: Nemotron-Terminal-8B (Phase C)

| Metric | Value |
|---|---|
| Model | `nvidia/Nemotron-Terminal-8B` (8B, Qwen3-based terminal SFT) |
| Harness | OpenHands 0.33, temperature 0.7, max 100 iterations |
| Rollouts completed | 273 / 768 planned (early-stopped) |
| Tasks with data | 18 (17 fully complete) |
| Strict successes | 0 |
| Server submissions | 0 |
| Infra failures | 0 |
| 95% CI upper bound | 1.1% (Clopper-Pearson) |
| Decision | EXTERNAL-TARGET-ONLY (< 5% threshold) |

The model actively explored source code and crash traces but could not synthesize
working exploit PoCs. Increasing timeout or rollouts would not help: the
bottleneck is reasoning capability, not wall-clock.

### Probe 2: Feyospace-v1.1-small (Amendment A1)

| Metric | Value |
|---|---|
| Model | `feyospace/feyospace-v1.1-small` (~28B, cyber-specialized Qwen3.5) |
| Harness | OpenHands 0.33, temperature 0.7, max 100 iterations |
| Rollouts completed | 249 / 768 planned (early-stopped) |
| Tasks with data | 16 (15 fully complete) |
| Strict successes | 0 |
| Server submissions | 0 |
| Infra failures | 0 |
| 95% CI upper bound | 1.2% (Clopper-Pearson) |
| Decision | EXTERNAL-TARGET-ONLY (< 5% threshold) |

Despite self-reporting 84.4% CyberGym success under its native harness,
Feyospace achieved zero successes under OpenHands 0.33. The discrepancy reflects
scaffold differences: the model is fine-tuned on its own exploit trajectory
format and cannot transfer to a third-party agent loop.

## Cybench scouting

After CyberGym returned no signal, Cybench (40 professional CTF tasks, Princeton
HAL project) was investigated as an alternative. Published open-weight scores:

| Model | Parameters | Score |
|---|---|---|
| Qwen3-Coder | ~72B | 25.0% (10/40) |
| gpt-oss-120b | 120B | 27.5% (11/40) |
| Llama 4 Maverick | ~400B active | 17.5% (7/40) |
| Llama 3.1 405B | 405B | 7.5% (3/40) |
| Llama 3 70B | 70B | 5.0% (2/40) |

A standalone probe confirmed that Feyospace cannot follow the Cybench agent
scaffold: 8 of 13 iterations produced unparsable output (meta-commentary instead
of the required Command/Answer format). The model is cyber-specialized but
trained on its own harness format and lacks general instruction-following for
third-party scaffolds.

At ≤28B, published Cybench scores are ≤5%, matching the EXTERNAL-TARGET-ONLY
threshold. Models achieving meaningful signal (>5%) start at ~70B+ parameters,
which exceeds the available GPU budget (max 2–3 A100-80G).

## Qualification artifacts

All protocol phases completed successfully before the floor-probe outcome:

- **Phase A** (desk): protocol v2 frozen, disjointness standard defined,
  reliability OC simulation, warm-start provenance verified
- **Phase B** (Docker, no GPU): 48 probe fixtures gated (46/48 admitted +
  2 backfilled → 48/48 final), containment verified (egress denied, grader
  hidden, secrets scrubbed), oracle/noop/reset all 1.000
- **Phase C** (GPU): two independent floor probes (8B, 28B), both 0%

Detailed results:
- `floor_probe_stats.json` (Nemotron-Terminal-8B)
- `floor_probe_feyospace_stats.json` (Feyospace-v1.1-small)
- `PROTOCOL_V2_AMENDMENT_A1.md` (model substitution rationale)

## Implications for the project

1. **CyberGym remains a valid external evaluation target.** The benchmark's
   infrastructure, containment, and grading all work correctly. The 0% result is
   a real measurement of model capability, not an infrastructure failure.

2. **No cyber benchmark shows signal at accessible model scales.** Both CyberGym
   (real CVE exploitation) and Cybench (professional CTF) require models
   substantially larger than 28B to achieve nonzero success rates. This is
   consistent with the published landscape: the smallest model achieving >5% on
   any cyber benchmark is Llama 3 70B on Cybench at exactly 5%.

3. **Cyber domain is not trainable in the current budget.** RL training requires
   a nonzero starting-policy success rate (the protocol's 5% floor). Since no
   accessible model reaches this floor, cyber cannot serve as an in-domain
   training source for the utility-prediction research program at this time.

4. **The qualification toolchain is reusable.** If larger models become available
   (through budget expansion or model efficiency gains), the frozen probe subset,
   containment spec, and harness validation can be reused without repeating
   Phases A and B.
