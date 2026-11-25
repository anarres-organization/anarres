# Contributing to Anarres

Anarres welcomes contributions to data systems, reusable packages, evaluation, documentation, and scientific experiments.

## Find the right workstream

The [workstream registry](WORKSTREAMS.md) maps each research program and shared
software component to its repository path, GitHub issue queue, and Discord
channel. Search the relevant issue queue before proposing work.

GitHub is the record for scope, assignments, decisions, and status. Discord is
for questions and short-lived coordination. If a Discord discussion produces a
decision or a task, record it on the relevant issue.

A bounded project may require several independently assignable issues. Create
one parent issue for the project and attach those tasks as sub-issues. Apply the
same `area:*` label to the parent and its sub-issues. Use a milestone only when
the work shares a time-bounded release or experimental freeze.

## Before writing code

1. Read the root `AGENTS.md` and any nearer instructions.
2. Search existing issues and the relevant data or experiment documentation.
3. Comment on an existing issue before beginning substantial work. If no issue
   exists, open one in the relevant workstream.
4. For a shared schema, breaking interface, or new maintained package, open an RFC before a large implementation.
5. For ordinary fixes, documentation, adapters, and experiment-local analysis, open a normal pull request.

## Local development

```bash
make setup
make check
make study-check
make example
```

The native CLI requires a Rust toolchain with `rustfmt` and `clippy`. Python
adapters require Python 3.11 or newer and `uv`. The default checks are CPU-only.
GPU, sandbox, and full-domain integration tests run separately in trusted
environments.

`make check` covers maintained software interfaces and schemas.
`make study-check` reproduces compact claim-bearing records and fails when a
reproducer changes tracked artifacts. Use `make study-check-extended` before a
release that changes an exhaustive study workflow.

Changes to routing, validation, serialization, adapter dispatch, or startup
behavior should also run `make benchmark` against a release build. The
[performance guide](docs/performance.md) describes the workloads and how to
interpret results across machines.

## Pull requests

A pull request should explain:

- What behavior changes
- Why the change belongs in its selected layer
- Which tests were run
- Whether schemas or stored artifacts change
- Whether scientific conclusions are affected
- Any checks that could not be run locally

Credentials, machine-specific paths, transient logs, and large generated artifacts must not be committed. Released experiments should include compact evidence, immutable identifiers, and scripts that reproduce their reported analyses.

## Adding a source or environment

New sources must record their upstream revision, license, stable task identities, transformation history, and contamination status. Executable tasks additionally require oracle, no-op, verifier-stability, and infrastructure checks before policy failures can be interpreted scientifically.

## Review

Research maintainers review scientific direction. Component maintainers review implementation in shared packages and data systems. Contract maintainers review shared schemas and compatibility changes. A single person may initially fill more than one role, but the decision rights remain distinct.
