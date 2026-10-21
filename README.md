# <img src="docs/assets/anarres-logo.jpeg" alt="Anarres" height="42" align="top"> Anarres

[![Quality](https://github.com/anarres-organization/anarres/actions/workflows/quality.yml/badge.svg)](https://github.com/anarres-organization/anarres/actions/workflows/quality.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/downloads/)

**Anarres is an open research program and software platform for predicting how training environments shape model improvement.**

Equal post-training budgets can improve a model, do very little, or make it worse across different environments. Anarres develops policy-relative measurements, data systems, and controlled experiments to predict those differences before expensive reinforcement-learning runs begin. The goal is to make environment selection a measurable, predictable part of post-training.

## How it works

```text
task sources
    → verify fixtures and rewards
    → measure experience under the target policy
    → construct candidate environments
    → predict finite-budget utility
    → test predictions with controlled RL
```

Anarres separates infrastructure validity, policy-relative learnability, and downstream utility. Sandbox failures remain infrastructure failures. Valid tasks must still be measured under the target policy, and reward alone does not determine held-out improvement.

The project provides:

- **Research releases** that connect measurements made before RL to downstream learning curves.
- **Environment processing** for turning heterogeneous task sources into verified, policy-measured candidate banks.
- **Reusable packages** for qualification, environment coordinates, provenance, and evaluation.
- **Versioned schemas** that keep data and experiment contracts interoperable across domains.

## Research program

| Area | Question | Status |
| --- | --- | --- |
| [Mathematics](experiments/mathematics/README.md) | Can starting-policy measurements predict finite-budget RL utility across model scale? | Study assets available |
| [Agentic systems](experiments/agentic/README.md) | Which measurements transfer to terminal, coding, and tool-using agents? | Active research |
| [Environment processing](data/environment-processing/README.md) | How can heterogeneous task collections become reliable RL environment banks? | In development |
| [Cyber](experiments/cyber/README.md) | How should utility be measured under executable security tasks and containment constraints? | Qualification underway |
| [AI for Science](experiments/ai-for-science/README.md) | Which training environments improve scientific models for a specified target and compute budget? | Molecular-design and materials-science protocols drafted |
| [Robotics](experiments/robotics/README.md) | Which environments help robots improve across diverse embodied tasks? | Planning |

## Get started

The reference environment-processing path is CPU-only. It requires Python 3.11 or newer, [`uv`](https://docs.astral.sh/uv/), and `make`.

```bash
git clone https://github.com/anarres-organization/anarres.git
cd anarres
make setup
make check
make example
```

The example classifies task groups without conflating infrastructure failures with reward zero, computes ρ and H from a frozen policy probe, and writes a content-addressed environment manifest to `.anarres/example/environment.json`.

To run the processor directly:

```bash
PYTHONPATH=packages/core/src:packages/environments/src:packages/evaluation/src \
  python -m anarres.environments.cli probe \
  examples/environment-processing/probe.json \
  --output .anarres/example/environment.json
```

## Inspect a study record

The mathematics environment-utility directory provides a versioned experimental record with configurations, disjoint evaluation data, pre-RL measurements, compact results, and audit scripts.

```bash
cd experiments/mathematics/environment-utility
python scripts/audit_study.py
python scripts/summarize_prerl.py
python scripts/reproduce_tables.py
```

The audit checks prompt counts and disjointness, configuration coverage, evaluation completeness, prospective chronology, and every recorded content hash.

## Repository map

```text
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

- [Environment-processing design](data/environment-processing/DESIGN.md)
- [Environment-processing implementation plan](data/environment-processing/ROADMAP.md)
- [Repository architecture](docs/architecture/repository.md)
- [Reproducibility standard](docs/standards/reproducibility.md)
- [Artifact standard](docs/standards/artifacts.md)
- [Contribution guide](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)
- [Security policy](SECURITY.md)

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
