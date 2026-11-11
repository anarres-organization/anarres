# RFC 0006: Native environment source manifests

- Status: accepted
- Date: 2026-11-11

## Context

Anarres supports domains whose native environment objects are intentionally
different. An agentic environment may be an OpenEnv package or Harbor task. A
robotics candidate may be an HDF5 demonstration dataset plus simulator and
policy contracts. Legal, molecular, materials, finance, and formal-verification
studies each retain other native sources, verifiers, units, and failure states.

Users need one obvious entry point without converting these objects into a
lowest-common-denominator task table. They also need to know which adapter will
open a source, what format it expects, and what will be produced before any
model or simulator work begins.

## Decision

A native environment may contain an `anarres.toml` manifest following
`anarres.environment-source.v1`. The manifest contains only:

- a stable environment identifier
- the scientific domain
- the adapter name
- the required adapter version
- the adapter's native-format identifier
- the native source URI, immutable revision, and license

Paths are relative to the manifest. Remote schemes remain adapter-owned. The
manifest contains no credentials, policy endpoints, downstream outcomes,
candidate scores, or unrestricted adapter options.

The native files remain authoritative and unchanged. For example:

| Native format | Authoritative object |
| --- | --- |
| `openenv` | OpenEnv package and `openenv.yaml` |
| `harbor-task` | Harbor task directory, `task.toml`, environment, and verifier |
| `gymnasium` | Registered environment or package plus its `EnvSpec` |
| `robomimic-hdf5` | Dataset, masks, simulator, and policy contract |
| domain-specific format | Versioned source described by that domain's adapter |

Adapters declare accepted `source_formats` and the capabilities
`source-qualification` and `policy-probe` in their existing descriptor. An
adapter does not declare either capability until a real native source passes
its conformance tests.

The unified flow is:

```text
anarres init <environment-directory> \
  --adapter <name> --revision <immutable-revision> --license <license>
anarres inspect <environment-or-anarres.toml>
anarres qualify <environment-or-anarres.toml>
anarres probe <environment-or-anarres.toml> \
  --policy <identity> --policy-revision <immutable-revision> \
  --output <measurement>
anarres measure <measurement> --output <environment-record>
anarres design <environment-record> <alternative-record>
```

`inspect` validates the envelope and reports adapter installation, source
format support, and available operations without executing the environment.
`qualify` dispatches `qualify-source` to the named adapter. `probe` dispatches
`probe-source` and requires an explicit starting-policy identity and immutable
revision. The adapter writes either the shared probe-run interchange or its
documented domain-native profile input. The native Rust core performs common
validation, aggregation, hashing, and comparison afterward.

CLI flags specify execution choices and override no scientific identity in the
manifest. Adapter-specific arguments may be passed after `--`, remain visible
in help and logs, and must be captured in the emitted measurement contract.

## Consequences

The source manifest gives every domain the same discoverable entry point while
preserving the files and concepts practitioners already use. It also prevents
silent format detection: an HDF5 file, task directory, or remote dataset is
never guessed into the wrong adapter.

Adding support for a native format normally changes one adapter and its tests,
not the Rust measurement model. A new universal field requires a schema review;
a domain-specific setting belongs in the native source or a versioned adapter
contract. Source revisions are mandatory so repeated qualification cannot
silently open different data.

This RFC standardizes dispatch and provenance. It does not claim that every
released evidence adapter can execute raw environments, nor that measurements
from one domain predict utility in another.
