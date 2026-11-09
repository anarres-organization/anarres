# Prospective post-trade environment-selection panel

This specification turns the post-trade source audit into a concrete experiment.
It remains a design until the scenario generator, evaluator, starting policy,
and task bank pass qualification.

## Decision

> Given one starting policy and a fixed post-training budget, which distribution
> of reconciliation and exception-handling cases produces the greatest held-out
> executable improvement at a prespecified precision floor?

The study treats false matches, missed breaks, unsupported explanations, and
unauthorized state changes as distinct outcomes. Aggregate completion cannot
compensate for violating a material control.

## Task contract

Each case provides a consistent or deliberately inconsistent view across a
subset of:

- trade, order, allocation, confirmation, and settlement records
- cash, position, collateral, ledger, and bank records
- reference data, standing instructions, agreement terms, and approvals
- event timestamps, currencies, quantities, prices, fees, and identifiers.

The agent may retrieve evidence, propose matches, classify discrepancies,
identify a root cause, request missing information, escalate an unresolved case,
or prepare a permitted state change. An executable oracle records the accepted
correspondence, discrepancy type, required evidence, permitted actions, and
post-action state.

## Environment coordinates

Candidate distributions vary continuously along measurable properties rather
than relying only on named task buckets:

- usable outcome variation under the starting policy
- admitted signal per generated token
- effective coverage across workflows and discrepancy types
- evidence-retrieval depth and prerequisite coverage
- ambiguity among plausible matches
- lifecycle and source-system diversity
- response, tool-call, and state-transition cost
- control burden, including approval and escalation requirements.

These coordinates are measured on candidate scenarios before training. Held-out
outcomes remain inaccessible to construction.

## Candidate mixtures

The minimum matched comparison contains four candidates:

1. **Source proportional.** Preserve the qualified generator's natural task
   frequencies.
2. **Static difficulty.** Match size while prioritizing cases judged difficult
   without using the starting policy's rollouts.
3. **Policy-relative signal.** Prioritize cases with usable starting-policy
   variation per unit of generated cost.
4. **Signal with coverage.** Optimize policy-relative signal subject to minimum
   representation for every prespecified workflow and discrepancy family.

Candidate size, training budget, trainer, model, tool contract, and scenario
schema remain fixed. An abstention is recorded when predicted differences are
small relative to measurement or training uncertainty.

## Outcome vector

The primary outcome is held-out executable task completion at equal generated
token budget. The study also reports:

- match precision and exception recall by discrepancy family
- false-match and missed-break cost
- root-cause accuracy with required-evidence completeness
- correct approval, abstention, and escalation decisions
- ledger, position, collateral, and cash consistency after tool actions
- unsupported claims and provenance failures
- generated tokens, tool calls, verifier calls, wall time, and measurement cost
- training-seed variation and allocation regret.

Qualification freezes the operating precision floor before any trained-policy
outcome is observed.

## Partition and chronology

Development scenarios validate the generator, tools, oracle, and failure modes.
Candidate scenarios measure the starting policy and construct mixtures. Held-out
scenarios are generated from separate seeds and committed before training.
Where possible, the held-out set also contains unseen combinations of known
discrepancy mechanisms.

The following artifacts are frozen before the first claim-bearing update:

- source and generator revisions
- development, candidate, and held-out commitments
- starting-policy identity and rollout contract
- candidate membership and mixture weights
- measurement definitions and prediction
- training budgets, seeds, checkpoints, and stopping rule
- outcome vector, precision floor, abstention rule, and scoring code.

The held-out partition opens only after every required arm passes identity,
completeness, and infrastructure checks.

## Qualification gates

Construction is admitted only after:

1. two independent oracle executions reach the same valid state
2. null and declared negative controls fail for the intended reasons
3. infrastructure failures remain distinct from financial errors
4. every write is permission-checked and replayable
5. the scorer detects planted false matches, missed breaks, and evidence gaps
6. source revisions, licenses, identities, and hashes are recorded
7. the starting policy produces enough non-degenerate outcomes to compare
   candidate environments.

FINOS Common Domain Model is the leading lifecycle representation candidate.
Business Bench is the current generator-qualified operations source. RecBench,
TradeOpsSim, and FinRCA-Bench inform reconciliation data, harness, and evidence
contracts but are not currently admitted as claim-bearing construction sources.
