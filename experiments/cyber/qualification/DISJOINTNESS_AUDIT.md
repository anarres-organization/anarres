# Probe/target disjointness audit (full identity)

This records the resolved run of the probe/target partition with a supplied
identity map, using the per-axis OR partitioner (ADR 0003). It flips the identity
audit from UNRESOLVED (exact-task only) to resolved on all four excluding axes
(project / fork lineage, patch-equivalence class, vulnerability class /
sanitizer signature, fuzz harness). It is a measurement-design artifact;
`execution_authorized` stays `false` and nothing here authorizes RL.

## Method

1. `build_identity_map.py --tasks tasks.json --data-dir data/ --output
   identity_map.json` builds a map keyed by real `task_id`:
   - `project`: canonicalized `project_main_repo` (upstream/fork-lineage anchor).
   - `provenance`: `arvo`/`oss-fuzz` (audit-only; not an excluding axis).
   - `patch_equivalence_class`: hash of the normalized `patch.diff` (blob
     indices and hunk line numbers stripped, context dropped, changed lines and
     paths kept) — collapses fixes identical modulo line numbers.
   - `vulnerability_class`: sanitizer + crash kind + `DEDUP_TOKEN` from
     `error.txt` (the canonical crash-dedup signature).
   - `fuzz_harness`: the fuzz target (`FUZZER=`/`run_fuzzer`/`/out/<name>`/the
     `LLVMFuzzerTestOneInput` source frame).

   An axis is left **absent** (non-excluding) wherever its source cannot be
   parsed, rather than fabricated. The per-task `error.txt`/`patch.diff` were
   obtained with a scoped `git lfs pull --include="data/**/error.txt,
   data/**/patch.diff"` (a few MB of text, not the image data).
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
| `identity_map.full.json` | `31a0126fa3e5450fd076a21096c5d323fa706ba456b54ff67ed51841fa350b3c` |
| `partition.full.json` | `d75d4723ef42a52d8ddf8d40ff682b036d8006f8eb2022409054d4707330ea38` |

An earlier project-lineage-only map (`41e34973…`, partition `0b0b363d…`) was
superseded by the full-axis map above; it excluded 311 tasks on project alone.

The identity map (reproducible from the inputs above and
`build_identity_map.py`, verified to reproduce bit-for-bit to the hash shown) and
the partition are generated artifacts and are kept out of Git per repository
hygiene; regenerate from the pinned inputs rather than committing them.

## Axis coverage (identity map, 1507 tasks)

| axis | populated | distinct |
| --- | ---: | ---: |
| `project` | 1507/1507 | 188 |
| `patch_equivalence_class` | 1507/1507 | 1476 |
| `vulnerability_class` | 1505/1507 | 1351 |
| `fuzz_harness` | 1507/1507 | 622 |

Two tasks have no parseable crash signature, so their `vulnerability_class` is
absent (non-excluding) rather than fabricated.

## Result

| quantity | value |
| --- | ---: |
| tasks in pool | 1507 |
| probe tasks | 48 |
| target tasks | 256 |
| excluded for identity (any axis) | 320 |
| target meets minimum (≥246) | **yes** |

Per-axis probe/target overlap (must be 0 on every axis):

| axis | probe values | target values | overlap |
| --- | ---: | ---: | ---: |
| `project` | 38 | 101 | 0 |
| `patch_equivalence_class` | 48 | 255 | 0 |
| `vulnerability_class` | 47 | 244 | 0 |
| `fuzz_harness` | 44 | 183 | 0 |

The partition is disjoint by exact task and by every excluding axis. Adding the
patch/vuln/harness axes on top of project lineage removes only 9 further
candidates (320 vs 311), so the fine signatures catch true cross-entry
duplicates — the same fix, crash, or harness appearing under a different project
— without starving the target, which still clears the ≥246 floor at 256.

## Scope and caveats

- **Full four-axis disjointness is resolved.** The partition is disjoint on
  project / fork lineage, patch-equivalence class, vulnerability class /
  sanitizer signature, and fuzz harness; provenance is recorded for audit only.
- **Signature granularity.** `patch_equivalence_class` and `vulnerability_class`
  are near-unique (1476 and 1351 distinct over 1507), so in practice they exclude
  only genuine duplicates; `fuzz_harness` is coarser (622 distinct) and does real
  cross-project work. If a future re-run with different probe tasks pushes the
  target below 246, treat it as an honest failure (add candidates or refine a
  signature), never loosen the axes.
- **Provenance imbalance.** The pool is 1368 ARVO / 139 OSS-Fuzz; the target is
  not stratified by provenance here, which is acceptable because provenance is
  not an identity axis, but worth noting for downstream panel composition.
