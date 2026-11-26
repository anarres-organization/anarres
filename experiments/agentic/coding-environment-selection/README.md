# Agentic coding environment selection

This study asks whether policy-response measurements can identify a useful terminal-training distribution before comparing trained outcomes. It reconstructs two public, internally matched decisions and keeps adaptive environment generation as a separate mechanism question. RLVE uses its pinned starting policy. TMax uses one common reference agent across all candidate pools because the exact historical starting checkpoint is unavailable.

## Result

The frozen policy-response rule first excludes candidates outside a readiness band of 0.10--0.85, then maximizes reward information per unit of generated-token cost. It selects the published best pool on both TMax evaluations and the best RLVE mixture at update 20. At update 60, its selected mixture trails the observed best by 0.40 percentage points.

Across two independent training decisions and four nested endpoints, the rule makes 3/4 best-candidate decisions with 0.10-point mean regret. A starting-performance readiness rule makes 0/4 and has 2.355-point mean regret. Reward information alone makes the same choices as the full rule, so the present evidence supports policy-response measurement but does not establish additional decision value from the readiness gate or cost normalization.

The chronology matters. TMax is an outcome-blind shadow decision reconstructed after publication. RLVE is a prospective decision frozen before the six claim-bearing outcomes were opened. One RLVE training seed and two nested updates leave its winning margin unresolved.

## Source-separated external check

AutoEnvScaling supplies four further matched decisions across two solver scales and two proposer models. Environment Evolution supplies two more under fixed synthesis models and environment counts. A source-native rule prefers calibrated solver feedback or verified progressive lineages scheduled from policy responses. It selects the best candidate in all six decisions and orders all ten forecasted pairs correctly. Static TMax has 5.45 points of mean regret inside AutoEnvScaling, while static environment ensembles have 11.8 points inside Environment Evolution.

These results extend the policy-relative principle to two independently published environment processes, but their chronology is retrospective. The rule was reconstructed after both studies were public, and no cross-study outcome scale is fitted. River separately supports verifier integrity as a mechanism, but its random-pool comparison bundles filtering with behavior shaping and is not counted as an isolated environment-selection decision.

## Retrospective cross-source bridge

A broader bridge now preserves 27 matched endpoint panels, 104 candidate-endpoint rows, and 14 independent training decisions across seven public sources. Source-native measurements are mapped by meaning, while scores are compared only through within-panel ordering and normalized regret. The practical measurement rule reaches 76.9% pair ordering and 0.017 mean normalized regret, compared with 50.0% and 0.529 for an uninformed tie. It receives 94.4% top-choice credit.

The added panels test three distinct decisions. CodeMidas separates environment quality from raw task count under one training recipe. SWE-Gym-Verified compares execution-audited reward labels with original and pass-rate-filtered tasks at fixed size. EnvSched tests the combination of reward differentiation and environment coverage under matched rollout budgets across four model scales. These panels strengthen the shared measurement pattern without making their native coordinates interchangeable. Most outcomes were already public when the bridge was assembled, so the result remains retrospective.

## Regression-risk audit

SWE-Gym-Verified also provides a task-level coding analogue of the legal regression analysis. We average each task's outcome across three training seeds and define a severe regression as a pass-rate decrease of at least 25 points from the common starting policy. The resulting record contains 476 regressions among 4,140 task-environment outcomes. A leave-one-repository-out model using starting behavior, target shift, and training-reward audit status reaches 0.736 ROC AUC, compared with 0.638 from starting behavior alone. Its highest-risk 20% contains 41.8% of the regressions with 24.0% precision. The AUC gain has a repository-clustered 95% interval of [0.045, 0.127].

A smaller benchmark-level view asks whether each trained seed regresses on either held-out target. All five regressions among 24 seed-target outcomes occur on SWE-bench Pro after training on unaudited reward labels. The task-level and benchmark-level results are contained within one public intervention, and both models were reconstructed after publication. They show that reward-label integrity and target shift can help prioritize coding regressions for testing within this study. Transfer to a new training intervention remains untested.

## Representation

Each candidate records four source-native coordinates:

- **readiness:** mean native reward under the declared policy probe, used to exclude environments at either extreme of the measured frontier.
- **reward information:** variation in verifiable outcomes under repeated attempts.
- **cost:** generated output required by the probe.
- **target affinity:** similarity to the intended held-out task family.

These names align the decision logic across sources without pretending that their native estimators or outcome scales are interchangeable. [`data/panels.json`](data/panels.json) preserves the source-specific definitions.

## Mechanism evidence and frontier relevance

The public evidence separates three decisions that are often conflated. TMax and RLVE study which fixed environment pool to train on. EnvSched studies how to reallocate after observing training rollouts. RepoFactory studies how to construct valid, broad, structurally coupled repository environments. Together they suggest a loop in which candidate environments are validated, measured under the current policy, selected for a fixed budget, and then adapted using fresh evidence.

The immediate boundary is composition transfer. The two exact panels do not qualify a universal predictor, and reward information remains a competent simple baseline. The next decisive test is a source-separated candidate set whose environments were assembled independently of these coordinates, with multiple training seeds and the selection rule frozen before outcomes.

## Marin interoperability boundary

Marin's public Qwen3-Coder sweep provides a frontier-relevant integration target: four agentic data sources, fixed-validation records, preserved training diagnostics, and explicit contamination and supersession states. The released BugsInPy and SWE-Gym records use separate held-out task families. They can support recipe comparisons within each dataset when split and runtime contracts match, but they do not form one cross-dataset allocation decision.

The coding adapter validates the released fixed-validation CSV, recomputes pass-rate accounting, preserves discarded and superseded checkpoints, and reports the comparison boundary. The archive does not expose a complete starting-policy probe for every candidate under one target contract, so the adapter does not declare native source qualification or policy probing. A future Marin candidate set can enter the shared Anarres path by recording outcome-free policy measurements under a common target and exporting them as environment profiles before training outcomes are opened.

## Reproduce

Recompute the released decisions and baseline regrets:

```bash
python experiments/agentic/coding-environment-selection/scripts/reproduce.py
python experiments/agentic/coding-environment-selection/scripts/reproduce_external_forecasts.py
python experiments/agentic/coding-environment-selection/scripts/reproduce_retrospective_bridge.py
python experiments/agentic/coding-environment-selection/scripts/reproduce_regression_risk.py
python experiments/agentic/coding-environment-selection/scripts/reproduce_task_regression.py
```

Export the source-native candidate measurements into the shared Anarres environment-profile contract:

```bash
python experiments/agentic/coding-environment-selection/scripts/export_environment_profiles.py /tmp/agentic-coding-profiles
anarres qualify /tmp/agentic-coding-profiles/tmax-tmax-15k.profile-input.json
anarres measure /tmp/agentic-coding-profiles/tmax-tmax-15k.profile-input.json \
  --output /tmp/agentic-coding-profiles/tmax-tmax-15k.profile.json
```

The profile export contains only policy-response measurements. Training outcomes remain in the study artifact and never enter qualification or measurement.

Export the outcome-free external design profiles through the same generic CLI contract:

```bash
python experiments/agentic/coding-environment-selection/scripts/export_external_profiles.py /tmp/agentic-coding-external-profiles
anarres qualify /tmp/agentic-coding-external-profiles/autoenv_qwen3_5_9b_gpt_5_6_sol-autoenvscaling.profile-input.json
```

[`SOURCE_QUALIFICATION.md`](SOURCE_QUALIFICATION.md) defines the evidence tiers and limitations. [`SOURCES.json`](SOURCES.json) records the audited public sources and licenses.

Install the study-local CLI and inspect the released evidence:

```bash
uv tool install ./experiments/agentic/coding-environment-selection
anarres adapter doctor coding
anarres coding status --repository .
anarres coding regressions --repository .
anarres coding profile --repository . --output /tmp/agentic-coding-profiles
```

Audit a pinned Marin fixed-validation record without merging unlike targets:

```bash
anarres coding audit-marin-evidence \
  --csv software-transfer-fixed-validation.csv \
  --sha256 <sha256> \
  --source-revision <revision> \
  --source-license <license-or-usage-terms>
```
