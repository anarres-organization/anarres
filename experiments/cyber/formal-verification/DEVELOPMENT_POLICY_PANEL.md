# Formal-verification development-policy panel

**Status date:** 2026-11-10

**Status:** design only. No candidate in this record is authorized for
scientific measurement.

This panel asks whether a lower-cost policy provides enough nondegenerate Vero
coverage for repeated environment measurement, or whether the stronger policy
is required. It is a development decision under one matched task, harness,
grader, containment, and budget. It does not rank formal-verification models in
general.

## Public evidence

LeanLean evaluates GPT-5.6 Sol and GPT-5.6 Luna at xhigh reasoning through
Codex 0.154.0 on the same 64-repository compression benchmark. Sol records
valid submissions on 63 repositories, 37.77% mean compression, and $135.51
mean cost. Luna also records 63 valid submissions, with 13.08% mean compression
and $2.32 mean cost. The objectives differ from Vero, so these values nominate
candidates without predicting Vero completion.

The pinned source revisions and native-contract values are preserved in the
[public policy-support record](public-evidence/data/policy-support.json) and
[starting-policy audit](STARTING_POLICY_SELECTION.md).

The Forall VeriSoftBench release provides the strongest direct support for a
nondegenerate task panel. Under GPT-5.6 Sol at xhigh reasoning through Codex,
15 tasks are first solved after sample one in a Pass@8 run. Each therefore has
at least one unsuccessful and one successful attempt under the same policy and
task. These task identities should seed the first repeated-measurement panel
once their public repositories, fresh checker, and model-facing containment are
qualified. PrimePy remains a route check because its 9/9 outcome is too easy to
measure a useful success boundary.

The wider source audit does not yield one policy ranking. Opus 5 leads LeanLean
compression, GPT-5.5 xhigh leads Vero repository completion, and Luna is the
lowest-cost reported LeanLean policy. GPT-5.5 is unavailable through the
current executable route. Opus 5 remains an independent-harness replication
candidate after a matching Claude Code containment path is qualified.

## Matched candidates

The first route screen contains two policies:

| Candidate | Model | Reasoning | Harness target | Why included |
| --- | --- | --- | --- | --- |
| Sol | `gpt-5.6-sol` | xhigh | managed Codex harness with a self-hosted task sandbox | stronger released repository evidence and one prior excluded Vero support result |
| Luna | `gpt-5.6-luna` | xhigh | managed Codex harness with a self-hosted task sandbox | lower-cost released repository evidence under the same model family and tool interface |

The route follows OpenAI's documented separation between the managed harness
and a [self-hosted sandbox](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted).
The model records document shell and patch tooling for
[Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) and
[Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

Model availability must be confirmed before the protocol is frozen. The
self-hosted route differs from the Codex 0.154 harness used by LeanLean and the
completed PrimePy attempt. Both candidates therefore require fresh excluded
route qualification. Their earlier outcomes remain source evidence rather
than measurements of the new route.

## Execution order

1. Qualify the task-only executor, restricted environment key, mount policy,
   network policy, cleanup, and fresh grader without opening a new task outcome.
2. Run one excluded PrimePy support attempt per candidate under identical
   containment, prompt, tool, and 90-minute budget contracts. Infrastructure
   failures may be retried under the same identity; scientific failures remain
   immutable.
3. If at least one route passes support and containment, freeze one
   outcome-blind queue covering the four development repositories in both Vero
   modes. Run one attempt for every qualified candidate and queue identity.
   Qualification and prospective repositories remain unopened.
4. Select one policy for repeated measurement, then freeze its model, reasoning
   setting, harness, executor, prompt, tools, budget, and grader.

## Selection and stop rule

A candidate is eligible only when every attempt is infrastructure-valid, the
containment controls pass, and strict fresh grading shows nonzero support in at
least two development repositories. Rank eligible candidates first by the
number of repository-mode identities with at least one passed and one failed
specification. This favors broader partial coverage because it supplies both
successful and unsuccessful specifications for later policy-relative
measurement. Break a tie by lower measured model cost, then by lexical model
identifier. Report all development outcomes regardless of which candidate is
selected.

If neither candidate passes the support gate, stop. Do not open qualification
or prospective repositories, increase the budget, or substitute a new model
without a new source-audited protocol. If only one candidate passes, select it
without interpreting the screen as a general model comparison.

## Evidence boundary

This screen chooses a usable starting policy for one Vero experiment. It does
not estimate reliability from a single route qualification, establish
downstream training utility, or replace the later repeated measurement. The
policy decision is complete only after the frozen development queue is scored.
