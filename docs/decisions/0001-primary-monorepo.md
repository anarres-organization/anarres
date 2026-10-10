# ADR 0001: Begin with one primary monorepo

- Status: accepted
- Date: 2026-10-09

## Context

Anarres contains coordinated research across several domains that shares schemas, environment processing, and evaluation. Premature repository separation would duplicate those contracts and make cross-domain changes harder to review.

## Decision

Shared packages, data systems, and domain-organized experiments remain in the primary `anarres` repository. Large datasets and models remain in external versioned stores. Components may be extracted later when they develop an independent release, governance, security, or contributor boundary.

## Consequences

Shared changes receive one atomic review and one integration test surface. Packages, data systems, and experiments still maintain explicit ownership and dependency boundaries. The repository must resist accidental coupling through schemas, tests, and dependency checks rather than through separate Git repositories.
