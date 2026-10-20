# Probe/target disjointness audit (project-lineage)

This records the first resolved run of the probe/target partition with a supplied
identity map. It flips the identity audit from UNRESOLVED (exact-task only) to
resolved at the **project-lineage** level, using the per-axis OR partitioner
(ADR 0003). It is a measurement-design artifact; `execution_authorized` stays
`false` and nothing here authorizes RL.

## Method

1. `build_identity_map.py --tasks tasks.json --output identity_map.json` builds a
   map keyed by real `task_id`, populating `project` (canonicalized
   `project_main_repo`, the upstream/fork-lineage anchor) and `provenance`
   (`arvo`/`oss-fuzz`, audit-only). `patch_equivalence_class`,
   `vulnerability_class`, and `fuzz_harness` are **absent** — not derivable from
   task metadata without per-task artifacts, and the partitioner treats an absent
   axis as non-excluding rather than fabricating one.
2. `freeze_development_candidates.py --cybergym-mask-map mask_map.json
   --identity-map identity_map.json --probe-size 48 --target-size 256
   --target-min 246` partitions the single frozen ordering.

## Inputs (content-addressed)

| artifact | sha256 |
| --- | --- |
| CyberGym `tasks.json` (1507 tasks) | `9cea452cc1e1a3703e0f60c2dfc8642430aab9f50433f976581509de58c7048f` |
| CyberGym `mask_map.json` | `04ec3f9037ebc3da64821302eeb71c304e799ba1f7a88e09ba4404b4a8058448` |
| CyberGym code revision | `c6fe2027d39471375920b92cf1025e23a99ffda5` |

## Outputs (content-addressed, retained on the materialization host, not in Git)

| artifact | sha256 |
| --- | --- |
| `identity_map.project_lineage.json` | `41e34973b1ab7bd1e2904cd959cb41edf01bbba709dc177bd81b633ffcafe458` |
| `partition.project_lineage.json` | `0b0b363d458390e7462c286d74b1e21721074123224c735c59676088012d3743` |

The identity map (reproducible from the inputs above and
`build_identity_map.py`, verified to reproduce bit-for-bit to the hash shown) and
the partition are generated artifacts and are kept out of Git per repository
hygiene; regenerate from the pinned inputs rather than committing them.

## Result

| quantity | value |
| --- | ---: |
| tasks in pool | 1507 |
| distinct projects | 188 |
| probe tasks | 48 |
| distinct probe projects | 38 |
| target tasks | 256 |
| distinct target projects | 101 |
| excluded for identity (shared project) | 311 |
| probe∩target project overlap | 0 |
| target meets minimum (≥246) | **yes** |

The partition is disjoint by exact task and by project/fork lineage: the 48-task
probe spans 38 projects, the 256-task target spans a disjoint 101 projects, and
311 same-project tasks are held out of the target. The target clears the ≥246
floor with margin, so project-lineage disjointness does not starve the target at
this probe size.

## Scope and caveats

- **Resolved at the project-lineage axis only.** The `identity_resolved` flag in
  the partition audit means an identity map was supplied; here only `project`
  (plus audit-only `provenance`) is populated. Patch-equivalence-class,
  vulnerability-class/sanitizer-signature, and fuzz-harness disjointness are
  **not yet enforced** — those axes are absent and therefore non-excluding.
  Project lineage is the dominant leak vector (shared codebase), so this closes
  the main confound, but the full v2 standard is not yet met.
- **Next.** Materialize the per-task patch/error artifacts, derive the remaining
  axes, and re-run. Adding axes can only remove more target candidates, so
  re-check `target_meets_minimum`; if a coarse axis pushes the target below 246,
  treat it as an honest failure (add candidates or use a finer signature), never
  loosen the axes.
