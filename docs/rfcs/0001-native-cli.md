# RFC 0001: Native CLI with scientific adapters

- Status: accepted
- Date: 2026-11-09

## Context

Anarres processes environment records across language-model training, robotics,
cyber, and scientific machine learning. Local commands should start quickly,
install without a language runtime, and remain responsive while validating
manifests, hashing records, and comparing candidate panels. Domain integrations
also depend on Python libraries for model inference, simulation, and scientific
computing.

A Python-only command layer would simplify the first implementation but make
every local operation depend on Python startup and packaging. Reimplementing
domain adapters in a systems language would separate Anarres from the ecosystems
that produce the records it measures.

## Decision

The `anarres` command is a Rust binary. It owns command routing, deterministic
serialization, content hashing, contract validation, candidate-panel audits,
and human-readable or machine-readable output.

Domain adapters remain independent producers of versioned Anarres records.
Python remains the primary adapter language while scientific interfaces are
evolving. The boundary between the native CLI and an adapter is a versioned
record rather than an in-process Python call.

The first CLI supports four workflow verbs:

- `qualify` classifies task groups without turning infrastructure failure into
  scientific reward zero
- `measure` creates a content-addressed environment manifest from a frozen
  policy probe
- `design` audits the compatibility and measured span of a candidate panel
- `validate` checks supported records and manifest integrity

Observability is part of each command rather than a separate remote service.
Commands provide concise terminal output by default and deterministic JSON with
`--json`. Records include contract fields and content digests so a result can be
traced to the policy probe that produced it.

The existing Python environment processor remains available during migration.
Cross-language conformance tests cover every scientific calculation implemented
in both languages.

## Consequences

Users receive one fast binary for local and continuous-integration workflows.
Adapters can continue to use PyTorch, LeRobot, NeMo, chemistry libraries, and
other domain runtimes without becoming CLI dependencies. Stable hot paths may
move into a shared Rust library after profiling, while experimental coordinates
remain in domain adapters until their contracts are accepted.

The repository must maintain release builds for supported operating systems and
architectures. A native measurement cannot replace a reference implementation
without conformance tests and an explicit contract update.
