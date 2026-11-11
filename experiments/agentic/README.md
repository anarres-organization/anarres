# Agentic systems

This directory connects Anarres studies that involve terminals, tools, or
multi-step execution. It is an overview, not a separate `anarres agentic`
adapter. Each domain keeps its own task format, verifier, cost model, and
qualification gates.

## Research questions

1. Which policy-relative coordinates transfer from mathematical RL to executable environments?
2. Which additional measurements are needed to distinguish task validity, learnability, cost, and target relevance?
3. Can measurements made before RL predict held-out terminal utility curves and finite-budget environment rankings?
4. Do improvements on a controlled, disjoint panel transfer to external benchmarks such as Terminal-Bench?

## Shared experimental contract

Agentic studies keep four layers separate:

- **Fixture validity:** an oracle succeeds, a no-op fails, and verifier behavior is stable.
- **Infrastructure validity:** sandbox and harness failures are recorded separately from scientific reward zero.
- **Policy measurement:** repeated rollouts measure the quantities defined by
  that study, such as success variation, cost, reliability, or candidate
  overlap.
- **Held-out evaluation:** trained checkpoints are compared with a common warm start on disjoint tasks at matched generated-token budgets.

Released studies use versioned task identities, content hashes, explicit
failure states, and disjoint evaluation records. The concrete entry points are:

- [formal verification](../cyber/formal-verification/README.md)
- [vulnerability exploitation](../cyber/qualification/README.md)
- [robotics](../robotics/README.md)
- [legal workflows](../legal/README.md)
- [finance workflows](../finance/README.md)

The shared contract makes results comparable without forcing every domain into
one measurement model.
