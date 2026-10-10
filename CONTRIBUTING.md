# Contributing to Anarres

Anarres welcomes contributions to data systems, reusable packages, evaluation, documentation, and scientific experiments.

## Before writing code

1. Read the root `AGENTS.md` and any nearer instructions.
2. Search existing issues and the relevant data or experiment documentation.
3. For a shared schema, breaking interface, or new maintained package, open an RFC before a large implementation.
4. For ordinary fixes, documentation, adapters, and experiment-local analysis, open a normal pull request.

## Local development

```bash
make setup
make check
make example
```

The default checks are CPU-only. GPU, sandbox, and full-domain integration tests run separately in trusted environments.

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
