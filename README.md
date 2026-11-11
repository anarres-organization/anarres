<p align="center">
  <img src="docs/assets/anarres-logo.jpeg" alt="Anarres" height="128">
</p>

<h1 align="center">Anarres</h1>

<p align="center"><strong>Measure and compare training environments before committing the full training budget.</strong></p>

<p align="center">
  <a href="https://github.com/anarres-organization/anarres/actions/workflows/quality.yml"><img src="https://github.com/anarres-organization/anarres/actions/workflows/quality.yml/badge.svg" alt="Quality"></a>
  <a href="https://github.com/anarres-organization/anarres/releases"><img src="https://img.shields.io/github/v/release/anarres-organization/anarres?filter=anarres-cli-v%2A&amp;label=CLI" alt="Latest CLI release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License: Apache 2.0"></a>
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="docs/cli.md">Documentation</a> ·
  <a href="#research-program">Research</a> ·
  <a href="https://github.com/anarres-organization/anarres/releases">Releases</a> ·
  <a href="https://github.com/anarres-organization/anarres/issues">Issues</a>
</p>

Anarres is an open-source toolkit and research program for predicting how
training environments shape model improvement. It qualifies task sources,
measures the experience they produce under a starting policy, compares
compatible candidates, and preserves the evidence behind each decision.

Equal post-training budgets can improve a model, do little, or make it worse.
Anarres makes those differences measurable before an expensive training run.

## Install

On macOS or Linux:

```bash
brew install anarres-organization/tap/anarres && anarres --version
```

The standalone installer is available when Homebrew is not:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
"${CARGO_HOME:-$HOME/.cargo}/bin/anarres" --version
```

Open a new terminal after the standalone installer updates `PATH`. If the shell
still cannot find the command, run `~/.cargo/bin/anarres --version` to confirm
the installation and follow the [PATH troubleshooting guide](docs/releases.md#command-not-found).

Windows, pinned-version, archive, checksum, and source-install options are in
the [release guide](docs/releases.md).

## Quick start

Install the CLI and run the bundled CPU-only workflow:

```bash
brew install anarres-organization/tap/anarres && anarres demo
```

The demo qualifies one candidate, measures its usable experience, and compares
two candidates produced under the same starting policy:

```text
Anarres demo
Repeated attempts from one starting policy are qualified, measured, and compared.

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

3. Compare
  ✓ Compatible   candidate panel
    Candidates         2

Next  anarres design .anarres/demo/environment.json .anarres/demo/environment-alternative.json
```

The `Next` line is a runnable command. Generated records live in the local
`.anarres/` working directory, which is ignored by Git and can be regenerated.
Run the demo from a project directory or pass `--output` to choose a different
location.

The [CLI guide](docs/cli.md) continues with your own measurements, candidate
comparison, installed domain workflows, JSON output, and shell completions.

## Core CLI and domain workflows

### What you provide

Bring two or more candidate environments measured under the starting policy
you intend to train. An environment can be a prompt distribution, proof-task
set, robot-episode dataset, collection of legal matters, molecular or material
structures, or another domain-defined source of training experience.

Keep each environment in its native format and add one small `anarres.toml`
beside it. The manifest names the domain adapter, the native format, and the
pinned source identity without copying domain data into a universal task table:

```toml
schema_version = "anarres.environment-source.v1"
environment_id = "candidate-a"
domain = "agentic-systems"
adapter = "openenv"
adapter_version = "0.1.0"
native_format = "openenv"

[source]
uri = "./native-environment"
revision = "git:<commit>"
license = "Apache-2.0"
```

Source-capable adapters qualify the native files and run the starting policy.
The Rust core then measures their normalized attempt stream:

```bash
anarres inspect ./candidate-a
anarres qualify ./candidate-a
anarres probe ./candidate-a \
  --policy <policy> \
  --policy-revision <revision> \
  --output .anarres/probes/candidate-a
anarres measure .anarres/probes/candidate-a --output .anarres/environments/candidate-a.json
```

The built-in workflow accepts raw attempt streams or grouped measurements with:

- stable task and candidate identifiers
- the starting policy and measurement contract
- repeated outcomes, generated cost, and per-attempt loss admission
- oracle, no-op, and infrastructure-validity checks

If a domain uses different measurements, its adapter emits the same portable
profile envelope while preserving its native coordinates, units, uncertainty,
and failure states. Candidates are comparable only when their starting subject
and measurement contract match. See the [input guide](docs/cli.md#what-you-bring)
and [versioned schemas](schemas/) for the exact contracts.

Homebrew installs the native `anarres` binary. Its built-in commands operate on
portable records and do not require a domain runtime:

| What you want to do | Start with | What it returns |
| --- | --- | --- |
| Inspect a native environment and its adapter | `anarres inspect <environment>` | Native format, source identity, adapter readiness, and missing requirements |
| Run repeated starting-policy attempts | `anarres probe <environment> ...` | A versioned raw-attempt directory |
| Find invalid, unusable, or comparison-ready measurements | `anarres qualify <environment-or-probe>` | Source checks or measurement status counts |
| Create a portable environment record | `anarres measure <input> --output <record>` | Coordinates, provenance, costs, and a content digest |
| Compare a candidate panel | `anarres design <record-a> <record-b>` | Compatibility checks and candidate coordinate ranges |
| Check a record before using it | `anarres validate <record>` | Structural, semantic, and integrity results |

Domain workflows are installed separately because robotics simulators, legal
evaluators, chemistry packages, and executable sandboxes have different
dependencies. Once installed, they appear under the same CLI:

```bash
anarres adapter list
anarres legal status --repository .
anarres robotics status --repository .
```

The adapter preserves each study's measurements, units, failure states, and
costs rather than replacing them with one universal model. See
[Install domain workflows](docs/adapters.md) for the supported adapters and
their first useful commands.

## How it works

```text
task sources
    → verify fixtures and rewards
    → measure experience under the target policy
    → construct candidate environments
    → predict finite-budget utility
    → test predictions with controlled training
```

Anarres keeps three questions separate: whether a task and verifier work,
whether the starting policy produces usable experience, and whether training on
that experience improves a held-out target. Infrastructure failures never
become ordinary unsuccessful attempts.

## Research program

| Area | Question | Status |
| --- | --- | --- |
| [Mathematics](experiments/mathematics/README.md) | Can starting-policy measurements predict finite-budget RL utility across model scale? | Study assets available |
| [Agentic systems](experiments/agentic/README.md) | Which measurements transfer to terminal, coding, and tool-using agents? | Program overview; concrete studies use domain adapters |
| [Cyber: formal verification](experiments/cyber/formal-verification/README.md) | Which executable proof environments improve held-out verification under a fixed policy and budget? | Positive public training-environment evidence and policy audit released; Vero containment qualification pending |
| [Cyber: vulnerability exploitation](experiments/cyber/qualification/README.md) | Which authorized exploit-generation environments provide measurable signal and held-out improvement? | Scaffold qualification and repeated-policy measurement released; no environment comparison |
| [Molecular design](experiments/ai-for-science/molecular-design/README.md) | Which reaction-based environments improve a molecular graph policy for a specified protein target and compute budget? | Candidate-bank qualification passed; outcomes remain sealed |
| [Materials science](experiments/ai-for-science/materials-science/README.md) | Which atomistic training distributions improve a materials model for a specified physical target and compute budget? | MLIP prospective test scored; the learned selector missed and exposes a support boundary |
| [Robotics](experiments/robotics/README.md) | Which environments help robots improve across diverse embodied tasks? | First evidence release available |
| [Legal reasoning](experiments/legal/README.md) | Can policy-relative measurements guide legal training-mixture selection? | Native adapter and evidence release available |
| [Agentic finance](experiments/finance/README.md) | Which finance-task distributions improve held-out work under fixed training and control budgets? | Native CLI workflow and retrospective evidence available |

Statuses describe released evidence, not a uniform claim of predictive support.
The [domain support matrix](docs/domain-support.md) separates public protocols,
runnable adapters, and downstream validation.

## Develop

The reference environment-processing path is CPU-only. Repository development requires Rust, Python 3.11 or newer, [`uv`](https://docs.astral.sh/uv/), and `make`.

```bash
git clone https://github.com/anarres-organization/anarres.git
cd anarres
make setup
make check
make study-check
make example
```

`make check` tests software and schemas. `make study-check` separately
reproduces the compact released study records and maintained adapter outputs.
The slower `make study-check-extended` also runs exhaustive isolated releases.

Install the native command from a checkout:

```bash
cargo install --path crates/anarres-cli --locked
anarres --version
```

The mathematics release can also be inspected directly:

```bash
cd experiments/mathematics/environment-utility
python scripts/audit_study.py
python scripts/summarize_prerl.py
python scripts/reproduce_tables.py
```

The audit checks prompt counts and disjointness, configuration coverage,
evaluation completeness, prospective chronology, and recorded content hashes.

## Repository map

```text
crates/       Native command-line and systems components
packages/     Reusable libraries with maintained interfaces
data/         Environment acquisition, qualification, and construction
experiments/  Domain-organized research and released evidence
schemas/      Versioned machine-readable contracts
docs/         Architecture, standards, and design decisions
examples/     Small examples that run without a cluster
tools/        Repository validation tools
tests/        Cross-package integration tests
```

Large model weights and checkpoints are distributed through versioned artifact stores rather than Git. Compact configurations, results, manifests, and analyses live beside the research they reproduce.

## Documentation

- **Use the software:** [CLI guide](docs/cli.md), [adapter installation](docs/adapters.md), [release and verification guide](docs/releases.md), and [first-run evaluation](docs/first-run-evaluation.md)
- **Integrate a domain:** [domain adapters](docs/architecture/domain-adapters.md), [adapter authoring](docs/architecture/adapter-authoring.md), and [measurement conventions](docs/conventions/README.md)
- **Understand the system:** [repository architecture](docs/architecture/repository.md), [scientific preservation](docs/architecture/scientific-preservation.md), [performance](docs/performance.md), and [domain support](docs/domain-support.md)
- **Contribute:** [contribution guide](CONTRIBUTING.md), [governance](GOVERNANCE.md), and [security policy](SECURITY.md)

## About the name

Anarres takes its name from the moon in Ursula K. Le Guin's [*The Dispossessed*](https://www.ursulakleguin.com/dispossessed), whose society develops under distinct environmental and social constraints. The project carries that question into learning systems: how does an environment shape the improvement a model can realize from a fixed compute budget?

## Contributing

Contributions to source adapters, qualification checks, shared measurements, evaluation, documentation, and scientific experiments are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Consequential changes to shared schemas or maintained interfaces begin with an RFC. Ordinary fixes and experiment-local improvements can proceed through a pull request.

## Citation

If you use Anarres in your research, please cite the project:

```bibtex
@software{anarres2026,
  author = {{Anarres contributors}},
  title = {Anarres: Open Infrastructure and Research for Predictable Post-Training},
  year = {2026},
  url = {https://github.com/anarres-organization/anarres}
}
```

Machine-readable citation metadata is available in [`CITATION.cff`](CITATION.cff). Study-specific citations will accompany their public research releases.

## Acknowledgements

Anarres draws on ideas and infrastructure from the broader open-source research community. We are especially grateful to [Marin](https://github.com/marin-community/marin), [LeRobot](https://github.com/huggingface/lerobot), [OpenSpiel](https://github.com/google-deepmind/open_spiel), and [vLLM](https://github.com/vllm-project/vllm) for demonstrating strong approaches to experiment organization, reusable components, evaluation, and open collaboration.

## License

Unless a subdirectory states otherwise, Anarres software is released under the [Apache License 2.0](LICENSE). Dataset and model artifacts retain their upstream licenses and terms.
