# ADR 0003: Cyber probe/target disjointness is per-axis, not conjunctive

- Status: accepted
- Date: 2026-10-19

## Context

The cyber qualification protocol (v2) uses CyberGym as both the in-domain
training pool and the isolated target, split from one frozen ordering into a
48-task warm-start probe and a target panel of at least 246 tasks. The split is
only valid if the two partitions are genuinely independent: the protocol's
disjointness *standard* lists upstream project / fork lineage, patch-equivalence
class, vulnerability class / sanitizer signature, fuzz-harness source, and
ARVO/OSS-Fuzz provenance.

The partitioner in `experiments/cyber/qualification/freeze_development_candidates.py`
built a single collision *key* as the tuple of all five axes, so a target task
was excluded only when it matched a probe task on **every** axis at once. Two
different bugs in the same upstream project (e.g. two `libxml2` tasks) have
different vulnerability classes, so their tuples differed and the target task was
admitted — placing the same codebase on both sides of the split. That is the
train/test-by-project leak protocol v2 was written to eliminate. The existing
unit tests only populated the `project` field, so the conjunction degenerated to
a project-only key and the defect was not exercised.

## Decision

Disjointness is enforced **per axis with OR semantics**: a target task is
non-disjoint from the probe if it shares the probe's value on *any single*
excluding axis. The excluding axes are `project`, `patch_equivalence_class`,
`vulnerability_class`, and `fuzz_harness`. `provenance` (ARVO vs OSS-Fuzz) is
recorded in the identity map for audit but is **not** an excluding axis: every
task shares it, so excluding on it would empty the target.

Implemented by replacing the single tuple key `_identity_key` with
`_identity_tokens`, which emits one `(axis, value)` token per populated excluding
axis; the target excludes any task whose token set intersects the union of the
probe's tokens. Regression tests cover a shared project with differing
vulnerability class (the leak), a shared patch class across distinct projects,
and provenance being non-excluding.

This is a bug fix that brings the implementation in line with the already-frozen
v2 disjointness standard; it does not change that standard. No probe/target
partition has been materialized yet, so no frozen artifact is invalidated.

## Consequences

The partition is now stricter whenever an identity map carries more than the
project axis, so more target candidates are excluded. Coarse axes
(`vulnerability_class`, `fuzz_harness`) can over-prune and push the target below
246; the partitioner already reports `target_meets_minimum`, and materialization
must treat an unmet minimum as an honest failure — add candidates, use a finer
sanitizer signature in place of a coarse class, or reconsider the target — never
loosen the axes to pass. The identity map must populate the axes it intends to
enforce; absent axes simply do not exclude, and a task with no excluding axes
falls back to exact-task disjointness only.
