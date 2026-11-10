# Credential-safe task runner

`run_task.py` preserves the QF-Bench task and verifier contract while keeping
model credentials outside benchmark containers. It stages only the pinned
instruction, task data, an empty output directory, and an optional candidate
resource. Tests and reference solutions never enter the agent workspace.

The host Codex CLI writes task artifacts into the staged output directory.
Automatic approval retains the CLI's workspace-write sandbox for generated
commands.
After the agent exits, the runner copies only those artifacts into a fresh
task image and invokes the source-native verifier. QF-Bench's verifier
bootstrap retains its normal network access, while the agent receives no
benchmark network resource. Execution events, hashes, wall time, verifier
output, and artifact hashes are stored beside the workspace in an `.anarres`
record directory.

Prepare, execute, and verify one frozen task with:

```bash
python run_task.py \
  --qfbench-root /path/to/QuantitativeFinance-Bench \
  --task-id historical-var-data-prep \
  --stage /path/to/stage \
  run
```

Pass `--candidate /path/to/SKILL.md` to evaluate a frozen candidate resource.
The source repository must be at the commit recorded in `SOURCE.json`, and the
task must match the hashes in `TASK_SPLIT.json`.

This release opens only the two round-one development tasks. Target, protected,
and round-two tasks remain sealed until a versioned authorization records the
preceding decision and opens the next stage.

Before any model execution, the bridge was checked in both directions on the
development smoke task. The source oracle output receives reward 1.0, and an
empty output directory receives reward 0.0.
