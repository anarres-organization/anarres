# <img src="docs/assets/anarres-logo.jpeg" alt="Anarres" height="42" align="top"> Anarres

[![Quality](https://github.com/anarres-organization/anarres/actions/workflows/quality.yml/badge.svg)](https://github.com/anarres-organization/anarres/actions/workflows/quality.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/downloads/)

**Measure and compare training environments before committing the full training budget.**

[Install](#install) · [Quick start](#quick-start) · [Research](#research-program) · [CLI guide](docs/cli.md) · [Releases](https://github.com/anarres-organization/anarres/releases) · [Issues](https://github.com/anarres-organization/anarres/issues) · [Contributing](CONTRIBUTING.md)

Anarres is an open-source toolkit and research program for predicting how
training environments shape model improvement. It qualifies task sources,
measures the experience they produce under a starting policy, compares
compatible candidates, and preserves the evidence behind each decision.

Equal post-training budgets can improve a model, do little, or make it worse.
Anarres makes those differences measurable before an expensive training run.

## How it works

```text
task sources
    → verify fixtures and rewards
    → measure experience under the target policy
    → construct candidate environments
    → predict finite-budget utility
    → test predictions with controlled RL
```

Anarres keeps three questions separate: whether a task and verifier work,
whether the starting policy produces usable experience, and whether training on
that experience improves a held-out target. Infrastructure failures never
become ordinary unsuccessful attempts.

The native CLI exposes four stable operations:

| Command | Purpose |
| --- | --- |
| `anarres qualify` | Check whether measured evidence is ready for comparison |
| `anarres measure` | Write a normalized, content-addressed environment record |
| `anarres design` | Compare compatible candidates and audit the panel |
| `anarres validate` | Check supported records and their content integrity |

Domain adapters preserve the measurements, units, failure states, and costs of
their originating studies. They extend the CLI without forcing robotics, legal
reasoning, materials science, or executable agents into one measurement model.
The native installer does not install every domain runtime. The
[adapter installation guide](docs/adapters.md) shows how to add only the
domain commands needed for a study.

## Install

Install the native CLI with Homebrew on macOS or Linux:

```bash
brew install anarres-organization/tap/anarres
```

Or use the standalone installer without requiring Python or Rust:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
```

Restart your shell if the installer updates `PATH`, then verify the installation:

```bash
anarres --version
```

Windows, pinned-version, archive, checksum, and source-install options are in
the [release guide](docs/releases.md).

## Quick start

Run the complete local workflow on the bundled CPU-only fixture:

```bash
git clone --depth 1 https://github.com/anarres-organization/anarres.git
cd anarres
anarres qualify examples/environment-processing/probe.json
mkdir -p .anarres/example
anarres measure examples/environment-processing/probe.json \
  --output .anarres/example/environment.json
anarres validate .anarres/example/environment.json
```

This fixture demonstrates the command contract rather than a scientific result.
The [CLI guide](docs/cli.md) continues with candidate comparison, installed
adapters, JSON output, shell completions, and record schemas.

## Research program

| Area | Question | Status |
| --- | --- | --- |
| [Mathematics](experiments/mathematics/README.md) | Can starting-policy measurements predict finite-budget RL utility across model scale? | Study assets available |
| [Agentic systems](experiments/agentic/README.md) | Which measurements transfer to terminal, coding, and tool-using agents? | Program overview; concrete studies use domain adapters |
| [Cyber: formal verification](experiments/cyber/formal-verification/README.md) | Which executable proof environments improve held-out verification under a fixed policy and budget? | Starting policy selected for development qualification |
| [Cyber: vulnerability exploitation](experiments/cyber/qualification/README.md) | Which authorized exploit-generation environments provide measurable signal and held-out improvement? | Scaffold qualification and repeated-policy measurement released; no environment comparison |
| [Molecular design](experiments/ai-for-science/molecular-design/README.md) | Which reaction-based environments improve a molecular graph policy for a specified protein target and compute budget? | Candidate-bank qualification passed; outcomes remain sealed |
| [Materials science](experiments/ai-for-science/materials-science/README.md) | Which atomistic training distributions improve a materials model for a specified physical target and compute budget? | Retrospective bridge validated; candidate selection in progress |
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
- **Understand the system:** [repository architecture](docs/architecture/repository.md), [scientific preservation](docs/architecture/scientific-preservation.md), and [domain support](docs/domain-support.md)
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
