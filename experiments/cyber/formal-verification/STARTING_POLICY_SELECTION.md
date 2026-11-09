# Vero starting-policy selection

**Status date:** 2026-11-09

This record selects the next development-only starting policy after Leanstral
failed the frozen Vero support screen and budget ladder. The selection uses
released repository-level Lean evidence before allocating another benchmark
run. It does not open qualification or prospective repositories, rank training
environments, or authorize downstream training.

## Selection criteria

A candidate must satisfy all of the following conditions:

1. released evidence on repository-level Lean work or a released Vero baseline
2. a named model, agent harness, reasoning setting, and executable verifier
3. evidence that the agent edits repositories and returns buildable artifacts
4. an available route that can be frozen without changing the Vero task
5. a fresh development-only support test before repeated measurement.

Single-theorem mathematics scores are insufficient because Vero requires an
agent to inspect a repository, organize reusable lemmas, preserve marker slots,
and return a buildable artifact for fresh grading.

## Audited evidence

| Candidate | Released repository evidence | Operational finding | Decision |
| --- | --- | --- | --- |
| GPT-5.5 xhigh with Codex | Vero reports 25/43 proof-only full solves and 9/9 PrimePy specifications under Codex 0.140.0 and a 90-minute budget | The model is not available through the current ChatGPT-backed Codex route | Exact Vero reference, not the next executable policy |
| GPT-5.6 Sol xhigh with Codex | The unaided Codex configuration reports 97/100 benchmark-rule and 86/100 strict successes on the VeriSoftBench-Aristotle subset. LeanLean records valid verified submissions on 63/64 repositories under Codex 0.154.0. | Codex 0.154.0 is installed and a non-benchmark route check succeeds | Selected for development qualification |
| Opus 5 with Claude Code | LeanLean records valid submissions on 64/64 repositories and the highest mean compression. The unaided VeriSoftBench subset run reaches 100/100 benchmark-rule and 89/100 strict success. | No matching Claude Code route has been qualified in this execution environment | Independent replication candidate |
| GPT-6 Astra with Codex | LeanLean reports verified compression on a 12-repository subset, and separate Lean Eval submissions establish larger software-verification capability | The released repository panel is smaller and no Vero baseline is available | Later replication candidate |
| Leanstral 1.5 with Vibe | LeanLean and theorem-proving releases establish Lean capability outside Vero | The frozen Vero measurement and 200k-to-1M budget ladder produce zero strict support | Rejected for this Vero contract |

The numeric results above preserve each source's own acceptance contract. They
do not make LeanLean compression, VeriSoftBench theorem completion, and Vero
repository completion interchangeable outcomes.

## Source audit

The source records were inspected at immutable revisions:

- Vero paper and repository:
  [`sunblaze-ucb/vero@0a7325d`](https://github.com/sunblaze-ucb/vero/tree/0a7325df9e9e6dbc275c0ad483b3d1cbe38d9b09),
  with the model and per-instance results reported in
  [arXiv:2608.13522](https://arxiv.org/abs/2608.13522)
- LeanLean:
  [`eth-sri/lean-lean@55097cf`](https://github.com/eth-sri/lean-lean/tree/55097cfe752717cd5ac9aca09a18b335d9c5bb7a),
  including the committed model configuration and result tables
- Forall-Lean-Agent VeriSoftBench release:
  [`astrio-labs/forall-verisoftbench@bac4c64`](https://github.com/astrio-labs/forall-verisoftbench/tree/bac4c6482fca597d965f9c18e78abacf0ad6204e),
  whose validator covers 23 release files, 1,300 task records, 761 axiom
  audits, and 400 independent checks
- Forall-Lean-Agent paper:
  [arXiv:2610.00885](https://arxiv.org/abs/2610.00885)

LeanLean pins GPT-5.6 Sol to Codex 0.154.0, xhigh reasoning, native harness
defaults, a 12-hour ceiling, eight CPUs, 64 GiB of memory, and model-proxy-only
networking. The next Vero qualification reuses the model and harness identity,
while retaining Vero's own task, grader, and 90-minute budget. It does not copy
LeanLean's objective or treat its score as a Vero result.

## Selected development qualification

The selected policy is GPT-5.6 Sol at xhigh reasoning through Codex 0.154.0.
The first attempt uses PrimePy in proof-only mode because Vero's released table
shows that the repository is solvable by two frontier configurations, including
the native Codex baseline. This is an excluded support test rather than an
estimate of policy reliability.

The qualification must preserve:

- the pinned Vero source and existing PrimePy development task
- the native Codex repository interface
- one fresh task and one independent final grade
- a 90-minute wall-clock ceiling
- model-provider-only network access and no task-internet access
- strict rejection of `sorry`, unapproved axioms, marker changes, and frozen
  source edits.

Policy support is established only if the attempt reaches infrastructure-valid
fresh grading and at least one specification passes with approved axioms. A
successful support test permits a fresh development screen under a separately
frozen protocol. It does not permit environment ranking or downstream
training.

## Why this is the next useful test

The prior result no longer leaves the failure ambiguous. Vero's released table
shows that PrimePy is solvable, while the larger Leanstral budget still returns
no valid scored slot. Changing the starting policy is therefore better
supported than extending the same interaction budget again. GPT-5.6 Sol also
keeps the next test close to two released precedents: native Codex on Vero and
the same model-harness pair on repository-scale Lean studies.
