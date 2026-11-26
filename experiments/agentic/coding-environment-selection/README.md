# Agentic coding environment selection

This study asks whether policy-response measurements can identify a useful terminal-training distribution before comparing trained outcomes. It reconstructs two public, internally matched decisions and keeps adaptive environment generation as a separate mechanism question. RLVE uses its pinned starting policy. TMax uses one common reference agent across all candidate pools because the exact historical starting checkpoint is unavailable.

## Result

The frozen policy-response rule first excludes candidates outside a readiness band of 0.10--0.85, then maximizes reward information per unit of generated-token cost. It selects the published best pool on both TMax evaluations and the best RLVE mixture at update 20. At update 60, its selected mixture trails the observed best by 0.40 percentage points.

Across two independent training decisions and four nested endpoints, the rule makes 3/4 best-candidate decisions with 0.10-point mean regret. A starting-performance readiness rule makes 0/4 and has 2.355-point mean regret. Reward information alone makes the same choices as the full rule, so the present evidence supports policy-response measurement but does not establish additional decision value from the readiness gate or cost normalization.

The chronology matters. TMax is an outcome-blind shadow decision reconstructed after publication. RLVE is a prospective decision frozen before the six claim-bearing outcomes were opened. One RLVE training seed and two nested updates leave its winning margin unresolved.

## Representation

Each candidate records four source-native coordinates:

- **readiness:** mean native reward under the declared policy probe, used to exclude environments at either extreme of the measured frontier;
- **reward information:** variation in verifiable outcomes under repeated attempts;
- **cost:** generated output required by the probe;
- **target affinity:** similarity to the intended held-out task family.

These names align the decision logic across sources without pretending that their native estimators or outcome scales are interchangeable. [`data/panels.json`](data/panels.json) preserves the source-specific definitions.

## Mechanism evidence and frontier relevance

The public evidence separates three decisions that are often conflated. TMax and RLVE study which fixed environment pool to train on. EnvSched studies how to reallocate after observing training rollouts. RepoFactory studies how to construct valid, broad, structurally coupled repository environments. Together they suggest a loop in which candidate environments are validated, measured under the current policy, selected for a fixed budget, and then adapted using fresh evidence.

The immediate boundary is composition transfer. The two exact panels do not qualify a universal predictor, and reward information remains a competent simple baseline. The next decisive test is a source-separated candidate set whose environments were assembled independently of these coordinates, with multiple training seeds and the selection rule frozen before outcomes.

## Reproduce

Recompute the released decisions and baseline regrets:

```bash
python experiments/agentic/coding-environment-selection/scripts/reproduce.py
```

Export the source-native candidate measurements into the shared Anarres environment-profile contract:

```bash
python experiments/agentic/coding-environment-selection/scripts/export_environment_profiles.py /tmp/agentic-coding-profiles
anarres qualify /tmp/agentic-coding-profiles/tmax-tmax-15k.profile-input.json
anarres measure /tmp/agentic-coding-profiles/tmax-tmax-15k.profile-input.json \
  --output /tmp/agentic-coding-profiles/tmax-tmax-15k.profile.json
```

The profile export contains only policy-response measurements. Training outcomes remain in the study artifact and never enter qualification or measurement.

[`SOURCE_QUALIFICATION.md`](SOURCE_QUALIFICATION.md) defines the evidence tiers and limitations. [`SOURCES.json`](SOURCES.json) records the audited public sources and licenses.
