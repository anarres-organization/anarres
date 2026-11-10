# Codex containment requalification

**Status:** route design plus an unqualified local-model implementation. This
record does not authorize another model attempt.

The excluded PrimePy qualification establishes strict task support for
GPT-5.6 Sol with Codex 0.154.0. Vero's fresh grader passes all nine
specifications after retaining only editable slots. The post-run audit also
shows that the direct local Codex process could read generic guidance from the
upstream checkout and write a temporary file outside the rendered task. No
reference proof or protected repository was accessed, but this boundary is too
broad for repeated measurement.

The next deployment must separate the model harness from model-directed
execution. OpenAI's self-hosted sandbox design makes this distinction explicit:
the harness owns the agent loop and model connection, while a fresh environment
owns shell commands and filesystem state. Only inputs intended for the agent
should be mounted into that environment. See the official
[self-hosted sandbox](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted)
and [sandbox-agent](https://developers.openai.com/api/docs/guides/agents/sandboxes)
guides.

## Route status

Two containment routes are currently distinct:

1. The repository implements an agent-socket Docker boundary for Vibe with
   local inference. Its contract, server, and negative-test harness are present,
   but remain unqualified. The frozen controller and inference records bind
   this implementation to Leanstral, which has already failed the Vero support
   screen. This implementation cannot be used to claim containment of the
   completed GPT-5.6 Sol qualification.
2. OpenAI's self-hosted Agents API route can keep the Codex harness outside a
   task-only environment and connect `codex exec-server` from inside that
   environment. Only a restricted environment key enters the sandbox. This
   route has not been implemented or qualified here. It also differs from the
   Codex CLI 0.154 harness used for the completed PrimePy support result, so it
   requires a new excluded route qualification before scientific measurement.

The development-screen policy must be selected only after candidate routes
have passed their own support and containment controls. A policy result cannot
be transferred across a different harness merely because the model name is the
same.

## Required boundary

Each attempt must begin from a newly rendered Vero task and a new execution
environment. The model-facing environment may contain only:

1. the rendered task mounted read-write at one workspace root
2. the pinned Lean and Lake runtime
3. tools required by the frozen interaction contract
4. ephemeral controller material that cannot authorize unrelated API actions.

The environment must not expose the upstream Vero checkout, reference proofs,
other benchmark partitions, another attempt's workspace, personal
configuration, or host temporary directories. Model-directed commands must
have no network access. Controller networking must remain limited to the model
provider, and the grader must run outside the model-facing environment against
a fresh benchmark render.

Python remains the orchestration language. The security boundary comes from
the container or sandbox provider, mount policy, process identity, and network
policy rather than from rewriting the controller in a systems language.

## Requalification controls

Before a new development screen, the exact deployment must pass all of the
following controls:

- **workspace read:** a command cannot read a sentinel above or beside the
  rendered task
- **workspace write:** a command cannot create or modify a file outside the
  task workspace
- **partition isolation:** qualification, prospective, and reference trees are
  absent from the model-facing filesystem
- **credential isolation:** task commands cannot recover a credential that
  authorizes model or repository access
- **network isolation:** task commands cannot reach the public internet, local
  metadata services, or the controller endpoint
- **process isolation:** task commands cannot inspect or signal host or sibling
  processes
- **fresh reset:** independent materializations have identical task-tree and
  instruction hashes
- **grader separation:** the fresh grader accepts only declared editable slots
  and rejects frozen-source, marker, statement, axiom, and `sorry` changes
- **cleanup:** the attempt environment, temporary filesystem, and restricted
  controller credential are destroyed after grading.

Every control must be exercised through the same path used by the model. A
configuration inspection is supporting evidence, not a substitute for negative
tests.

## Route qualification

The preferred implementation uses a separate harness and self-hosted sandbox
because it gives the task a narrow workspace without exposing controller state.
That route is admissible only if the selected model, reasoning setting,
interaction semantics, executor revision, and usage accounting can be bound
exactly. If the route changes the policy or harness identity, it requires a new
excluded support qualification before the development screen.

The direct local Codex route remains useful for the completed support result.
Repeated measurement through that route requires an operating-system or
container boundary that satisfies the same negative controls.

## Decision after containment

A complete containment pass authorizes only a separately frozen
development-only screen. The screen must establish nonzero strict coverage in
at least two development repositories before repeated measurement is designed.
It cannot open qualification or prospective repositories, rank environments,
or authorize downstream training.
