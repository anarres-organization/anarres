# Governance

Anarres uses lightweight, path-based ownership.

## Roles

### Research maintainers

Research maintainers own an experimental domain's priorities, roadmap, and coordination. They do not receive automatic authority over shared packages used by that domain.

### Component maintainers

Component maintainers review implementation changes within a package or data system and maintain its documented behavior, tests, and compatibility.

### Contract maintainers

Contract maintainers review shared schemas, compatibility guarantees, and organization-wide scientific invariants.

## Decisions

Routine changes are resolved through pull-request review by the relevant owners. An RFC is required when a proposal changes a shared schema, breaks a public interface, introduces a maintained package, or changes an organization-wide scientific invariant.

The default decision process is evidence-seeking consensus. When consensus is not reached, the relevant component or contract maintainers document the decision and its rationale. Decisions can be revisited when new evidence appears.

## Maintainer growth

Maintainers are added through demonstrated contributions, reliable review, and sustained responsibility for the affected area. Ownership should expand before reviewer load becomes a bottleneck.

## Research integrity

No maintainer may override a frozen prospective protocol after viewing its outcomes. Corrections create a new version with a recorded relationship to the superseded artifact.
