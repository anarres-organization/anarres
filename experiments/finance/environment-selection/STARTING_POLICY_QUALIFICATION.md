# Starting-policy qualification for finance operations

The prospective experiment needs a policy that can use the ERP tools reliably
while leaving enough outcome variation to compare candidate environments. This
stage selects that policy on development scenarios only. It does not construct
candidate mixtures or inspect held-out scenarios.

## Qualification panel

The panel contains the four generator-qualified workflows:

- freight accrual revision
- month-end close
- payment run
- payment-run need-to-know.

Eight new development seeds are generated per workflow. Each scenario receives
four independent rollouts, producing 128 episodes in total. Task-defined business
dates, counterparties, handbooks, controls, and executable graders remain
unchanged. The policy receives four tools: read a workspace file, list workspace
files, call the ERP command, and write a handoff note. Every tool call and state
transition is recorded.

## Policy ladder

Qualification begins with
[`Qwen/Qwen3-8B`](https://huggingface.co/Qwen/Qwen3-8B) at revision
`b968826d9c46dd6066d109eabc6255188de91218`. The checkpoint is Apache-2.0,
supports the Qwen tool-call template, and is small enough to measure without
committing the resources required by the final training panel.

The next candidate is
[`Qwen/Qwen3-30B-A3B-Instruct-2507`](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507).
The checkpoint is pinned at revision
`0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe` and remains unevaluated unless 8B
fails the complete qualification record. A tool-specialized checkpoint can be
considered when the limiting failure is tool-protocol validity rather than task
performance. Every evaluated checkpoint receives a separately named
qualification record.

## Fixed rollout contract

- temperature 0.6
- top-p 0.95
- four rollouts per scenario
- 8,192-token total interaction limit
- at most 24 tool calls per business turn
- task-defined turn count and business clock
- no outcome-driven retry or seed replacement
- infrastructure retries repeat the identical scenario, rollout seed, and model
  configuration.

The interaction limit is a qualification setting. The final training contract
may adopt a larger limit before the prospective freeze if valid episodes show
systematic truncation.

## Admission gates

A policy qualifies when one complete record satisfies all of the following:

1. every planned episode has either a valid result or a separately recorded
   infrastructure failure
2. at least 98% of non-infrastructure episodes execute the tool protocol validly
3. held-out-style executable completion on development scenarios lies between
   2% and 80%
4. at least 10% of complete scenario groups contain both successful and failed
   rollouts
5. at least two workflow families contain a mixed scenario group
6. no more than 10% of non-infrastructure episodes exhaust the interaction limit
7. the record reports material-control violations, generated tokens, tool calls,
   and truncation separately.

Infrastructure failures never become task reward zero. Material-control
violations remain visible even when an episode completes its requested work.
Failure to qualify selects the next policy in the ladder only after the failure
mode is identified.

## Selection rule

The smallest policy that passes every gate becomes the starting-policy candidate.
If several policies pass, the study chooses the least expensive policy whose
mixed-group fraction is within five percentage points of the largest passing
value. The rule prevents a larger model from winning solely through higher
starting accuracy when a smaller model provides comparable environment
measurement.

The selected policy, revision, tool schema, rollout settings, and qualification
record are frozen before candidate-bank measurement begins.

## Machine-readable scoring

`scripts/score_policy_qualification.py` accepts one JSONL row per planned
episode. Each row contains the policy, workflow, scenario, rollout seed,
execution validity, reward, control outcome, token count, tool-call count, and
truncation status. The script computes the gates without reading candidate or
held-out partitions.

`adapters/business-bench-openai-policy.sh` implements the upstream Business
Bench harness contract for an OpenAI-compatible local policy endpoint. It offers
only the ERP command, workspace reads, workspace listing, and handoff-note
writes. It does not provide a general shell. The adapter records every model
message, tool call, tool result, and protocol error for later conversion into a
qualification record. A completed policy attempt returns normally even when its
trace contains an invalid tool call. This keeps model protocol failures distinct
from endpoint or harness failures.

`scripts/convert_business_bench_qualification.py` converts completed process
attempts into the JSONL schema above. It marks an attempt infrastructure-valid
only when every planned turn has a trace, exits normally, and avoids a timeout.
Deterministic grading failures and control breaches remain policy outcomes.

```bash
python scripts/convert_business_bench_qualification.py \
  business-bench/results/qualification-qwen3-8b \
  --policy-id qwen3-8b-pinned \
  --output qualification-attempts.jsonl
```

```bash
python scripts/score_policy_qualification.py \
  qualification-attempts.jsonl \
  --expected-workflows 4 \
  --expected-scenarios-per-workflow 8 \
  --group-size 4 \
  --output qualification-summary.json
```

The summary is descriptive until the complete signed attempt record, model
revision, and environment identity are attached.
