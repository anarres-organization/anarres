# LAB workflow intake

This adapter validates and inventories the target side of a Harvey LAB experiment before any model response or training outcome is used. It reads a pinned LAB checkout and records task identity, practice area, work type, matter documents, deliverables, and criterion-level review structure.

An installed adapter can qualify the native checkout through the shared source
workflow:

```bash
anarres init /path/to/harvey-labs \
  --adapter legal \
  --revision "LAB-REVISION" \
  --license MIT
anarres inspect /path/to/harvey-labs
anarres qualify /path/to/harvey-labs
```

`inspect` reports source qualification as available and policy probing as
unavailable. Qualification validates the complete task and matter-document
inventory without reading model responses, judge verdicts, or training
outcomes. The adapter can qualify a portable execution contract, but it does
not execute the LAB harness or advertise policy probing.

The explicit inventory export remains available when task-level rows are
needed:

```bash
anarres legal lab-intake \
  --lab-root /path/to/harvey-labs \
  --source-revision v1.3.0 \
  --output-dir /path/to/intake
```

The command emits a compact summary and one JSONL row per task. Its content address covers both task specifications and matter-document bytes. It validates the fields needed to define a LAB-shaped target, while preserving fields that must come from later run artifacts or a supplemental legal contract.

The intake is model agnostic. Model and checkpoint identity enter with the run artifacts, not the target representation. The output is not an environment profile and contains no policy measurement, judge verdict, or downstream outcome. It cannot support a training-utility claim by itself.

Before execution, package the starting-policy and judge runtimes in a separate
versioned record:

```bash
anarres legal lab-contract \
  --input /path/to/contract-draft.json \
  --output /path/to/lab-execution-contract.json
```

The [execution-contract guide](EXECUTION_CONTRACT.md) defines the required
model, checkpoint, harness, tools, compaction, judge, scoring, accounting,
validity, and protected-outcome fields. The command content-addresses the
record and rejects credentials. It does not launch either runtime.

Native LAB runs can then be audited without assuming a provider-specific model name:

```bash
anarres legal lab-runs \
  --repository /path/to/anarres \
  --results-root /path/to/harvey-labs/results \
  --run-manifest /path/to/run-manifest.json \
  --execution-contract /path/to/lab-execution-contract.json \
  --output-dir /path/to/run-audit
```

The optional manifest binds each native run ID to policy, intervention,
checkpoint, seed, and role. When an execution contract is supplied, the
manifest also records the contract, model revision, checkpoint ID, and
checkpoint revision. The audit checks the agent configuration, compaction,
runtime identity, and judges before accepting a score. Missing metrics,
incomplete runs, judge mismatches, and other infrastructure failures never
become legal failures.

## Frontier legal experiment

A complete experiment joins three records without collapsing them:

1. **Target workflow intake.** Tasks, matter documents, deliverables, rubric criteria, practice areas, and any supplemental jurisdiction or risk metadata.
2. **Starting-policy run record.** Exact model and checkpoint, harness and tools, criterion verdicts, all-pass, document coverage, artifact completion, tool use, latency, token cost, and infrastructure validity.
3. **Training intervention record.** Candidate membership, budget, seed, checkpoints, and the same held-out outcome vector after training.

This separation supports comparisons across model families while keeping the legal workflow, evaluator, and training intervention explicit.

## Source

Harvey LAB is released under the MIT License. Its task schema and evaluation methodology are documented in the [official repository](https://github.com/harveyai/harvey-labs) and [evaluation guide](https://github.com/harveyai/harvey-labs/blob/main/docs/eval-strategies.md).
