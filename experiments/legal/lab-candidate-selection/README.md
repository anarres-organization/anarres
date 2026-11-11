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
This is a first overlap screen. An exact-document check against the pinned
source tree finds 17 document blobs shared with the probe panel and three
shared with the target panel. They affect four distinct candidate tasks, which
are removed. An exact-title screen removes two more candidate tasks whose
normalized titles match target tasks. The screened bank therefore contains
1,452 tasks. The document check compares Git blob identities, and the title
check uses task metadata. Neither opens target outcomes or reports target task
IDs. All 2,010 inventory task hashes also match `task.json` at the pinned
revision. A four-word-gram screen of task instructions finds no candidate with
Jaccard similarity at or above 0.7 to either protected panel. This lexical
screen does not establish semantic independence, so similar matters and rubric
templates still require review before candidate training.

The preflight constructs three sampling distributions on this same 1,452-task
support:

| Candidate | Sampling rule | Effective task count |
| --- | --- | ---: |
| Source-proportional | Equal weight per eligible source task | 1,452 |
| Practice-area balanced | Equal total weight per represented practice area | 765 |
| Rubric-dense | Half the weight on tasks with at least 68 criteria | 1,126 |

The 68-criterion cutoff is the screened pool's upper-quartile boundary and
contains 382 tasks. Pairwise total variation from the source-proportional
distribution is 0.387 for area balancing and 0.237 for rubric density. These
rules create distinguishable candidate distributions without reading policy
outcomes. The third rule changes exposure to rubric-dense work; it does not
assume that criterion count measures task difficulty or reward quality.

```bash
python experiments/legal/lab-candidate-selection/scripts/build_candidate_bank.py \
  --inventory /path/to/TASK_INVENTORY.jsonl \
  --probe-panel /path/to/PROBE_PANEL.json \
  --target-panel /path/to/TARGET_PANEL.json \
  --source-repo /path/to/checked-out/pinned/harvey-labs \
  --output /path/outside/repository/CANDIDATE_BANK.json
```

This bank remains a metadata preflight. The frozen LAB probe panel is separate
from the candidate support. Policy-relative measurements for each candidate
must sample from that candidate's source tasks, while the target panel stays
unopened. The document-overlap and execution gates below determine whether
these preflight distributions can become training interventions.

## Decision to test

At least three candidate distributions must share one starting checkpoint,
agent harness, verifier profile, trainer, compute budget, and held-out target.
The source-proportional distribution is the practical incumbent. Area balancing
and rubric density are two alternatives. Their task support and weights are
fixed by metadata, while the predictive decision rule, uncertainty, and budget
must be fixed after development-only policy measurements and before any
candidate training outcome. The comparison also includes simple starting-
success and cost-based decision rules.

The target is a vector of native LAB all-pass and criterion results, practice-
area retention, document and tool behavior, reliability, and cost. A selected
environment is useful only if its improvement and guardrails justify the
measurement and training cost relative to the practical choice. Checkpoints,
rubric criteria, judge repetitions, and tasks remain nested under each trained
intervention.

[Harvey and Baseten](https://www.harvey.ai/blog/post-training-open-legal-agents-with-baseten-research)
report a short Qwen3.5-9B GRPO run using LAB rubric reward. This shows a viable
legal training signal, while the released aggregate does not compare matched
candidate distributions. Our pre-RL probe must use the same reward and grader
as candidate training. Held-out all-pass and criterion results are then scored
under the pinned LAB evaluation profile, with grading cost reported separately.

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

The [pinned LAB tutorial](https://github.com/harveyai/harvey-labs/blob/9e9fa7fe126103de1fceb2227b7c70bf59b67f73/docs/tutorial.md)
uses a task sandbox and two model judges for standard evaluation. A local
diagnostic scorer cannot silently replace that contract. This page records the
scientific path and source check. It does not authorize an unqualified trainer,
grader substitution, or an outcome-driven candidate revision.
