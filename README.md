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

Run the bundled CPU-only workflow:

```bash
anarres demo
```

The demo runs locally without an adapter or GPU. It qualifies two candidate
environments, measures the experience each produces under the same starting
policy, checks that they can be compared, and writes validated portable
records. The comparison makes their usable signal density and effective
coverage visible before training.

```text
  ✓ Qualified    math-reference-demo-v1
  ✓ Measured     math-reference-demo-v1
  ✓ Compatible   candidate panel

ENVIRONMENT               SIGNAL / 1M   COVERAGE  ADMITTED   REPAIR
math-alternative-demo-v1     214.2857     0.4154         2        1
math-reference-demo-v1       833.3333     0.6533         2        1
```

Use the generated records immediately:

```bash
anarres design \
  .anarres/demo/environment.json \
  .anarres/demo/environment-alternative.json
```

Generated records live in the local `.anarres/` working directory, which is
ignored by Git and can be regenerated. Run the demo from a project directory
or pass `--output` to choose a different location. Real domain data uses one of
the domain workflows described below.

The [CLI guide](docs/cli.md#first-run) includes the complete terminal output,
then continues with your own measurements, domain workflows, JSON output, and
shell completions.

## Core CLI and domain workflows

Bring two or more candidate sources and the starting model or system you want
to evaluate. A source may contain prompts, proof tasks, robot episodes, legal
matters, molecular structures, atomistic configurations, or another
domain-defined form of training experience.

Keep each source in its native format. Anarres can qualify every maintained
format, and supported adapters can also run the starting-policy measurement.
Begin by connecting a source to its adapter:

```bash
anarres init ./candidate-a \
  --adapter <adapter> \
  --revision <immutable-revision> \
  --license <SPDX-identifier>
```

`inspect` reports what the installed adapter can do with that format. Every
maintained adapter can qualify its native source. Adapters that can execute a
starting policy also expose `probe`:

```bash
anarres inspect ./candidate-a
anarres qualify ./candidate-a
anarres probe ./candidate-a \
  --policy <policy> \
  --policy-revision <revision> \
  --output .anarres/probes/candidate-a
anarres measure .anarres/probes/candidate-a \
  --output .anarres/environments/candidate-a.json
```

Not every adapter can probe yet. The CLI reports that boundary directly and
keeps domain-specific measurements, units, uncertainty, and failure states in
the resulting records. See the [input guide](docs/cli.md#what-you-bring) and
[adapter guide](docs/adapters.md) for the exact workflow available in each
domain.

Homebrew installs the native `anarres` binary. Its built-in commands operate on
portable records and do not require a domain runtime:

| What you want to do | Start with | What it returns |
| --- | --- | --- |
| Connect a native environment to an adapter | `anarres init <directory> ...` | A pinned `anarres.toml` source manifest |
| Inspect a native environment and its adapter | `anarres inspect <environment>` | Native format, source identity, adapter readiness, and missing requirements |
| Measure a source under the starting policy | `anarres probe <environment> ...` | A shared probe-run or domain-native profile input |
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
    → compare compatible candidates
    → evaluate domain-specific predictions with controlled training
```

Anarres keeps three questions separate: whether a task and verifier work,
whether the starting policy produces usable experience, and whether training on
that experience improves a held-out target. Infrastructure failures never
become ordinary unsuccessful attempts.

## Research program

| Area | Question | Status |
| --- | --- | --- |
| [Mathematics](experiments/mathematics/README.md) | Can starting-policy measurements predict finite-budget RL utility across model scale? | Four-scale evidence released |
| [Agentic systems](experiments/agentic/README.md) | Which measurements transfer to terminal, coding, and tool-using agents? | Domain workflows available |
| [Cyber: formal verification](experiments/cyber/formal-verification/README.md) | Which executable proof environments improve held-out verification under a fixed policy and budget? | Evidence and runtime qualification released |
| [Cyber: vulnerability exploitation](experiments/cyber/qualification/README.md) | Which authorized exploit-generation environments provide measurable signal and held-out improvement? | Source qualification released |
| [Molecular design](experiments/ai-for-science/molecular-design/README.md) | Which reaction-based environments improve a molecular graph policy for a specified protein target and compute budget? | Probe qualified; training outcomes sealed |
| [Materials science](experiments/ai-for-science/materials-science/README.md) | Which atomistic training distributions improve a materials model for a specified physical target and compute budget? | Prospective test scored |
| [Robotics](experiments/robotics/README.md) | Which environments help robots improve across diverse embodied tasks? | Prospective evidence released |
| [Legal reasoning](experiments/legal/README.md) | Can policy-relative measurements guide legal training-mixture selection? | Evidence and source qualification released |
| [Agentic finance](experiments/finance/README.md) | Which finance-task distributions improve held-out work under fixed training and control budgets? | Retrospective evidence and source qualification released |

Statuses describe released evidence, not a uniform claim of predictive support.
The [domain support matrix](docs/domain-support.md) separates public protocols,
runnable adapters, and downstream validation.

## Develop

The reference environment-processing path is CPU-only. Repository development
requires Rust, Python 3.11 or newer, [`uv`](https://docs.astral.sh/uv/), and
`make`.

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

Install the native command from a checkout with
`cargo install --path crates/anarres-cli --locked`. Each study README contains
its own reproduction command and scientific scope.

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
