# RFC 0002: Cross-domain environment profiles

- Status: accepted
- Date: 2026-11-09

## Context

The grouped policy-probe contract measures usable advantage density and effective
coverage for reinforcement learning. Those coordinates can apply when a native
protocol uses repeated policy attempts and group-relative updates. They do not
describe every Anarres study. A materials environment may be characterized by
starting-model residuals, chemical coverage, and labeling cost, while a robot
dataset may require target relevance, episode coverage, correction quality, and
action cost.

A universal record should preserve these measurements without implying that
their values are interchangeable or that one coordinate system applies to every
training method.

## Decision

Anarres defines a versioned environment-profile input and a content-addressed
environment profile. A profile records:

- the environment, domain, starting subject, and source revision
- the adapter identity and implementation revision
- the exact measurement contract and repetition count
- structured qualification checks with error or warning severity
- named coordinates with roles, units, direction, estimator, and sample count
- a versioned definition for every coordinate
- optional uncertainty intervals and artifact references
- content digests for the input and normalized profile

Coordinate names are domain-defined. Comparison requires matching coordinate
definitions, starting subjects, and measurement contracts. The core CLI reports
ranges and incompatibilities but does not infer that a larger value is better or
select an environment without a separately validated decision rule.

Domain adapters produce profile inputs in their native ecosystem. The Rust CLI
validates and normalizes those records. This keeps LeRobot, Gymnasium, Harbor,
ASE, molecular simulation, and other domain dependencies outside the core
binary.

A profile is a typed projection, not a replacement for the domain study. It can
link native measurements, qualification reports, and decision records by role,
URI, and content digest. The originating protocol and analysis remain
authoritative for scientific interpretation.

## Consequences

The grouped RL probe remains the preferred contract when its assumptions hold.
Cross-domain profiles provide a common operational envelope rather than a
universal scientific representation. Predictors must declare which coordinate
definitions and measurement contracts they accept.

New coordinate definitions should use stable names and standard units where
available. A changed estimator, unit, or meaning receives a new definition
revision. The CLI rejects mixed revisions within one candidate panel, so domain
conventions can evolve without changing the Rust core. A profile cannot turn a
failed error-level qualification check into a valid scientific observation.
Domain-specific raw data remain in referenced artifacts rather than being copied
into the profile.

Namespaced coordinate roles follow the extensibility pattern used by
OpenLineage custom facets. Shared roles remain small, while domains can add
producer-owned semantics without claiming that those fields belong in every
study. OpenTelemetry's stability model similarly motivates separate convention
revisions when meanings change rather than silent reinterpretation of existing
records.
