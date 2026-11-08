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
planned MolGenBench Version4 target. It holds the molecular action space,
target reward, trainer, and budgets fixed while changing only the replay
experience bank.

The study compares operational measurements with graph-aware measurements.
Operational measurements cover reward signal, reliability, validity, and
oracle cost. Graph-aware measurements add scaffold, ring-system, reaction,
route, and frozen graph-representation coverage. Six development banks support
model fitting, followed by a frozen prospective decision between an
operational hybrid and a graph-aware hybrid.

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

## Evidence boundary

The first experiment can establish a measurable, prospective relationship for
one public molecular policy and target contract. Generalization requires new
targets, policy families, and eventually experimental feedback. Current
closed-loop work in protein and drug design makes that later progression
important, while preserving a clear boundary between computational screening
and wet-lab evidence.

The current public artifacts qualify the RxnFlow and MolGenBench code revisions
without inspecting outcomes. Dataset, oracle, warm-start, and candidate-freeze
gates remain open. No claim-bearing training is authorized until those gates
pass.
