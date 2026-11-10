# Authoring a domain adapter

A domain adapter translates an established measurement record into an Anarres
environment-profile input. It does not reproduce the study in a new framework,
infer missing measurements from downstream outcomes, or rename unlike outcomes
until they appear comparable.

## Ownership boundary

The domain study owns:

- the scientific estimand and measurement procedure
- qualification and missingness rules
- coordinate definitions, units, and estimators
- native task, episode, structure, or trajectory identities
- uncertainty and abstention semantics

The adapter owns:

- reading one pinned native record
- mapping released measurements to versioned coordinate definitions
- preserving failed, unknown, and invalid states
- linking the native evidence by URI, digest, media type, and license
- emitting a deterministic profile input

The native CLI independently validates the resulting record. It owns neither
the domain formula nor the scientific interpretation.

## Executable contract

A maintained command-line adapter installs an executable named
`anarres-<name>`. It must answer the descriptor query without opening native
study artifacts or performing network access:

```bash
anarres-robotics --anarres-adapter-descriptor
```

The response follows
[`anarres.adapter-descriptor.v1`](../../schemas/adapters/adapter-descriptor.v1.schema.json)
and declares the adapter name and version, protocol version, domain, executable,
supported profile schemas, capabilities, and measurement contracts. Lists are
sorted and contain no duplicates. The descriptor's executable and name must
match the installed filename.

The descriptor query is part of discovery rather than the scientific workflow.
It must return within five seconds, write no more than 256 KiB across either
output stream, avoid network access, and leave study artifacts unopened.

Users can inspect an installation before running a workflow:

```bash
anarres adapter doctor robotics
anarres robotics --help
```

Adapters write structured results to standard output, diagnostics to standard
error, and return nonzero for invalid inputs or incomplete workflows. They must
accept literal forwarded arguments and must not rely on the caller's current
working directory. Large runtimes and scientific dependencies remain in the
adapter package rather than the Rust core.

## Python interface

The `anarres-environments` package provides small construction helpers:

```python
from pathlib import Path

from anarres.environments import (
    build_profile_input,
    coordinate,
    local_artifact,
    qualification_check,
    write_profile_input,
)

native = Path("measurements.json")
profile = build_profile_input(
    environment_id="candidate-a",
    domain="robotics",
    subject={"kind": "policy", "id": "policy-a", "revision": "weights-sha256"},
    producer={"kind": "adapter", "id": "robotics.episode-probe", "revision": "1"},
    source={"uri": "hf://datasets/example", "revision": "commit", "license": "license-id"},
    measurement_contract={
        "kind": "episode-probe",
        "id": "robotics.episode-probe.v1",
        "revision": "1",
        "repetitions": 3,
        "cost_unit": "action_steps",
    },
    qualification_checks=[qualification_check(...)],
    coordinates=[coordinate(...)],
    artifacts=[
        local_artifact(
            role="native-measurements",
            path=native,
            uri="release://measurements.json",
            media_type="application/json",
            license_id="license-id",
        )
    ],
)
write_profile_input(Path("candidate-a.profile-input.json"), profile)
```

The helpers hash native artifacts, require measured coordinates and
qualification evidence, serialize deterministically, and refuse to overwrite
an existing record unless explicitly requested. They deliberately do not
calculate domain measurements. The adapter should import the study's existing
measurement functions or consume its released outputs.

## Conformance workflow

An adapter is ready when the following workflow passes:

```bash
anarres qualify candidate-a.profile-input.json
anarres measure candidate-a.profile-input.json --output candidate-a.profile.json
anarres validate candidate-a.profile-input.json candidate-a.profile.json
```

Two or more candidates can be compared with `anarres design` only when their
domain, starting subject, adapter revision, measurement contract, and complete
coordinate definitions match.

An adapter test should also verify:

1. exact native artifact digests
2. stable output for the same native bytes
3. rejection of absent measurements and missing source revisions
4. preservation of infrastructure and verifier failures
5. preservation of units, estimators, sample counts, and uncertainty
6. incompatibility after a coordinate definition or adapter revision changes
7. descriptor conformance and protocol compatibility
8. installation and execution outside a repository checkout
9. deterministic structured output and nonzero error propagation

## Promotion policy

Experiment-specific adapters remain beside their study while their interface is
changing. Promotion into a maintained package requires two real producers, an
independent consumer, conformance tests, and a documented migration policy.
Changing a coordinate's meaning, unit, or estimator creates a new definition
revision. It never silently changes an existing profile.

The SylloGym release now includes its complete outcome-blind component
measurements and frozen candidate weights. Its study-local adapter projects
those native records into three compatible profiles without reading downstream
outcomes. The prospective PushT release still omits complete per-candidate
pre-training vectors and remains an authoritative evidence record rather than a
profile producer. The prospective Can v1.4.1 study publishes a separate
pre-outcome candidate-measurement record and native adapter because its complete
vectors and frozen identities are available.
