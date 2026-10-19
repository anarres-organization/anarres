# Cyber benchmark qualification

## Decision to make

Select at most one primary family for the first cyber utility pilot. The
qualification comparison is CyberGym versus SEC-Bench Pro. ExploitBench is a
graded-headroom diagnostic, not a third integration candidate.

This decision is intentionally separate from external-target selection.
ExploitGym is the priority public frontier-transfer target; CyberGym-E2E and a
recent or sequestered vulnerability panel remain bounded investigations. None is
added to the initial bakeoff workload.

Qualification is development-only. It cannot inspect RL outcomes, redesign the
candidate panel after seeing downstream performance, or authorize cyber RL by
itself.

## Frozen order of work

1. Pin the upstream repositories and task-data revisions in
   `source-registry.yaml`.
2. Confirm current open-weight frontier relevance using
   `FRONTIER_RELEVANCE_AUDIT.md`.
3. Audit code and task-data licenses separately.
4. Generate the outcome-blind candidate ordering from the pinned sources with
   `freeze_development_candidates.py`, record its content hash in the execution
   manifest, and materialize the development subset from that frozen artifact.
5. Verify containment, agent-visible files, network policy, reset behavior, and
   grader isolation without running a model.
6. Run oracle, no-op, and repeated-reset checks on every candidate fixture.
7. Run the same warm-start agent contract on both families and record success,
   graded progress where available, cost, latency, and infrastructure failures.
8. Estimate the minimum detectable downstream utility effect and the cost of a
   four-to-six-environment, two-seed pilot.
9. Apply the frozen decision table and either select one family or stop.

After a family passes, run a separate external-target feasibility check. That
check cannot change the primary-family qualification outcomes and cannot expose
external target tasks to probing or training.

## Preliminary official-source audit

| Criterion | CyberGym | SEC-Bench Pro |
| --- | --- | --- |
| Public code license | Apache-2.0 | MIT |
| Task structure | Real vulnerable projects with vulnerable/fixed verification | Verified V8, SpiderMonkey, and Linux cases with reproduction and grading artifacts |
| Primary outcome | One designated final PoC succeeds on the vulnerable build and fails on the fixed build | Strict verified outcome; grader and infrastructure errors remain distinct |
| Initial storage signal | Approximately 240 GB for benchmark data; dynamic server data can be substantially larger | Per-project images and artifacts; Linux additionally requires KVM-capable infrastructure |
| Isolation requirement | Local-only submission service, restricted egress, fixed build hidden from the agent | Network-restricted agent; trusted grading outside the agent sandbox |
| First-pilot concern | Recent public contamination and cross-benchmark-overlap reports require an independent identity audit | Linux adds privileged KVM and nested-virtualization complexity; begin qualification with V8 or SpiderMonkey |
| Qualification status | Static audit complete; fixture execution pending | Static audit complete; fixture execution pending |

The table records repository claims and risks to test. It is not a benchmark
selection result.

## Decision table

The values below are frozen in `qualification-protocol.v1.json`. They may be
changed only by issuing a new protocol version before any warm-start outcome is
examined.

| Gate | Frozen statistic | Threshold | Required |
| --- | --- | --- | --- |
| Warm-start headroom | Strict success or deterministic graded progress | Strict success in [5%, 80%], or at least 20% non-extreme groups over at least 3 deterministic levels | Yes |
| Mixed-group availability | Complete valid groups with nonzero variation | At least 8 groups and at least 20% | Yes |
| Probe reliability | Agreement across two independent \(G=8\) views | \(\rho\) symmetric relative difference at most 20%; \(H\) and mixed fraction absolute difference at most 0.10 | Yes |
| Fixture validity | Oracle pass, no-op rejection, repeated-reset agreement | 100% admitted fixtures | Yes |
| Infrastructure reliability | Typed infrastructure-failure fraction | At most 5% | Yes |
| Contamination | Exact and near-duplicate overlap with training and target partitions | No unresolved overlap | Yes |
| Containment | Egress, grader visibility, fixed-build visibility, and secret checks | No unresolved failure | Yes |
| Pilot feasibility | Projected wall time, storage, and valid-rollout cost | At most 1,536 warm-start rollouts, 96 fixtures, 1 TiB retained storage, 5 engineering days, and 7 elapsed days | Yes |

## Selection rule

Select the family that passes every required gate and offers the higher expected
information about environment-dependent utility per unit of measured pilot cost.
If both pass with practically indistinguishable information and cost, prefer the
family requiring less new infrastructure. If neither passes, do not launch RL.

The selection record must preserve failed fixtures and rejection reasons. A
failed family may remain an external benchmark, but it cannot be silently
modified into the primary pilot target.

## Explicit non-goals

- supporting every cyber benchmark;
- building a shared cyber range or new scheduler;
- maximizing leaderboard performance;
- treating public benchmark difficulty as training utility;
- fitting a general cyber forecasting law from the four-to-six-environment pilot;
- running exploit code outside authorized, isolated benchmark fixtures.

## Outputs

Qualification produces only the following artifacts:

- completed source and license registry;
- frontier-relevance audit and frozen development-candidate ordering;
- frozen feasibility budget and numerical gates;
- fixture and contamination manifests;
- oracle, no-op, reset, and containment results;
- warm-start measurement and cost summary;
- one signed selection or stop decision.

No additional benchmark integration is on the critical path.
