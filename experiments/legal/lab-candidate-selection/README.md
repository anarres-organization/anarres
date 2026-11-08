# Qualifying a held-out LAB environment comparison

Harvey's [Legal Agent Benchmark](https://github.com/harveyai/harvey-labs)
provides legal assignments, matter documents, rubrics, and an agent harness.
Anarres currently has one released LAB learning trajectory and a separate
three-mixture procedural legal study. Neither record identifies which of several
LAB training distributions would best improve the same starting policy on a
held-out legal target. This workstream prepares that comparison.

## Source and partition boundary

The first source audit uses the pinned LAB revision
`9e9fa7fe126103de1fceb2227b7c70bf59b67f73`. It accepts an outcome-blind
task inventory and separate probe and target panels. The auditor checks every
task hash, rejects opened panels, and excludes candidate training tasks that
share a scenario family with either panel. Tasks marked as sharing a document
corpus are also excluded from the candidate pool. Its output contains counts and
hashes, not target identities or outcomes.

```bash
python experiments/legal/lab-candidate-selection/scripts/audit_pool.py \
  --inventory /path/to/TASK_INVENTORY.jsonl \
  --probe-panel /path/to/PROBE_PANEL.json \
  --target-panel /path/to/TARGET_PANEL.json
```

The panels and candidate environments will be released with their final source
and outcome record. Until then, this auditor is a reproducible partition check,
not a claim that a candidate panel has already been trained or scored.

On the pinned 2,010-task inventory, the screen protects 128 probe tasks and 128
target tasks, then excludes 76 remaining tasks in those scenario families and
220 remaining tasks flagged as sharing a document corpus. This leaves 1,458
candidate-source tasks across 26 practice areas. The eligible membership digest
is `4f0b82789eccebf04a08c6fd6eac6c396c6c3612e9d24079e8185cb1fca15b6b`.
This is a first overlap screen. Document content, templates, and semantically
similar matters still require review before candidate training.

## Decision to test

At least three candidate distributions must share one starting checkpoint,
agent harness, verifier profile, trainer, compute budget, and held-out target.
One candidate represents the source-proportional training distribution. Others
may change practice-area or work-product exposure, with their exact membership
and sampling weights fixed after development-only policy measurements and before
any candidate training outcome. The comparison must include the source-native
practical rule and simple starting-success, cost, and uniform controls.

The target is a vector of native LAB all-pass and criterion results, practice-
area retention, document and tool behavior, reliability, and cost. A selected
environment is useful only if its improvement and guardrails justify the
measurement and training cost relative to the practical choice. Checkpoints,
rubric criteria, judge repetitions, and tasks remain nested under each trained
intervention.

## Execution gates

1. Qualify the source revision, task documents, sandbox, tools, reset behavior,
   and official judge profile. Record infrastructure failures separately from
   scientific task failures.
2. Measure candidate experience under the intended starting policy on the
   development partition. Freeze candidate memberships, the decision rule,
   uncertainty, budget, training seeds, and evaluation contract.
3. Train the minimum matched candidate arms needed to test the decision. Open
   the held-out outcomes only after predictions and the practical comparator
   are recorded. Score allocation regret, guardrail regressions, and net
   decision value.

The [official LAB tutorial](https://github.com/harveyai/harvey-labs/blob/main/docs/tutorial.md)
uses a task sandbox and two model judges for standard evaluation. A local
diagnostic scorer cannot silently replace that contract. This page records the
scientific path and source check. It does not authorize an unqualified trainer,
grader substitution, or an outcome-driven candidate revision.
