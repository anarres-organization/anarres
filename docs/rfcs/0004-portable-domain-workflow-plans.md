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

The first implementation is `anarres robotics plan`. It describes the frozen
RoboMimic Can v1.4.1 candidate comparison and makes its current execution
blockers explicit. The command does not manufacture an executable entrypoint
where the public study does not yet provide one.

Submission remains a separate, explicit operation. A future executor may bind
one validated plan to Ray Jobs, Slurm, Kubernetes, or another scheduler, but the
scheduler-specific record must remain separate from the scientific plan. The
executor must preserve plan and artifact digests, isolate runs, expose status
and logs, and keep candidate outcomes sealed until the release gate passes.

The plan generator remains in the Python domain adapter because it interprets
robotics-specific protocol fields and runs once per experiment. Simulator and
training time dominate its runtime. The Rust core continues to own fast routing,
record validation, hashing, and compatible-profile comparison. A shared plan
validator may move into Rust after two domains produce the same stable envelope
and cross-language conformance tests exist.

## Consequences

Users can inspect the exact candidate matrix and workload before committing
compute. Automation can consume one stable JSON record without depending on a
particular cluster. The command cannot accidentally launch an expensive run,
and a scientifically complete plan does not imply that the runtime is portable
or ready for submission.

The first robotics plan remains intentionally blocked until the repository
contains a portable candidate-training entrypoint, an immutable runtime image,
and a selected scheduler binding. Adding those pieces changes execution
readiness, not the frozen candidates or prospective decision.

## References

- [Snakemake command-line dry runs](https://snakemake.readthedocs.io/en/latest/executing/cli.html)
- [DVC experiment queues](https://dvc.org/doc/user-guide/experiment-management/running-experiments)
- [Ray Jobs overview](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/index.html)
