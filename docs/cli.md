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
brew tap \
  anarres-organization/tap
brew install anarres
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

The complete unstyled output is:

```text
Anarres demo
Repeated attempts from one starting policy are qualified, measured, and compared.

Input
    Starting policy    synthetic-policy-v1
    Candidates         2 synthetic alternatives
    Task groups        5 per candidate
    Group size         4 attempts
    Measurements       outcomes, admitted advantage mass, and generated tokens
    Validity           oracle, no-op, and infrastructure checks

1. Qualify
  ✓ Qualified    math-reference-demo-v1
    Admitted           2
    Reserve            1
    Repair             1
    Quarantine         1

2. Measure
  ✓ Measured     math-reference-demo-v1
    Signal density     833.3333 advantage mass / million generated tokens
    Effective coverage 0.6533 (0 to 1)
    Evidence           3 eligible task groups, 4,200 generated tokens

3. Compare
  ✓ Compatible   candidate panel
    Policy             synthetic-policy-v1
    Revision           synthetic-reference-only
    Candidates         2

ENVIRONMENT               SIGNAL / 1M   COVERAGE  ADMITTED   REPAIR
math-alternative-demo-v1     214.2857     0.4154         2        1
math-reference-demo-v1       833.3333     0.6533         2        1

    Signal span        214.2857 to 833.3333
    Coverage           0.4154 to 0.6533

Artifacts
  ✓ Wrote        .anarres/demo/environment.json
  ✓ Wrote        .anarres/demo/environment-alternative.json
  ✓ Validated    2 content digests

Next  anarres design .anarres/demo/environment.json .anarres/demo/environment-alternative.json
    Use your data: anarres qualify --help
```

## What you bring

Anarres compares candidate sources of training experience for a specified
starting policy or system. A candidate may contain prompts, executable tasks,
proof obligations, robot episodes, legal matters, molecular structures,
materials configurations, or another domain-defined unit.

The complete path begins with the domain's native files. Do not rewrite a
Harbor task, OpenEnv package, robot dataset, legal matter panel, reaction bank,
or structure set into a generic task row. Add an `anarres.toml` beside the
native source instead:

```bash
anarres init ./candidate-a \
  --adapter <adapter> \
  --revision <immutable-revision> \
  --license <SPDX-identifier>
```

`init` reads the installed adapter descriptor, records its domain and exact
version, and infers the native format when the adapter accepts only one. It
refuses unknown formats and never guesses between multiple formats. The written
manifest is:

```toml
schema_version = "anarres.environment-source.v1"
environment_id = "candidate-a"
domain = "robotics"
adapter = "robotics"
adapter_version = "0.5.0"
native_format = "robomimic-can-v141-hdf5"

[source]
uri = "."
revision = "sha256:<dataset-digest>"
license = "<dataset-license>"
```

The envelope contains dispatch and provenance only. Policy credentials,
runtime secrets, outcomes, and domain-specific task contents remain outside
it. Source qualification and policy probing are separate adapter capabilities.
Every source begins with inspection and qualification:

```bash
anarres inspect ./candidate-a
anarres qualify ./candidate-a
```

When `inspect` reports `Can probe yes`, the adapter can run the starting policy
and the Rust core can stream and aggregate the resulting attempts:

```bash
anarres probe ./candidate-a \
  --policy <policy> \
  --policy-revision <revision> \
  --output .anarres/probes/candidate-a
anarres measure .anarres/probes/candidate-a \
  --output .anarres/environments/candidate-a.json
```

`inspect` reports the selected adapter, its accepted native formats, and whether
qualification and probing are available. These are separate capabilities: an
adapter may be able to validate a native dataset before it can execute the
starting policy. `anarres inspect <source>` shows the available next step, and
`anarres adapter doctor <name>` reports the same contract at the adapter level.
Evidence-only adapters do not become environment runners automatically.

Every maintained domain adapter now declares one native source format. The
shared `init`, `inspect`, and `qualify` sequence verifies source identity and
routes the source to its domain contract. Qualification does not imply that
policy execution is available. `inspect` reports those capabilities separately.

The molecular adapter currently declares the portable `policy-probe`
capability. Its probe binds a qualified reaction environment to a pinned
starting policy and remains dry-run by default. Robotics exposes a separate
content-addressed planning and execution workflow for the Can study. Finance,
formal verification, legal reasoning, materials science, and vulnerability
exploitation currently stop at source or runtime qualification in the shared
path. Their domain commands preserve the additional gates required before
model execution. See the [adapter guide](adapters.md) for the exact source
format and released boundary of each workflow.

Use the built-in probe-run contract when an environment runtime can provide:

1. stable candidate, task, and starting-policy identifiers
2. a fixed sampling and measurement contract
3. repeated attempts grouped by task
4. one outcome, generated cost, and loss-admission decision per attempt
5. oracle, no-op, and infrastructure-validity results

Use a domain adapter when the study requires different native measurements.
Adapters preserve those coordinates, units, uncertainty, costs, provenance,
and failure states inside a portable profile rather than converting every
domain to one universal score. Candidate records can be compared only when the
starting subject and measurement contract match.

The runtime writes `probe.json` plus streaming `attempts.jsonl`. The native CLI
checks exact group membership and derives the declared leave-one-out admitted
advantage mass. Producers therefore do not need to reproduce Anarres's
aggregation code. Start with `anarres adapter list` to discover installed
domain workflows. The source-envelope example lives in
`examples/environment-source/`; normalized fixtures live in
`examples/environment-processing/` and `examples/environment-profiles/`.

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
  https://github.com/anarres-organization/anarres/releases/download/anarres-cli-v0.4.0/anarres-cli-installer.sh | sh
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

| Command | Purpose | Input |
| --- | --- | --- |
| `init` | Connect native files to an installed adapter | Native environment directory |
| `inspect` | Show the source format and available adapter operations | Environment directory or `anarres.toml` |
| `qualify` | Check a native source or measured evidence | Environment source, probe run, policy-probe input, or profile input |
| `probe` | Measure a qualified source under a pinned starting policy | Environment directory or `anarres.toml` |
| `measure` | Normalize evidence into a content-addressed record | Probe-run directory, policy-probe input, or profile input |
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

An adapter that accepts native environments must expose source qualification
and may expose policy probing. Qualification validates the native task,
verifier, and runtime setup. A probe executes repeated attempts under a pinned
starting policy and writes measurements for the Rust core. These capabilities
are tested separately from evidence-reproduction commands such as `status` or
`results`.

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
| Materials science | `anarres materials status --repository .`<br>`anarres materials qualify-source --manifest <anarres.toml>`<br>`anarres materials results --repository .` | Native atomistic-bank qualification, the frozen protocol boundary, and the scored prospective MLIP test |
| Molecular design | `anarres molecular status --repository .`<br>`anarres molecular acquisition-results --repository .` | Qualified reaction-bank measurements and separate released antibody and protein acquisition panels |
| Agentic finance | `anarres finance status --repository .`<br>`anarres finance decide <panel.json>` | Released evidence and a calibrated selection or abstention decision |
| Vulnerability exploitation | `anarres vulnerability status`<br>`anarres vulnerability qualify-source --help` | Sanitized CyberGym source qualification and the current execution boundary |

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
coverage from one fixed policy probe. A domain profile instead retains the
adapter's own measurements. Both output types record the source, starting model
or system, measurement setup, provenance, and content digests.

Writes are atomic, and an existing destination is preserved unless `--force`
is supplied. Use `--force` only when intentionally regenerating a derived
record from reviewed input.

### Design a candidate panel

```bash
anarres design .anarres/candidates/*.json
```

`design` audits whether candidates can be interpreted together. Grouped-probe
manifests must share the starting policy and probe setup. Domain profiles must
share the domain, starting model or system, adapter revision, measurement
setup, and coordinate definitions. A changed unit, estimator, definition, or
adapter revision makes the panel incompatible.

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

Profiles record the domain, starting model or system, adapter revision,
measurement setup, qualification checks, named coordinates, units, estimators,
uncertainty, and supporting artifacts. The portable record keeps the domain's
original measurements. The native study remains the authority for scientific
interpretation.

The [domain integration matrix](domain-support.md) distinguishes schema
conformance, native adapters, and predictive evidence. The [domain adapter
guide](architecture/domain-adapters.md) defines the runtime boundary, and the
[adapter authoring guide](architecture/adapter-authoring.md) documents the
Python construction interface and promotion requirements.

Detailed finance commands live in the [finance overview](https://github.com/anarres-organization/anarres/tree/main/experiments/finance).
The robotics planning, execution, and scoring sequence lives in the
[Can study guide](https://github.com/anarres-organization/anarres/tree/main/experiments/robotics/environment-selection/prospective-cupid-can-v141).

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

- [`probe-input.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/environments/probe-input.v1.schema.json)
- [`environment-manifest.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/environments/environment-manifest.v1.schema.json)

Cross-domain profiles use:

- [`environment-profile-input.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/environments/environment-profile-input.v1.schema.json)
- [`environment-profile.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/environments/environment-profile.v1.schema.json)

Installed adapters describe their compatibility with:

- [`adapter-descriptor.v1`](https://github.com/anarres-organization/anarres/blob/main/schemas/adapters/adapter-descriptor.v1.schema.json)

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
states instead of converting them into ordinary failures.
