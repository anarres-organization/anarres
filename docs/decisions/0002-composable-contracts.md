# ADR 0002: Use composable research contracts

- Status: accepted
- Date: 2026-10-09

## Context

Environment processing is important to Anarres, but not every experiment uses the same environment or runtime. Requiring every domain to implement one fixed pipeline would make unrelated work inherit unnecessary concepts.

## Decision

All experiments use shared identity, artifact, and provenance contracts. Environment, training, evaluation, simulator, and safety contracts are composed only when the experiment requires them.

## Consequences

Cross-domain evidence remains comparable without defining Anarres solely as an environment-processing framework. Schema dependencies must remain explicit and versioned.
