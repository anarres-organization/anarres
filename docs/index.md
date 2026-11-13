# Anarres

Measure and compare training environments before committing the full training
budget.

Anarres is an open-source toolkit and research program for determining which
training environments are most likely to improve a model at fixed compute. It
connects domain-native measurements to portable evidence without flattening the
science that produced them.

[Install Anarres](#installation), then follow the
[first steps](getting-started.md) or browse the released
[research programs](https://github.com/anarres-organization/anarres/tree/main/experiments).

## Highlights

- Covers mathematical reasoning, cyber, robotics, legal reasoning, molecular
  design, materials science, and agentic finance through native formats.
- Separates task qualification, starting-policy measurement, and validation
  against later training outcomes, while keeping infrastructure failures
  distinct from ordinary failures.
- Preserves measurement definitions, units, uncertainty, costs, and provenance
  in versioned, content-addressed records.
- Combines a fast Rust CLI for shared operations with installable adapters for
  specialized domain runtimes.

## Installation

Install the native CLI, then verify that it is available:

=== "Homebrew"

    ```console { .mobile-terminal }
    $ brew tap \
        anarres-organization/tap
    $ brew install anarres
    $ anarres --version
    ```

=== "Standalone installer"

    ```console { .mobile-terminal }
    $ curl --proto '=https' --tlsv1.2 -LsSf \
        https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
    $ anarres --version
    ```

=== "Windows"

    ```powershell { .mobile-terminal }
    powershell -ExecutionPolicy ByPass -c "irm https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.ps1 | iex"
    anarres --version
    ```

Then follow the [first steps](getting-started.md), or see every installation
method in the [release guide](releases.md). Domain adapters are installed only
when a workflow needs its specialized runtime.

## Quick start

Run the bundled CPU-only workflow:

```console { .mobile-terminal }
$ anarres demo
```

The demo qualifies two environments, measures both under the same synthetic
starting policy, checks that their records are comparable, and writes validated
records to `.anarres/demo/`.

To use native data, connect a source to its matching adapter and inspect the
requirements before running a policy probe:

```console { .mobile-terminal }
$ anarres init ./candidate-a \
    --adapter <adapter> \
    --revision <revision> \
    --license <SPDX-id>
$ anarres inspect ./candidate-a
$ anarres qualify ./candidate-a
```

The [first-run workflow](getting-started.md) continues from a native source to a
portable environment record. The [domain support guide](domain-support.md)
shows which formats, probes, and outcome tests are available today.

## How it works

```text
native task sources
    → qualify tasks, verifiers, and rewards
    → measure experience under the starting policy
    → compare compatible candidate environments
    → test frozen predictions through controlled training
```

Anarres keeps three questions separate: whether a task and verifier work,
whether the starting policy produces usable experience, and whether training on
that experience improves a held-out target. Infrastructure failures never
become ordinary failures.

The native CLI handles routing, validation, hashing, and comparison. Installable
adapters retain specialized runtimes where simulators, evaluators, chemistry
packages, or executable sandboxes are required.

## Domains

The same environment-selection question takes a different form in each domain.
These examples describe the scope of the research program rather than an
exhaustive list of supported tasks or datasets.

| Domain | What Anarres examines |
| --- | --- |
| [Mathematical reasoning](https://github.com/anarres-organization/anarres/tree/main/experiments/mathematics/environment-utility) | Prompt distributions, verifiers, rollout signal, and finite training budgets |
| [Formal verification](https://github.com/anarres-organization/anarres/tree/main/experiments/cyber/formal-verification) | Proof tasks, repository context, tool access, and machine-checked outcomes |
| [Robotics](https://github.com/anarres-organization/anarres/tree/main/experiments/robotics/environment-selection) | Demonstrations, task distributions, embodiments, and rollout success |
| [Legal reasoning](https://github.com/anarres-organization/anarres/tree/main/experiments/legal) | Legal tasks, practice areas, interaction depth, and regression risk |
| [Materials science](https://github.com/anarres-organization/anarres/tree/main/experiments/ai-for-science/materials-science) | Atomistic datasets, physical targets, and post-training outcomes |
| [Molecular design](https://github.com/anarres-organization/anarres/tree/main/experiments/ai-for-science/molecular-design) | Molecular experience, target-specific acquisition, and finite oracle budgets |
| [Vulnerability exploitation](https://github.com/anarres-organization/anarres/tree/main/experiments/cyber/qualification) | Authorized tasks, agent scaffolds, containment, and exploit verification |
| [Agentic finance](https://github.com/anarres-organization/anarres/tree/main/experiments/finance) | Finance tasks, tool use, operational controls, and evidence trails |

The [domain support guide](domain-support.md) reports the native formats,
runnable interfaces, and validation currently released for each domain.

## Learn more

- Install a [domain adapter](adapters.md).
- Read the complete [CLI guide](cli.md).
- Check the current [domain support](domain-support.md).
- See how Anarres [preserves domain-native science](architecture/scientific-preservation.md).
- Browse the released [research programs](https://github.com/anarres-organization/anarres/tree/main/experiments).
