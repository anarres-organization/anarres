# Domain adapters

Anarres separates domain runtimes from the native CLI. An adapter reads a
domain's established records, performs domain-specific checks, and writes a
versioned environment-profile input. The CLI validates and normalizes that
input without importing the runtime that produced it.

```text
native dataset or runtime
    → domain adapter
    → environment-profile input
    → anarres qualify / measure
    → content-addressed environment profile
    → compatible candidate panel
```

This boundary follows the receiver, processor, and exporter structure used by
OpenTelemetry. It also keeps Anarres compatible with tools that already own
large artifacts, including episode stores, agent sandboxes, molecular
simulators, and atomistic datasets. Profiles reference those artifacts by URI
and digest instead of copying them into the repository.

## Adapter contract

Every adapter must preserve:

1. a stable environment identifier and source revision
2. the starting model, policy, or scientific model being measured
3. the adapter identity and implementation revision
4. the exact measurement contract and number of repetitions
5. infrastructure, verifier, source, and measurement checks
6. coordinates with explicit roles, units, estimators, and sample counts
7. the domain's realized cost unit

Every coordinate references a versioned definition. Profiles can also link the
native measurements, qualification report, decision record, or other evidence
by role, URI, and digest. These links preserve the originating study as the
authoritative scientific record.

An error-level check must pass before a profile is ready for comparison.
Warnings remain visible without changing the underlying measurement. Adapters
must never convert a runtime failure, missing label, or invalid verifier result
into an ordinary failure.

The scientific protocol is a JSON record, and the runtime boundary is a
standalone executable rather than a dynamically loaded library. Installed
adapters use the name `anarres-<name>` and publish a side-effect-free versioned
descriptor. This keeps the native binary small, allows adapters to use the best
language and libraries for their domain, and provides a stable boundary for
containers and workflow systems.

```bash
anarres adapter list
anarres adapter doctor robotics
anarres adapter run robotics -- profile --output-dir profiles
```

The shorter `anarres robotics ...` form uses the same generic discovery path.
The CLI resolves an exact executable on `PATH` and forwards a versioned runtime
handshake plus the domain arguments without a shell. The adapter validates the
protocol and identity before opening study artifacts. `adapter doctor` performs
the full descriptor audit. This single-launch path avoids paying adapter startup
twice for routine commands. The CLI does not download adapters or search a
repository checkout implicitly.

Adding a domain measurement does not require changing the Rust binary. An
adapter publishes a measurement convention, emits the coordinate with that
definition revision, and retains its domain-specific implementation. The core
changes only when the shared operational envelope changes.

## Domain guidance

### Reasoning, legal, finance, coding, and cyber

Repeated policy attempts should retain task and sample identifiers, verifier
outcomes, tool or sandbox validity, generated-token or wall-clock cost, and the
policy revision. The grouped-probe contract is preferred when binary rewards
and repeated attempts make admitted advantage density and effective coverage
well-defined. Executable domains should retain oracle and no-op checks as
qualification evidence.

### Robotics

Robotics adapters should preserve episode and task identities, policy revision,
success or continuous return, action-step or wall-clock cost, and sensor or
runtime validity. Natural termination and external truncation remain separate,
matching Gymnasium's step contract. LeRobot datasets should be referenced by
repository revision and retain their episode, task, feature, and metadata
structure rather than being flattened into independent frames.

### Molecular design

Molecular adapters should retain molecule or reaction identity, target and
oracle revision, chemical validity, simulator or docking failures, action or
route cost, and scaffold or target coverage. Invalid chemistry and failed
infrastructure remain qualification outcomes rather than low rewards.

### Materials science

Materials adapters should retain structure, composition, trajectory, target
property, and starting-model revision. Useful coordinates can include force or
energy residuals, uncertainty, chemical-system coverage, and reference-label or
simulation cost. Atomistic records should keep units explicit and reference the
native structure or trajectory artifact.

## Comparison rules

`anarres design` compares profiles only when their domain, starting subject,
adapter revision, measurement contract, and coordinate definitions match.
Coordinate definitions include the versioned definition, name, role, unit,
direction, and estimator. The command reports ranges and incompatibilities. It
does not rank unlike domains or infer that a coordinate direction is a validated
utility rule.

The schemas are
[`environment-profile-input.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/environments/environment-profile-input.v1.schema.json)
and
[`environment-profile.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/environments/environment-profile.v1.schema.json).
Synthetic cross-domain fixtures live in
[`examples/environment-profiles`](https://github.com/anarres-organization/anarres/tree/main/examples/environment-profiles).
The [adapter authoring guide](adapter-authoring.md) documents the Python
construction interface, conformance workflow, and promotion policy.
The [external adapter RFC](../rfcs/0003-external-adapter-protocol.md) defines
discovery, compatibility, and execution.
The [scientific preservation guide](scientific-preservation.md) explains how
profiles relate to the legal and robotics releases.

## Compatibility references

- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)
  motivate versioned meanings, units, and stability levels for measurements.
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/) keeps run metadata
  separate from large native artifacts, which profiles follow through typed
  artifact references.
- [DVC pipelines](https://dvc.org/doc/user-guide/pipelines/defining-pipelines)
  treat tools as producers of declared outputs without assuming how each stage
  performs its work.
- [LeRobotDataset](https://huggingface.co/docs/lerobot/main/api/datasets)
  defines episode-aware data, task metadata, features, and revisions.
- [Gymnasium Env](https://gymnasium.farama.org/api/env/) separates natural
  termination from external truncation.
- [ASE Atoms](https://ase-lib.org/ase/atoms.html) and
  [calculators](https://ase-lib.org/ase/calculators/calculators.html) define
  common atomistic structures, energies, forces, stress, and units.
- [OpenTelemetry Collector configuration](https://opentelemetry.io/docs/collector/configuration/)
  provides the receiver, processor, and exporter architecture used as the
  adapter model.
- [OpenLineage facets](https://openlineage.io/docs/spec/facets/)
  provide the precedent for a small common envelope with project-prefixed
  extensions that preserve producer-specific metadata without name collisions.
