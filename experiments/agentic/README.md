# Agentic systems

The agentic program extends environment-utility measurement to terminal, coding, and tool-using tasks. These settings add long trajectories, heterogeneous verifiers, sandbox startup and execution failures, and stronger interactions between the policy and the experience it generates.

## Research questions

1. Which policy-relative coordinates transfer from mathematical RL to executable environments?
2. Which additional measurements are needed to distinguish task validity, learnability, cost, and target relevance?
3. Can measurements made before RL predict held-out terminal utility curves and finite-budget environment rankings?
4. Do improvements on a controlled, disjoint panel transfer to external benchmarks such as Terminal-Bench?

## Experimental contract

Agentic studies keep four layers separate:

- **Fixture validity:** an oracle succeeds, a no-op fails, and verifier behavior is stable.
- **Infrastructure validity:** sandbox and harness failures are recorded separately from scientific reward zero.
- **Policy measurement:** repeated rollout groups estimate signal density, coverage, cost, reliability, and candidate overlap.
- **Held-out evaluation:** trained checkpoints are compared with a common warm start on disjoint tasks at matched generated-token budgets.

Released adapters and analyses will use the same versioned task identities, content hashes, failure taxonomy, and evaluation primitives as the rest of Anarres. This directory will accumulate the reproducible components as the agentic study matures.
