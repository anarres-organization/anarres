# Static source feasibility audit

Date: 2026-10-17

This audit reads pinned public source trees. It does not download task images,
execute vulnerability artifacts, start services, or measure model performance.

## CyberGym

- Pinned code revision: `c6fe2027d39471375920b92cf1025e23a99ffda5`.
- The code repository is Apache-2.0; task-level upstream licenses still require
  an identity-level audit.
- The public mask maps 1,507 task identities.
- The published benchmark data is approximately 240 GB. The complete dynamic
  server data can be much larger, so qualification must use an outcome-blind
  bounded subset rather than materializing the full collection.
- The official harness separates vulnerable and fixed execution, requires the
  fixed build to remain hidden from the agent, and supports network-disabled
  verification containers.
- The submission service must remain locally reachable only. Its presence is a
  containment gate, not an ordinary web-service deployment task.
- A recent public issue reports overlap with open training data and SEC-Bench.
  The report is not treated as ground truth; it establishes a required
  independent bug/fix identity audit before partitioning.

## SEC-Bench Pro

- Pinned code revision: `da80928ee20dc417ca6a068a1213e1d9d279df20`.
- The code repository is MIT; upstream task licenses still require an
  identity-level audit.
- The pinned source contains metadata for 103 V8, 104 SpiderMonkey, and 137 Linux
  cases.
- V8 and SpiderMonkey expose bounded Docker grading paths and record grader
  errors separately from verified scientific outcomes.
- The Linux path requires privileged KVM-capable execution and is excluded from
  the first qualification pass.
- The official harness already records pinned image identities, input digests,
  timeouts, infrastructure outcomes, and aggregate grading summaries. Those
  fields should be adapted into the shared Anarres metadata contract rather than
  replaced by a new cyber-specific orchestration system.

## Current decision

Both candidates remain eligible for bounded fixture qualification. CyberGym has
the larger task reservoir but a more substantial identity and storage audit.
SEC-Bench Pro has stronger in-repository case metadata and bounded JavaScript
paths, but each JavaScript engine alone is too small for the preferred 256-task
isolated target. The qualification stage must therefore resolve target-panel
capacity as well as warm-start signal and cost.

No benchmark has been selected and no execution is authorized by this audit.
