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
```

Restart your shell if the installer updates `PATH`, then verify the installation:

```bash
anarres --version
```

Homebrew users can install the same release from the official tap:

```bash
brew install anarres-organization/tap/anarres
```

The installer can be inspected before execution:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | less
```

Windows users can run the corresponding PowerShell installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.ps1 | iex"
```

Every release also includes platform archives, SHA-256 checksums, a Homebrew
formula, and build attestations. See the [release guide](releases.md) for
verification, pinned versions, and supported platforms.

### Install from source

Install Rust with [rustup](https://rustup.rs/), then run:

```bash
git clone https://github.com/anarres-organization/anarres.git
cd anarres
cargo install --path crates/anarres-cli --locked
anarres --version
```

For repository development, `cargo run -p anarres-cli --` can replace
`anarres` in the examples below.

### Shell completions

Generate completions from the installed binary so they always match its
command contract. Add the command for your shell, then restart it:

```bash
# bash
echo 'eval "$(anarres generate-shell-completion bash)"' >> ~/.bashrc

# zsh
echo 'eval "$(anarres generate-shell-completion zsh)"' >> ~/.zshrc

# fish
mkdir -p ~/.config/fish/completions
anarres generate-shell-completion fish > ~/.config/fish/completions/anarres.fish
```

PowerShell and Elvish users can generate scripts with
`anarres generate-shell-completion powershell` or
`anarres generate-shell-completion elvish` and source them from their profiles.

## First run

Run the complete bundled workflow without cloning the repository:

```bash
anarres demo
```

The command qualifies a fixed policy probe, measures its usable experience,
writes two candidate records, compares them under one starting policy, and
validates both content digests. It ends with a runnable `anarres design`
command containing the exact generated paths. Use `--output <path>` and
`--comparison-output <path>` to choose other destinations.

Generated records live in the project-local `.anarres/` directory, which is
ignored by Git and safe to regenerate. Running the demo from your home
directory writes to `~/.anarres`; run it from a project directory when you want
the artifacts to stay with that project.

Human-readable output uses restrained status color when standard output is a
terminal. Styling is disabled automatically for pipes and respects `NO_COLOR`.
Use `--color always` or `--color never` to override detection. Machine-readable
`--json` output never contains terminal styling.

## What you bring

Anarres compares candidate sources of training experience for a specified
starting policy or system. A candidate may contain prompts, executable tasks,
proof obligations, robot episodes, legal matters, molecular structures,
materials configurations, or another domain-defined unit.

Use the built-in policy-probe contract when you can provide:

1. stable candidate, task, and starting-policy identifiers
2. a fixed sampling and measurement contract
3. repeated attempts grouped by task
4. outcomes, generated cost, and the signal admitted by training
5. oracle, no-op, and infrastructure-validity results

Use a domain adapter when the study requires different native measurements.
Adapters preserve those coordinates, units, uncertainty, costs, provenance,
and failure states inside a portable profile rather than converting every
domain to one universal score. Candidate records can be compared only when the
starting subject and measurement contract match.

Start with `anarres qualify --help` for the built-in contract, or run
`anarres adapter list` to discover installed domain workflows. Reference inputs
live in `examples/environment-processing/` and `examples/environment-profiles/`.

## Run the core commands directly

The bundled policy-probe fixture runs without a model server or GPU. Clone the
repository to obtain the fixture if it is not already present:

```bash
git clone --depth 1 https://github.com/anarres-organization/anarres.git
cd anarres
anarres qualify examples/environment-processing/probe.json
mkdir -p .anarres/example
anarres measure examples/environment-processing/probe.json \
  --output .anarres/example/environment.json
anarres validate .anarres/example/environment.json
```

`qualify` separates usable task groups from repair and quarantine cases.
`measure` writes a deterministic record with source, policy, contract,
coordinate, and digest information. `validate` recomputes its integrity checks.

### Read the result

The default output is a short report for a person at the terminal. In the
bundled fixture, `qualify` reports two admitted groups, one reserve group, one
repair, and one quarantine. It names the two groups that require action.
`measure` then reports:

```text
  ✓ Measured     math-reference-demo-v1
    Policy             synthetic-policy-v1
    Signal density     833.3333 advantage mass / million generated tokens
    Effective coverage 0.6533 (0 to 1)
    Evidence           3 eligible task groups, 4,200 generated tokens
    Record             .anarres/example/environment.json
    Digest  sha256:5471a6e0fb121640260770060a3b858f2e31100a66b73eb2210bd59603dd76d9
```

The digest binds the measured record to its content. `validate` recomputes the
record checks and exits nonzero if the input is invalid. Add `--json` when a
script, notebook, or CI job should consume the same report.

### Update or remove a standalone installation

Rerun the installer to update to the latest tagged release. To install a fixed
version, replace `latest/download` with the release tag:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/download/anarres-cli-v0.3.1/anarres-cli-installer.sh | sh
```

The standalone installer places the binary in `$CARGO_HOME/bin`, or
`$HOME/.cargo/bin` when `CARGO_HOME` is unset. Remove that binary to uninstall:

```bash
rm "${CARGO_HOME:-$HOME/.cargo}/bin/anarres"
```

## Commands

Anarres has two command layers:

1. **Built-ins** transform and compare versioned local records. Use these when
   measurements already conform to an Anarres probe or profile schema.
2. **Domain adapters** preserve a study's native measurements, costs, failure
   states, and scientific boundaries. Use these to inspect, reproduce, or
   extend a released domain workflow.

The built-in `design` command checks whether candidates can be compared and
reports their measured coordinates. It does not silently turn those
coordinates into a winner. A domain adapter may expose a decision command only
when its study defines and validates that decision rule.

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
descriptor without opening study artifacts. `adapter run` launches the adapter
once with a versioned runtime handshake and forwards domain arguments literally
without a shell. The adapter validates the protocol and identity before opening
study artifacts. Built-in commands always take precedence over adapter names.
Descriptor queries must finish in five seconds and stay below 256 KiB of output,
preventing a faulty adapter from blocking installation audits.

The CLI does not download adapters, search a repository checkout, or import an
adapter's libraries. The [adapter installation guide](adapters.md) gives the
supported checkout-based commands for every maintained adapter. The
[adapter authoring guide](architecture/adapter-authoring.md) defines the
descriptor and release requirements.

### Choose a domain workflow

Install the adapter you need from the paths in the [adapter installation
guide](adapters.md), then begin with `status`. The status command shows what is
released, what remains sealed, and which operations are supported.

| Domain | First useful commands | What they reveal |
| --- | --- | --- |
| Formal verification | `anarres formal status --repository .`<br>`anarres formal qualification --repository .` | Local Vero support and the separate development qualification |
| Robotics | `anarres robotics status --repository .`<br>`anarres robotics can-results --repository .` | Workflow stage and the released prospective Can result |
| Legal reasoning | `anarres legal status --repository .`<br>`anarres legal regressions --repository .` | SylloGym selection evidence and the separate LAB regression audit |
| Materials science | `anarres materials status --repository .`<br>`anarres materials results --repository .` | Frozen protocol boundary and the scored prospective MLIP test |
| Molecular design | `anarres molecular status --repository .`<br>`anarres molecular verify --repository .` | Qualified reaction-bank measurements and deterministic verification |
| Agentic finance | `anarres finance status --repository .`<br>`anarres finance decide <panel.json>` | Released evidence and a calibrated selection or abstention decision |

Use `anarres <domain> --help` to see every operation for that adapter. Commands
that plan, prepare, submit, gate, or score an experiment remain domain-specific
because their runtimes and completeness contracts differ.

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
anarres finance decide candidate-panel.json
anarres finance profile --output-dir .anarres/finance
anarres finance score-holdout finharmbench
anarres finance verify
anarres finance verify --exhaustive
anarres finance reproduce --output-dir .anarres/finance-reproduction
```

`status` reports the released capabilities and current prospective boundary.
`audit-sources` validates immutable source revisions and generator preflight.
`profile` converts the completed starting-policy qualification into a shared
profile input. `score-holdout` reruns one frozen source test from its released
decision contract. `verify` quickly validates source pins, qualification
artifacts, compact retrospective summaries, and frozen holdout identities.
`verify --exhaustive` reruns every released finance check in an isolated copy.
`reproduce` performs the same exhaustive replay and exports the regenerated
retrospective, strict-transfer, and frozen-holdout artifacts without modifying
checked-in evidence.

`decide` validates a complete finance candidate panel, applies the released
practical rule, and returns either one selected environment or an abstention
set. An optional `baseline_id` adds improvement or regression directions. The
fixed 0.2 margin is the largest threshold selected across the source-held-out
0.85-precision calibration folds. Its released retrospective operating point
has 90.3% pairwise accuracy at 75.4% coverage across seven sources. The command
does not convert that retrospective operating point into a prospective
guarantee.

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

## Example adapter: robotics planning and scoring

The robotics adapter converts the frozen Can v1.4.1 protocol into a portable
workflow plan and recomputes the released prospective result:

```bash
uv tool install \
  ./experiments/robotics/environment-selection/prospective-cupid-can-v141
anarres robotics status --repository .
anarres robotics plan --repository . \
  --output .anarres/can-v141.plan.json
anarres robotics can-results --repository . --json
```

The plan records five candidate arms, five seeds per arm, and 25 candidate runs
with matched training and evaluation tasks. It also retains stage dependencies,
exact input digests, workload totals, and the release gate that precedes
scoring. The record is deterministic and content-addressed. Planning performs
no training, simulator execution, network request, or scheduler submission.

The released plan reconstructs the original pre-outcome workload. `prepare`
binds the exact candidate masks to the pinned dataset, while `bundle` records a
CuraEval checkout, Python environment, accelerator type, and local or Slurm
launcher. Execution remains behind explicit `submit --execute`; scoring remains
behind the completeness and identity gate.

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
