# RFC 0007: Portable robotics adapter

- Status: proposed
- Date: 2026-11-20
- Issue: #64

## Context

The installed robotics adapter reproduces the released RoboMimic Can v1.4.1,
PushT, and Square studies. Its package lives with one study in
`experiments/robotics/environment-selection/prospective-cupid-can-v141`, and its
descriptor accepts one native format, `robomimic-can-v141-hdf5`. A robotics team
with its own candidate datasets, starting policy, and evaluation contract cannot
follow the shared `init`, `inspect`, `qualify`, `probe`, and `measure` path
without editing Anarres code.

Robotics sources differ in observation and action spaces, demonstration units,
reset semantics, success definitions, and cost units. RoboMimic, LIBERO, and
MetaWorld store these in different native formats and use different simulators.
Policies come from different frameworks and checkpoints. A single robotics
parser or an embedded policy runtime would erase those distinctions and couple
Anarres releases to simulator releases.

RFC 0003 defines the adapter executable boundary. RFC 0005 separates
environment execution from attempt aggregation. RFC 0006 defines the source
manifest and the `qualify-source` and `probe-source` dispatch. This RFC applies
those contracts to robotics and adds the two interfaces they leave open: source
drivers and an external policy runner.

## Decision

### Package and name

A new maintained package, `packages/robotics`, provides the study-independent
adapter. It owns the distribution name `anarres-robotics`, the executable
`anarres-robotics`, and the descriptor name `robotics`. Its descriptor names no
study. It reports the native formats of the installed source drivers, the
installed study commands, and their measurement contracts. It reads only
entry-point names to do so and imports no driver or study module.

The Can study package is renamed `anarres-robotics-cupid-can-v141` and stops
installing an `anarres-robotics` executable. It provides the Can source driver
and registers its study commands with the portable adapter. Existing commands
such as `anarres robotics can-results` keep their names, arguments, and output
bytes. Their installation command changes, which is the breaking part of this
proposal.

The study package declares three entry-point groups:
`anarres.robotics.source_drivers` for its driver,
`anarres.robotics.study_commands` for its command names, and
`anarres.robotics.measurement_contracts` for its contract identifiers. The
adapter reads only the entry-point names when it builds its descriptor. It
imports a study module only when that study's command runs, and it passes the
arguments through unchanged. A study command cannot shadow an adapter command.

The Can workflow plan names its producer. That producer becomes
`anarres-robotics-cupid-can-v141` at the study package version, so the plan
digest changes while its tasks, inputs, and release gate stay identical. The
released reports and exported profiles are byte-identical. The Can driver
qualifies the released dataset. It refuses to list probe tasks, because the Can
probe contract records that its execution is not released.

### Source drivers

A source driver translates one native format into the robotics input contract
without rewriting the native files. Drivers are separately versioned Python
distributions registered under the entry-point group
`anarres.robotics.source_drivers`. The adapter imports a driver only when a
source declares its format, so the descriptor command stays side-effect free.

A driver declares its `native_format`, version, and accepted manifest fields.
For each source it must report:

- candidate and dataset identity, revision, license, and content digest
- the episode or demonstration unit and its grouping key
- observation, action, and optional language-instruction fields
- task, scene, or initial-state identity when the source provides it
- duration and other collected or generated cost fields, with native units
- success, termination, truncation, and infrastructure outcomes
- reset and evaluation semantics

A missing required field fails qualification. A field the source does not
provide is reported as missing and never filled with a default.

### Policy-runner protocol

Anarres invokes a starting policy through an external executable and never
imports a policy framework. The adapter launches the runner without a shell:

```text
<runner> --anarres-policy-runner-protocol 1 \
  --request <request.json> --output <attempt-directory>
```

The request follows `anarres.robotics-policy-runner-request.v1`. It binds the
starting-policy identity and revision, the source identity and digest, the
driver name and version, the evaluation-contract digest, the ordered list of
task or episode identities with their seeds, and the step and wall-clock
limits. The number of attempts follows from the task and seed list. Credentials, endpoints, and private runtime state stay in the
runner's environment and never enter the request or the outputs.

The runner writes `attempts.jsonl`, one row per attempt following
`anarres.robotics-probe-attempt.v1`, and a `runner-result.json` following
`anarres.robotics-policy-runner-result.v1`. The result binds the runner name and
version to the request digest and lists the digests of produced artifacts.
The adapter stops a runner that exceeds the wall-clock limit and reports the
probe as an infrastructure timeout. Each attempt row records the
task identity, sample index, seed, closed-loop success, termination or
truncation, control steps, simulated and wall-clock duration, and a separate
infrastructure status. Reset, simulator, checkpoint, and runtime failures are
infrastructure statuses and never become scientific failure.

`probe-source` plans by default, following the molecular adapter and RFC 0004.
Without `--execute` it writes the request and the complete ordered execution
plan and launches nothing, so planning requires no accelerator. Execution
requires the adapter argument `--execute`, passed after `--`.

The adapter declares the `policy-probe` capability only after a real native
source and policy runner pass conformance tests, as RFC 0006 requires. Until
then the shared `anarres probe` command reports that probing is unavailable,
and `anarres-robotics probe-source` remains available for direct invocation
with the fixture driver and runner.

### Measurement and comparison

Robotics attempts keep native costs such as control steps and simulated
seconds. The adapter converts qualified attempts to the existing
`anarres.environment-profile-input.v1` record, as RFC 0006 permits for
domain-native measurements. The Rust core then validates, hashes, and compares
profiles as it does today. Robotics attempts do not populate the
`generated_action_tokens` field of `anarres.probe-attempt.v1`, because control
steps and generated tokens are different units.

Candidates are comparable only when the starting policy, target, episode unit,
and measurement contract match. The core already rejects mismatched contracts.
The robotics adapter adds checks for the episode unit and evaluation contract
before export.

### Decision and freeze

The robotics decision command compares the frozen selection rule with random
and source-native cost or length baselines. It returns `abstain` when the rule
is unsupported for the panel, predicted margins are unresolved, or required
measurements are missing. The freeze record binds candidate membership, the
starting policy, measurements, baselines, the decision or abstention, the
target, the training budget, the evaluation contract, and artifact digests
before downstream outcomes are opened. These records build on proposed RFC 0004
(predictive decision records), and their schemas will be added in a revision of
this RFC after the first implementation stage.

### Command path

| Step | Command | Owner |
| --- | --- | --- |
| init | `anarres init <source> --adapter robotics ...` | core |
| inspect | `anarres inspect <source>` | core, adapter descriptor |
| qualify | `anarres qualify <source>` | adapter and source driver |
| probe | `anarres probe <source> --policy ... [-- --execute]` | adapter and policy runner |
| measure | `anarres measure <probe-run>` | core, after adapter export |
| design | `anarres design <record> <record>` | core |
| freeze | `anarres robotics freeze ...` | adapter |

## Acceptance

The design is accepted for portability only when two source paths complete it:

1. The released Can source runs through the Can driver and reproduces the
   released claim-bearing compact results byte for byte.
2. One independently qualified source with a distinct native format and policy
   runner reaches a frozen pre-outcome decision or a justified abstention. Issue
   #62 selects this source.

## Implementation stages

1. Add the package, descriptor, driver and runner interfaces, one deterministic
   fixture driver and runner, and the request and attempt schemas. Route the
   Can source through the driver interface and demonstrate
   `init -> inspect -> qualify -> probe` (planning only) from outside the repository.
2. Add bounded probe execution, profile export, and comparability checks.
3. Add the decision and freeze records.
4. Add the independent source driver after #62.

## Alternatives considered

- **Generalize the Can package in place.** This keeps one package but leaves
  shared robotics behavior under one study's directory, against the repository
  layout rules.
- **One universal robotics parser.** This would flatten native observations,
  actions, and success definitions into one table.
- **Embedded policy frameworks.** This would add large, fast-changing
  dependencies to the adapter and tie releases to model frameworks.
- **Reuse `anarres.probe-attempt.v1` unchanged.** This would require storing
  control steps as generated tokens.

## Consequences

New robotics sources need a driver and a runner, and no change to Anarres code.
The descriptor reports what each installation can do. Users of the released
studies change one installation command. The repository gains one maintained
package and two shared schemas.

## Open questions

- Should study commands keep their current names through delegation, as the
  first implementation does, or move under
  `anarres robotics study <study> <command>`?
- Should drivers be discovered only through entry points, or also from a path
  declared in `anarres.toml`?
- Should the Rust core later accept a declared cost unit so robotics attempts
  can use native aggregation directly?
- How should a candidate declare its membership when it is a subset of one
  native file? Each Can candidate is the released HDF5 dataset plus a list of
  demonstrations. The source description has no membership field yet, so the
  Can driver describes the whole dataset as one source.
- Does a fixture driver and runner count as conformance for the
  `policy-probe` capability, or must the adapter wait for the independent source
  from #62? The first implementation waits.
- Should the adapter descriptor report capabilities that are known but
  unavailable? The current descriptor schema does not allow that field.
