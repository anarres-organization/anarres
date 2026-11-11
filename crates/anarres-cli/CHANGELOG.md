# Changelog

All notable CLI changes are recorded here. The project follows semantic
versioning for the command contract and versioned JSON schemas for stored
records.

## 0.4.0 - 2026-11-11

- Add `init`, `inspect`, and `probe` for qualifying native environment sources
  before they become portable Anarres records.
- Support seven released source formats through independently installable
  domain adapters while preserving each study's measurements and gates.
- Add adapter compatibility checks, bounded execution, deterministic source
  records, and clearer errors for missing or incompatible adapters.
- Keep fast routing, validation, hashing, and comparison in the native Rust
  binary while domain runtimes remain with their scientific implementations.
- Clarify the first-run workflow, adapter capabilities, and current evidence
  boundary across the public documentation.

## 0.3.1 - 2026-11-10

- Turn `anarres demo` into a complete two-candidate qualification,
  measurement, comparison, and validation journey.
- End the demo with an exact, runnable command instead of placeholder paths.
- Clarify the input contract, generated artifact location, measurement units,
  and human-readable status fields.

## 0.3.0 - 2026-11-10

- Add TTY-aware semantic color and status symbols to human-readable output.
- Respect `NO_COLOR`, disable styling in pipes, and add `--color` overrides.
- Keep JSON output unstyled and preserve every machine-readable contract.
- Improve command hierarchy, adapter discovery, and actionable error hints.

## 0.2.0 - 2026-11-10

- Add `anarres demo` for a complete first run without a repository checkout or
  domain runtime.
- Group human-readable qualification, measurement, and validation output by
  action while preserving the existing JSON contract.
- Make the first-run workflow repeatable when its generated record is unchanged.

## 0.1.0

- Add `qualify`, `measure`, `design`, and `validate` commands.
- Add grouped policy-probe measurement with Python/Rust digest conformance.
- Add cross-domain environment profiles with qualification, units, uncertainty,
  compatibility checks, and content integrity.
- Add deterministic JSON output and nonzero exits for invalid records and
  incompatible candidate panels.
- Add a versioned external-adapter protocol with local discovery, compatibility
  checks, and literal argument forwarding.
- Add bounded adapter descriptor discovery with timeout and output limits.
- Add generated completions for Bash, Zsh, Fish, and PowerShell.
- Add cross-platform archives, installers, checksums, and a Homebrew formula
  published through the official tap.
- Reserve `anarres-<name>` executables for protocol-conforming adapters and use
  the native `anarres measure` command for environment processing.
