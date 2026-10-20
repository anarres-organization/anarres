"""Freeze outcome-blind candidate orderings for cyber qualification.

The output is an ordering, not an admission decision. Static licensing,
contamination, containment, oracle, no-op, and reset gates are applied in order;
the first 24 eligible entries from each declared stratum form a 48-task subset.
No replacement is allowed after warm-start measurements begin.

Protocol v2 also requires a single frozen ordering to yield two mutually
exclusive partitions: the 48-task warm-start probe subset and a target panel of
at least 246 tasks that is disjoint from the probe by exact task and, when an
identity map is supplied, by sharing any single excluding identity axis (upstream
project / fork lineage, patch-equivalence class, vulnerability class / sanitizer
signature, or fuzz-harness source). Disjointness is per-axis OR, not a
conjunction: sharing the project alone is enough to be non-disjoint. ARVO/OSS-Fuzz
provenance is recorded for audit but is not an excluding axis, since every task
shares it. Without an identity map, only exact-task disjointness is enforced and
the identity audit is reported UNRESOLVED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SALT = "anarres-cyber-qualification-v1"


def rank(family: str, task_id: str, salt: str = SALT) -> str:
    payload = f"{salt}\0{family}\0{task_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def ordered_rows(family: str, task_ids: list[str]) -> list[dict[str, str | int]]:
    rows = [
        {"task_id": task_id, "rank_sha256": rank(family, task_id)}
        for task_id in sorted(set(task_ids))
    ]
    rows.sort(key=lambda row: (str(row["rank_sha256"]), str(row["task_id"])))
    for position, row in enumerate(rows, start=1):
        row["position"] = position
    return rows


def cyber_candidates(mask_map_path: Path) -> dict[str, list[dict[str, str | int]]]:
    mapping = json.loads(mask_map_path.read_text())
    if not isinstance(mapping, dict):
        raise ValueError("CyberGym mask map must be an object")
    result: dict[str, list[dict[str, str | int]]] = {}
    for source in ("arvo", "oss-fuzz"):
        task_ids = [task_id for task_id in mapping if task_id.startswith(f"{source}:")]
        if len(task_ids) < 24:
            raise ValueError(f"CyberGym stratum {source} has fewer than 24 tasks")
        result[source] = ordered_rows("cybergym", task_ids)
    return result


def cybergym_global_ordering(mask_map_path: Path) -> list[dict[str, str | int]]:
    """One salted ordering over every CyberGym task id (not per stratum)."""
    mapping = json.loads(mask_map_path.read_text())
    if not isinstance(mapping, dict):
        raise ValueError("CyberGym mask map must be an object")
    return ordered_rows("cybergym", list(mapping))


IdentityMap = dict[str, dict[str, str]]

# A target task is non-disjoint from the probe if it shares the probe on ANY of
# these axes (per-axis OR), not only when every axis matches at once. Sharing an
# upstream project / fork lineage alone is enough to leak a codebase between the
# training pool and the target, which is exactly what protocol v2 forbids.
# `provenance` (ARVO vs OSS-Fuzz) is deliberately excluded: every task shares it,
# so using it to exclude would empty the target. It stays in the record for audit
# only. See docs/decisions/0003-cyber-identity-disjointness-per-axis.md.
EXCLUDING_AXES = (
    "project",
    "patch_equivalence_class",
    "vulnerability_class",
    "fuzz_harness",
)


def _identity_tokens(task_id: str, identity: IdentityMap | None) -> frozenset[tuple[str, str]]:
    """Per-axis collision tokens used for probe/target disjointness.

    Returns one ``(axis, value)`` token per populated excluding axis. Two tasks
    are non-disjoint iff their token sets intersect (share a value on any axis).
    An empty set means identity is unknown (or carries no excluding axis), so only
    exact-task disjointness can be enforced for that task.
    """
    if not identity:
        return frozenset()
    record = identity.get(task_id)
    if not record:
        return frozenset()
    return frozenset(
        (axis, record[axis]) for axis in EXCLUDING_AXES if record.get(axis) is not None
    )


def partition_probe_and_target(
    ordering: list[dict[str, str | int]],
    *,
    probe_size: int = 48,
    target_size: int = 256,
    target_minimum: int = 246,
    identity: IdentityMap | None = None,
) -> dict[str, object]:
    """Carve a probe subset and a disjoint target panel from one frozen ordering.

    The probe subset is the first ``probe_size`` tasks by frozen rank. The target
    panel takes subsequent tasks that collide with the probe neither by exact
    task id nor, when an identity map is supplied, by sharing any excluding
    identity axis (project / fork lineage, patch-equivalence class, vulnerability
    class, fuzz harness). The two partitions are mutually exclusive by
    construction and the probe is excluded from the target.
    """
    probe = [str(row["task_id"]) for row in ordering[:probe_size]]
    probe_ids = set(probe)
    probe_tokens: set[tuple[str, str]] = set()
    for task_id in probe:
        probe_tokens |= _identity_tokens(task_id, identity)

    target: list[str] = []
    excluded_exact: list[str] = []
    excluded_identity: list[str] = []
    for row in ordering[probe_size:]:
        task_id = str(row["task_id"])
        if task_id in probe_ids:
            excluded_exact.append(task_id)
            continue
        if _identity_tokens(task_id, identity) & probe_tokens:
            excluded_identity.append(task_id)
            continue
        target.append(task_id)
        if len(target) >= target_size:
            break

    identity_resolved = identity is not None
    audit = {
        "identity_resolved": identity_resolved,
        "probe_size": len(probe),
        "target_size": len(target),
        "target_minimum": target_minimum,
        "target_meets_minimum": len(target) >= target_minimum,
        "excluded_for_exact_collision": len(excluded_exact),
        "excluded_for_identity_collision": len(excluded_identity),
        "disjointness": (
            "exact-task and per-axis identity (shares any of "
            "project/patch-class/vuln-class/harness; provenance audit-only)"
            if identity_resolved
            else "exact-task only; identity-key disjointness UNRESOLVED, audit at materialization"
        ),
    }
    return {
        "probe": probe,
        "target": target,
        "excluded_for_identity_collision": excluded_identity,
        "audit": audit,
    }


def secbench_candidates(projects_path: Path) -> dict[str, list[dict[str, str | int]]]:
    result: dict[str, list[dict[str, str | int]]] = {}
    for source in ("v8", "sm"):
        root = projects_path / source
        task_ids = [
            f"{source}:{path.name}"
            for path in root.iterdir()
            if path.is_dir() and (path / "meta.json").is_file()
        ]
        if len(task_ids) < 24:
            raise ValueError(f"SEC-Bench Pro stratum {source} has fewer than 24 tasks")
        result[source] = ordered_rows("sec_bench_pro", task_ids)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cybergym-mask-map", type=Path, required=True)
    parser.add_argument("--cybergym-revision", required=True)
    parser.add_argument("--secbench-projects", type=Path, default=None)
    parser.add_argument("--secbench-revision", default=None)
    parser.add_argument(
        "--identity-map",
        type=Path,
        default=None,
        help="optional JSON mapping task_id -> identity record for disjointness",
    )
    parser.add_argument("--probe-size", type=int, default=48)
    parser.add_argument("--target-size", type=int, default=256)
    parser.add_argument("--target-min", type=int, default=246)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    identity: IdentityMap | None = None
    if arguments.identity_map is not None:
        identity = json.loads(arguments.identity_map.read_text())

    cybergym_ordering = cybergym_global_ordering(arguments.cybergym_mask_map)
    partitions = partition_probe_and_target(
        cybergym_ordering,
        probe_size=arguments.probe_size,
        target_size=arguments.target_size,
        target_minimum=arguments.target_min,
        identity=identity,
    )

    artifact: dict[str, object] = {
        "schema_version": "anarres.cyber-development-candidate-order.v2",
        "salt": SALT,
        "outcome_blind": True,
        "admission_rule": (
            "within each declared stratum, take the first 24 candidates that pass "
            "all pre-measurement gates; do not replace after measurement begins"
        ),
        "partition_rule": (
            "one frozen ordering yields a mutually exclusive probe subset and "
            "target panel; the probe is excluded from the target and the target is "
            "disjoint by exact task and, when an identity map is supplied, by "
            "identity key"
        ),
        "sources": {
            "cybergym": {
                "revision": arguments.cybergym_revision,
                "strata": cyber_candidates(arguments.cybergym_mask_map),
                "partitions": partitions,
            },
        },
    }
    if arguments.secbench_projects is not None:
        artifact["sources"]["sec_bench_pro"] = {  # type: ignore[index]
            "revision": arguments.secbench_revision,
            "strata": secbench_candidates(arguments.secbench_projects),
            "role": "rejected_as_target_capacity; optional external transfer",
        }
    arguments.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
