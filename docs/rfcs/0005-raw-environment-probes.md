# RFC 0005: Raw environment probes and native attempt aggregation

- Status: accepted
- Date: 2026-11-10

## Context

The first native workflow accepted grouped measurements after a policy probe
had already calculated admitted advantage mass. That boundary made the record
format reproducible, but it left the most important integration step outside
the product: a user could not point a domain runtime at an environment, run a
starting policy, and hand the resulting attempts to the native CLI without
writing custom aggregation code.

Environment execution is not uniform. OpenEnv exposes `reset`, `step`, and
`state` over isolated services. Harbor tasks carry executable environments and
verifiers. Gymnasium environments distinguish termination from truncation.
Robotics, legal, molecular, and materials studies use still different task,
cost, and validity contracts. Moving those runtimes into one Rust binary would
erase scientific distinctions and import large, fast-changing dependencies.

## Decision

Anarres separates environment execution from attempt aggregation.

An environment adapter owns:

- reading and validating its native environment
- checking fixtures, rewards, oracle behavior, and no-op behavior
- executing the specified starting policy under a pinned runtime contract
- preserving native termination, truncation, verifier, and infrastructure
  outcomes
- writing a probe-run directory

The probe-run directory contains `probe.json` and `attempts.jsonl`.
`probe.json` identifies the environment, starting policy, source, sampling
contract, and advantage estimator. Each JSONL row records one stable task and
sample identity, reward or missing reward, loss-admission decision, generated
action tokens, oracle result, no-op result, and infrastructure validity.

The Rust CLI owns:

- streaming and validating the attempt rows
- rejecting duplicate or incomplete groups
- keeping infrastructure failures distinct from scientific reward zero
- deriving unnormalized leave-one-out admitted advantage mass when explicitly
  declared by the probe contract
- calculating portable coordinates and content digests
- comparing only candidates with matching starting-policy and probe contracts

The initial interchange uses JSONL because it can be emitted incrementally by
model servers, simulators, and executable-task harnesses without a shared
language runtime. Rows may arrive in any order. The native reader validates and
hashes them canonically by task and sample identity, so concurrent completion
order does not change the record identity. It retains state proportional to
task count, not the size of the serialized stream. Parquet remains an
adapter-side option for large native artifacts; promotion into the core
requires a benchmark showing that its dependency and binary-size cost improves
a real workflow.

The environment-facing workflow is:

```text
anarres <adapter> qualify <environment>
anarres <adapter> probe <environment> --policy <policy> --output <probe-run>
anarres qualify <probe-run>
anarres measure <probe-run> --output <environment-record>
anarres design <environment-record> <alternative-record>
```

An adapter is not described as supporting raw environments until its
qualification and probe commands pass conformance tests on a real native
environment. Existing study adapters that only reproduce released evidence do
not acquire this capability by declaration.

## Consequences

The native hot path becomes fast and portable without claiming that one
measurement model covers every domain. Runtime adapters can evolve with
OpenEnv, Harbor, Gymnasium, model servers, or study-specific systems while
emitting one bounded interchange. Domain-native profiles remain available when
leave-one-out signal density and effective coverage are not the scientific
estimands.

The first release of this contract provides native ingestion and derivation,
not a universal environment runner. Each supported runtime still needs an
adapter that qualifies the raw source and emits the probe run. Missing rewards,
incomplete groups, and infrastructure-invalid attempts remain visible and
cannot be converted to ordinary failures.
