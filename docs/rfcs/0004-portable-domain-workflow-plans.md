# RFC 0004: Portable domain workflow plans

- Status: accepted
- Date: 2026-11-10

## Context

Domain adapters can qualify measurements and produce interoperable profiles,
but long-running experiments still begin from study-specific scripts. Robotics
adds simulator state, policy checkpoints, paired initial conditions, candidate
training, and sealed outcome gates. Encoding those details in the native Rust
CLI would couple the core release cycle to one simulator and scheduler.

Established workflow tools separate planning from execution. Snakemake exposes
a dry run before any job starts. DVC can queue an experiment without executing
it and derives the queued work from a fixed workspace state. Ray Jobs treats a
remote submission as an explicit entrypoint plus a runtime environment. Anarres
uses the same boundary while retaining each study's scientific contract.

## Decision

Domain adapters may emit deterministic, content-addressed workflow plans. A
plan records the frozen inputs, stage dependencies, task matrix, aggregate
workload, resource contract, release gate, and outcome-access boundary. Creating
a plan performs no training, evaluation, network request, or scheduler action.

The first implementation covers the frozen RoboMimic Can v1.4.1 candidate
comparison. `plan` records the scientific workload without binding it to a
machine. `prepare` verifies the official source artifact and writes the frozen
candidate masks to a copy. `bundle` binds that plan to a pinned CuraEval
checkout, an exact Python environment, and either local or Slurm execution.
`run-task --execute` is the explicit mutation boundary, and `gate` verifies all
checkpoint and log identities before results may be scored.

Submission remains a separate, explicit operation. Scheduler-specific records
remain outside the scientific plan. The released executor supports a
deterministic multi-GPU local launcher and dependency-linked Slurm arrays.
Additional backends can bind
the same task manifest without changing the frozen candidate comparison.

The plan generator remains in the Python domain adapter because it interprets
robotics-specific protocol fields and runs once per experiment. Simulator and
training time dominate its runtime. The Rust core continues to own fast routing,
record validation, hashing, and compatible-profile comparison. A shared plan
validator may move into Rust after two domains produce the same stable envelope
and cross-language conformance tests exist.

## Consequences

Users can inspect the exact candidate matrix and workload before committing
compute. Automation can consume one stable JSON record without depending on a
particular cluster. Planning and bundling cannot accidentally launch an
expensive run. A bundle records the complete package freeze and refuses to run
if that environment changes. The prepared dataset, CuraEval revision, candidate
memberships, checkpoints, and evaluation logs are checked by digest.

The plan remains unbound by design and therefore reports the runtime and
scheduler choices as blockers. A successful bundle resolves both for one
execution target. This changes execution readiness without changing the frozen
candidates or prospective decision.

## References

- [Snakemake command-line dry runs](https://snakemake.readthedocs.io/en/latest/executing/cli.html)
- [DVC experiment queues](https://dvc.org/doc/user-guide/experiment-management/running-experiments)
- [Ray Jobs overview](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/index.html)
