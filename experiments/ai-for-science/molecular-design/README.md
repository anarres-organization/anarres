# Predictable post-training for molecular design

## Research program

This program asks whether measurements made before post-training can predict
which molecular-design experience will produce the greatest improvement for a
specified starting policy, protein target, and compute budget. The first study
uses a reaction-based molecular graph policy and a computational
virtual-screening endpoint. It does not make claims about biological efficacy
without experimental validation.

The shared utility object is

$$
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D),
$$

where $E$ is a replay experience distribution, $\pi_0$ is the starting
molecular graph policy, $C$ is a matched generation and oracle budget, and $D$
is a frozen protein-target evaluation. Utility remains specific to the policy,
target, environment family, and budget.

## Current study

The [prospective reaction-environment selection
study](reaction-environment-selection/README.md) uses RxnFlow v2.1.0 and a
qualified MolGenBench Version4 target, Q07820. It holds the molecular action
space, target reward, trainer, and budgets fixed while changing only the replay
experience bank.

Start with the released status and adapter contract:

```bash
uv tool install \
  ./experiments/ai-for-science/molecular-design/reaction-environment-selection
anarres molecular status --repository .
anarres adapter doctor molecular
```

The study compares operational measurements with graph-aware measurements.
Operational measurements cover reward signal, reliability, validity, and
oracle cost. Graph-aware measurements add scaffold, ring-system, reaction,
route, and frozen graph-representation coverage. Six construction-view banks
were tested on untouched confirmation views. The complete-order Version 3
statistic failed because it ranked banks on coordinates they were not designed
to optimize. A sealed diagnostic motivated a Version 4 selector-fidelity gate
that preserved the banks, selectors, estimators, and runtime. All eight
prespecified selector-versus-neutral checks pass in both independent views.
The matched six-bank development study and the two-bank prospective decision
are complete. The frozen graph-aware forecast correctly ranked the operational
hybrid above the graph-aware hybrid at all three budgets. Observed differences
were small relative to the prespecified uncertainty threshold, so the rule
abstained rather than issuing an allocation decision. The full chronology and
claim boundary are reported in the study's
[`RESULTS.md`](reaction-environment-selection/RESULTS.md).

The primary endpoint is a multi-gate qualifying-hit rate rather than raw
docking score. It combines target docking with molecular validity, chemical
filters, pose validity, strain, clash, and target interaction. Supporting
MolGenBench metrics retain enough detail to identify why an environment helps
or fails.

## Research progression

The first loop follows a research-first sequence:

1. qualify source identities, licenses, and public construction fixtures
2. qualify one outcome-blind target, reward adapter, and common warm start
3. measure two independent starting-policy probe views
4. freeze equal-size development and prospective experience banks
5. run matched post-training and score complete utility curves
6. test whether graph-aware measurements improve the prospective decision.

The architecture question is intentionally nested. A later study may compare
the released GINE-style encoder with a parameter-matched GPS encoder after the
environment-selection loop is scored. This order tests whether graph structure
helps choose experience before asking whether a different graph architecture
changes the result.

## Retrospective evidence bridge

The [retrospective molecular-design bridge](retrospective-bridge/README.md)
recovers nine public evidence objects spanning closed-loop active learning,
experience replay, augmentation, molecular representation, target-specific
acquisition, and finite-budget optimization. Four decision audits test early
optimization across 23 oracle tasks, acquisition policies across three
molecular libraries, target-specific acquisition across 50 complex substrates,
and acquisition schedules across four binding-affinity datasets. A separate
Rubisco object tests the resulting UCB-over-random direction on two released
protein-engineering landscapes. Each object retains its native intervention,
budget, and outcome rather than being pooled with unlike decisions. The bridge
provides cross-study context for the candidate-bank hypothesis, while the
RxnFlow study remains the prospective environment-selection test.

The PMO object also supports a charged temporal decision audit. A 1,000-call
pilot combined with a training-fold method prior changes the fixed-method choice
on 18 of 23 held-out oracle tasks. It reaches 84.3% pairwise ordering and 0.078
mean normalized regret while using 14.2% of exhaustive evaluation cost. These
pilot values are early optimization outcomes, so the result complements rather
than replaces the pre-training RxnFlow test.

## Evidence boundary

The first experiment can establish a measurable, prospective relationship for
one public molecular policy and target contract. Generalization requires new
targets, policy families, and eventually experimental feedback. Current
closed-loop work in protein and drug design makes that later progression
important, while preserving a clear boundary between computational screening
and wet-lab evidence.

The current public artifacts qualify the pinned source revisions, Version4
archive and target fixtures, docking oracle, QED warm start, Q07820 target, and
two-view measurement. They preserve the failed Version 3 complete-order result,
the passing Version 4 selector-fidelity confirmation, the frozen forecast, and
the complete prospective endpoint gate. Released outcomes remain downstream
result records and are not converted into environment-profile coordinates.

An installable `anarres-molecular` adapter exposes the native qualification
status and deterministic profile export without changing this evidence
boundary. See [Use the CLI](reaction-environment-selection/README.md#use-the-cli).
