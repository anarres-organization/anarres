# LAB workflow intake

This adapter validates and inventories the target side of a Harvey LAB experiment before any model response or training outcome is used. It reads a pinned LAB checkout and records task identity, practice area, work type, matter documents, deliverables, and criterion-level review structure.

```bash
anarres legal lab-intake \
  --repository /path/to/anarres \
  --lab-root /path/to/harvey-labs \
  --source-revision v1.3.0 \
  --output-dir /path/to/intake
```

The command emits a compact summary and one JSONL row per task. It validates the fields needed to define a LAB-shaped target, while preserving fields that must come from later run artifacts or a supplemental legal contract.

The intake is model agnostic. Model and checkpoint identity enter with the run artifacts, not the target representation. The output is not an environment profile and contains no policy measurement, judge verdict, or downstream outcome. It cannot support a training-utility claim by itself.

## Frontier legal experiment

A complete experiment joins three records without collapsing them:

1. **Target workflow intake.** Tasks, matter documents, deliverables, rubric criteria, practice areas, and any supplemental jurisdiction or risk metadata.
2. **Starting-policy run record.** Exact model and checkpoint, harness and tools, criterion verdicts, all-pass, document coverage, artifact completion, tool use, latency, token cost, and infrastructure validity.
3. **Training intervention record.** Candidate membership, budget, seed, checkpoints, and the same held-out outcome vector after training.

This separation supports comparisons across model families while keeping the legal workflow, evaluator, and training intervention explicit.

## Source

Harvey LAB is released under the MIT License. Its task schema and evaluation methodology are documented in the [official repository](https://github.com/harveyai/harvey-labs) and [evaluation guide](https://github.com/harveyai/harvey-labs/blob/main/docs/eval-strategies.md).
