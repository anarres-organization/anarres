# Changelog

All notable CLI changes are recorded here. The project follows semantic
versioning for the command contract and versioned JSON schemas for stored
records.

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
