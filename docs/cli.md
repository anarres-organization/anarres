# Anarres CLI

The `anarres` command turns measured evidence into content-addressed environment
records and compares compatible candidates without changing remote state. The
command is a native Rust binary. Model inference, simulators, sandboxes, and
other domain runtimes remain in adapters that emit versioned records.

## Install

Tagged releases provide a native binary without a Python or Rust runtime:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
anarres --version
```

Windows users can run the corresponding PowerShell installer from the latest
release. Every release also includes platform archives, SHA-256 checksums, and
a Homebrew formula. See the [release guide](releases.md) for verification and
supported platforms.

### Install from source

Install Rust with [rustup](https://rustup.rs/), clone this repository, and run:

```bash
cargo install --path crates/anarres-cli --locked
anarres --version
```

For repository development, `cargo run -p anarres-cli --` can replace
`anarres` in the examples below.

### Shell completions

Generate completions from the installed binary so they always match its
command contract:

```bash
# bash
anarres generate-shell-completion bash > ~/.local/share/bash-completion/completions/anarres

# zsh
mkdir -p ~/.zfunc
anarres generate-shell-completion zsh > ~/.zfunc/_anarres

# fish
anarres generate-shell-completion fish > ~/.config/fish/completions/anarres.fish
```

PowerShell users can generate a script with
`anarres generate-shell-completion powershell` and source it from their
profile.

## Five-minute example

The bundled policy-probe fixture runs without a model server or GPU:

```bash
anarres qualify examples/environment-processing/probe.json
mkdir -p .anarres/example
anarres measure examples/environment-processing/probe.json \
  --output .anarres/example/environment.json
anarres validate .anarres/example/environment.json
```

`qualify` separates usable task groups from repair and quarantine cases.
`measure` writes a deterministic record with source, policy, contract,
coordinate, and digest information. `validate` recomputes its integrity checks.
The fixture is synthetic and demonstrates software behavior rather than a
scientific result.

## Commands

| Command | Purpose | Accepted records |
| --- | --- | --- |
| `qualify` | Check whether measured evidence is ready for comparison | Policy-probe input or profile input |
| `measure` | Normalize evidence into a content-addressed record | Policy-probe input or profile input |
| `design` | Compare candidates and audit panel compatibility | Two or more manifests or profiles of one type |
| `validate` | Check structure, semantics, and content integrity | Any supported input or measured record |
| `adapter` | Discover, inspect, and run installed domain adapters | Local adapter executables and descriptors |

Run `anarres <command> --help` for the complete arguments of one command.

### Work with domain adapters

Domain runtimes are installed separately from the native binary. An adapter is
a standalone executable named `anarres-<name>` on `PATH`:

```bash
anarres adapter list
anarres adapter doctor finance
anarres adapter run finance -- status --json
```

The shorter form uses the same generic discovery and compatibility checks:

```bash
anarres finance status --json
```

`adapter list` reports the executable selected for each name and any shadowed
copies later on `PATH`. `adapter doctor` validates the adapter's versioned
descriptor without opening study artifacts. `adapter run` validates that
descriptor and forwards arguments literally without a shell. Built-in commands
always take precedence over adapter names. Descriptor queries must finish in
five seconds and stay below 256 KiB of output, preventing a faulty adapter from
blocking CLI discovery.

The CLI does not download adapters, search a repository checkout, or import an
adapter's libraries. Install domain tools through their documented package or
binary distribution. The
[adapter authoring guide](architecture/adapter-authoring.md) defines the
descriptor and release requirements.

### Qualify task groups

```bash
anarres qualify examples/environment-processing/probe.json
```

For grouped policy probes, qualification checks task identities and probe
fields, then separates admitted, reserve, repair, and quarantine groups.
Infrastructure failures are reported as repair work rather than scientific
reward zero. For cross-domain profiles, the command reports each adapter-owned
qualification check and whether all error-level checks pass.

### Measure an environment

```bash
anarres measure examples/environment-processing/probe.json \
  --output .anarres/example/environment.json
```

The grouped-probe path computes usable signal density and effective task
coverage from one frozen policy probe. A cross-domain profile instead retains
the adapter's own named coordinates. Both output types record their source,
starting subject, measurement contract, provenance, and content digests.

Writes are atomic, and an existing destination is preserved unless `--force`
is supplied. Use `--force` only when intentionally regenerating a derived
record from reviewed input.

### Design a candidate panel

```bash
anarres design .anarres/candidates/*.json
```

`design` audits whether candidates can be interpreted together. Grouped-probe
manifests must share the starting policy and probe contract. Cross-domain
profiles must share the domain, starting subject, producer revision,
measurement contract, and complete coordinate definitions. A changed unit,
estimator, definition revision, or adapter revision makes the panel
incompatible.

The command reports candidate values and observed ranges. It does not infer an
optimal environment or assume that a coordinate direction predicts downstream
utility.

### Validate records

```bash
anarres validate \
  examples/environment-processing/probe.json \
  .anarres/example/environment.json
```

`validate` checks supported record structure, semantic constraints, content
integrity, task identity, status counts, and coordinate ranges. Multiple files
can be checked in one invocation.

## Cross-domain profiles

Some studies do not use grouped binary-reward probes. A robotics study may
measure target relevance, policy weakness, episode coverage, and action cost.
A materials study may measure starting-model residuals, chemical-system
coverage, and reference-label cost. Domain adapters preserve those measurements
without forcing them into $\rho$ and $H$.

```bash
anarres qualify examples/environment-profiles/robotics-a.profile-input.json
anarres measure examples/environment-profiles/robotics-a.profile-input.json \
  --output .anarres/robotics-a.profile.json
anarres measure examples/environment-profiles/robotics-b.profile-input.json \
  --output .anarres/robotics-b.profile.json
anarres design \
  .anarres/robotics-a.profile.json \
  .anarres/robotics-b.profile.json
```

Profiles record the domain, starting subject, adapter revision, measurement
contract, qualification checks, named coordinates, versioned definitions,
units, estimators, uncertainty, and role-labelled artifact references. The
profile is an interoperable projection. The native study record remains the
authority for scientific interpretation.

The [domain integration matrix](domain-support.md) distinguishes schema
conformance, native adapters, and predictive evidence. The [domain adapter
guide](architecture/domain-adapters.md) defines the runtime boundary, and the
[adapter authoring guide](architecture/adapter-authoring.md) documents the
Python construction interface and promotion requirements.

## Example adapter: agentic finance

The finance adapter retains its domain-native Python implementation and is
installed separately from the Rust binary:

```bash
cargo install --path crates/anarres-cli --locked
uv tool install ./packages/finance
anarres adapter doctor finance
```

After installation, the direct generic form exposes its released workflows:

```bash
anarres finance status
anarres finance audit-sources
anarres finance profile --output-dir .anarres/finance
anarres finance score-holdout finharmbench
anarres finance verify
anarres finance reproduce --output-dir .anarres/finance-reproduction
```

`status` reports the released capabilities and current prospective boundary.
`audit-sources` validates immutable source revisions and generator preflight.
`profile` converts the completed starting-policy qualification into a shared
profile input. `score-holdout` reruns one frozen source test from its released
decision contract. `verify` reruns every released finance check in an isolated
copy, and `reproduce` exports the regenerated retrospective, strict-transfer,
and frozen-holdout artifacts without modifying checked-in evidence.

New policy-attempt records use the same native gate:

```bash
anarres finance qualify-policy qualification-attempts.jsonl \
  --output qualification-summary.json
```

The native CLI resolves `anarres-finance` through the same protocol used by
every other domain. Finance dependencies remain isolated from the Rust core,
and no finance command performs a network call.

The installed adapter can also be invoked directly. When the current directory
is not a repository checkout, pass the evidence location explicitly:

```bash
anarres-finance status --repository /path/to/anarres --json
anarres-finance audit-sources --repository /path/to/anarres --json
```

The generic and direct forms execute the same native finance command. The
repository path supplies released evidence. The installed adapter contains no
fallback copy of study artifacts.

## Automation

Terminal output is intended for people. Add `--json` for deterministic,
machine-readable output:

```bash
anarres qualify examples/environment-processing/probe.json --json
anarres design .anarres/candidates/*.json --json
```

Structured data is written to standard output. Errors are written to standard
error. Successful commands exit with status 0; invalid input, incompatible
candidate panels, failed validation, and write failures exit nonzero. The CLI
built-ins perform no network calls and send no telemetry. Installed adapters
retain their own documented runtime and network contract.

## Record contracts

Grouped probes use:

- [`probe-input.v1`](../schemas/environments/probe-input.v1.schema.json)
- [`environment-manifest.v1`](../schemas/environments/environment-manifest.v1.schema.json)

Cross-domain profiles use:

- [`environment-profile-input.v1`](../schemas/environments/environment-profile-input.v1.schema.json)
- [`environment-profile.v1`](../schemas/environments/environment-profile.v1.schema.json)

Installed adapters describe their compatibility with:

- [`adapter-descriptor.v1`](../schemas/adapters/adapter-descriptor.v1.schema.json)

Unknown fields and unsupported schema versions are rejected. A change in
meaning, unit, or estimator requires a new coordinate definition revision
rather than a silent reinterpretation of an existing field.

## Troubleshooting

**The output file already exists.** Inspect or validate the existing record.
Pass `--force` only when replacement is intended.

**`design` reports incompatible candidates.** Run `anarres validate` on every
record, then compare the compatibility fields reported by `design --json`.
Candidates from different subjects, contracts, producer revisions, or
coordinate definitions belong in separate panels.

**A profile is valid but not ready.** Structural validity and scientific
readiness are separate. Inspect the error-level qualification checks with
`anarres qualify <profile-input> --json` and repair the native evidence rather
than editing the measured profile.

**A runtime failure appears as reward zero.** Stop the adapter workflow. Native
adapters must preserve infrastructure, verifier, missingness, and invalid-data
states instead of converting them into ordinary unsuccessful outcomes.
