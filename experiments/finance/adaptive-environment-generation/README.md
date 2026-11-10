# Adaptive environment generation for finance agents

Finance agents can improve through model-weight updates, but also through the
procedures, tools, feedback, and retained experience available on later tasks.
These mechanisms create a lower-cost test of environment selection: identify a
failure, propose several ways to address it, and decide which proposal should be
promoted before its downstream outcome is opened.

This study asks:

> Can measurements available before deployment predict which task, skill, or
> feedback proposal will improve later financial work without creating a
> protected-case or control regression?

The study extends environment selection from a single training run to a
repeated improvement loop:

1. observe typed failures on a development stream
2. generate candidate tasks, procedures, tools, or feedback carriers
3. qualify each candidate against executable checks and scope constraints
4. measure its target coverage, policy need, cost, and protected-case coverage
5. select, reject, or abstain without reading later-case outcomes
6. evaluate on sealed target and guardrail cases
7. preserve the complete decision record before beginning the next round.

The loop is successful only when later decisions improve. Generating more
tasks or retaining more experience is not itself evidence of improvement.

## Why this is the next finance test

Released finance studies already contain controlled decisions about the form
and admission of experience:

- [FinSkillBench](https://arxiv.org/abs/2608.18099) compares no skill, curated
  procedural resources, and skills generated within an episode over 2,603
  verifiable investment-management episodes. Curated resources improve mean
  performance, while naive within-episode generation adds little at higher
  cost.
- [Knowledge or Calculator?](https://arxiv.org/abs/2610.03564) separates
  procedural documents from executable tools. Their value depends on the
  workflow, which makes resource choice a target-conditional decision.
- [FinEvo-Bench](https://arxiv.org/abs/2608.06144) compares retained experience
  across 120 professional tasks and paired state-reset controls. It also
  separates skill, memory, and feedback choices.
- [FINSKILLOPS](https://arxiv.org/abs/2609.19680) admits only six of 33 proposed
  skills after targeted validation, negative controls, and protected-case
  regression checks.
- [FilingLoop](https://arxiv.org/abs/2610.37905) converts requirement-level
  feedback into procedures used only on later disclosure cases, preserving the
  chronology needed to evaluate cross-case improvement.
- [Auditing Self-Evolution in Financial
  Agents](https://arxiv.org/abs/2608.17684) shows why capability, exposure to
  injected content, attack success, and unauthorized state changes must remain
  separate outcomes.

These studies provide the finance analogue of the public learning-dynamics and
external-check records used in the legal and robotics programs. They allow the
selection rule to be tested across released interventions before a larger
native training panel is justified.

## First public bridge

The first bridge will normalize decisions rather than raw benchmark scores.
Each panel contains candidates that share a model, task family, outcome
contract, and evaluation budget. Candidate outcomes remain source-native.

The prediction unit is one candidate experience carrier applied to one target
contract. Examples include:

- procedural documentation, executable tools, or both
- retained skills, memory, or a combined carrier
- rubric feedback or reference-answer feedback
- a proposed scoped skill versus rejection or replacement
- an updated disclosure procedure versus a fixed procedure.

Measurements available before the held-out outcome include:

- target and failure-mode coverage
- executable support and verifier reliability
- candidate scope and protected-case coverage
- evidence, temporal, and authorization requirements
- policy-relative failure rate or learning opportunity
- expected token, tool, validation, and human-review cost
- exposure to untrusted content and authority-bearing actions.

No study's downstream outcomes may enter the rule used to score that study.
Source-held-out evaluation reports pair ordering, normalized regret, regression
precision, guardrail violations, and abstention coverage. More experience,
starting performance, and a source-native practical rule remain explicit
baselines.

## First closed-loop demonstration

The lowest-cost native demonstration does not begin with model-weight training.
It begins with a released verifiable finance task family and two rounds of
candidate improvement:

1. freeze development, target, protected, and negative-control partitions
2. collect typed failures from the development partition
3. produce several scoped skill or task proposals from those failures
4. validate syntax, execution, evidence use, and declared scope
5. freeze the selector's promotion, rejection, or abstention decisions
6. run admitted candidates on untouched target and protected cases
7. repeat the process once using only the newly available development record.

The primary claim requires the selector to improve later-case utility relative
to retain-all, latest-proposal, and no-update controls. A candidate is not
promoted when its predicted gain is smaller than uncertainty or when a material
guardrail fails. The study reports proposal cost and validation cost in
addition to downstream execution cost.

## Development bridge result

The first normalized bridge contains 53 arms in 17 matched decision panels
from five primary sources. Source-native outcomes are normalized only within a
panel. A ridge fit with one complete source held out reaches 80.3% pairwise
ordering, 58.8% top-choice accuracy, and 0.119 mean normalized regret. A rule
that only distinguishes update from no update reaches 75.8% ordering and 0.122
regret, but cannot reliably choose among several updates.

A fixed practical rule constructed while auditing these sources reaches 98.5%
pairwise ordering and selects the observed best arm in all 17 panels. This is a
development diagnostic rather than validation because its representation and
weights were specified after the source papers were available. It defines the
hypothesis to freeze on an excluded source.

Guardrails change the decision in the e-banking panel. The practical rule
selects ReasoningBank on benign utility, but its unauthorized-state rate is
0.595 compared with 0.583 for the static baseline. The control-constrained
decision is therefore blocked even though benign utility improves. Capability
and financial-state safety are not collapsed into one score.

## Relationship to model-weight training

The generator-qualified accounting panel remains a valuable causal test. It
asks whether the same measurement discipline chooses a better task mixture
when every candidate receives a matched model-weight training budget. It is a
later validation rather than a prerequisite for testing the decision loop.

The adaptive study and the accounting panel answer different questions. The
adaptive study tests whether experience can be proposed, screened, and retained
over repeated rounds. The accounting panel tests whether selected task
distributions produce better policies after matched training. Evidence from
both is needed before treating the loop as a general environment optimizer.

## Current status

The development bridge, protocol, and primary-source audit are complete. The
bridge is retrospective and does not qualify the selector. A separately frozen
[ProFinAgent component test](heldout-profinagent/README.md) gets three of five
prediction families correct. The two central component comparisons transfer
across all nine reported model-by-complexity cells, while two broader
generalizations fail. The native two-round result remains open.

The native path is now frozen on a ten-task
[QF-Bench risk-transfer panel](native-qfbench-v1/README.md). The external
benchmark provides air-gapped execution, reference solutions, deterministic
unit-test verifiers, and complete trajectory and cost records. Its source pin,
task split, candidate resource types, decision rubric, and success criteria are
fixed before any model-generated development or target outcome is opened.
