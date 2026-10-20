"""Build the project-lineage identity map for cyber qualification disjointness.

The output is a JSON object keyed by real CyberGym ``task_id`` (which aligns with
the keys of ``mask_map.json`` and therefore with the frozen ordering consumed by
``freeze_development_candidates.py``). Each record populates:

- ``project``: the canonicalized ``project_main_repo`` URL, used as the upstream
  project / fork-lineage anchor. CyberGym records the documented main repository
  per task, so tasks from the same upstream collapse to one key.
- ``provenance``: ``arvo`` or ``oss-fuzz``, derived from the task-id prefix. This
  is audit-only: it is not an excluding axis in the partitioner (every task
  shares a provenance, so excluding on it would empty the target).

``patch_equivalence_class``, ``vulnerability_class``, and ``fuzz_harness`` are
intentionally **left absent**: they are not derivable from ``tasks.json`` alone
(they need the per-task patch/error artifacts), and the partitioner treats an
absent axis as non-excluding rather than fabricating a value. The resulting map
therefore resolves disjointness at the project-lineage level only; populating the
remaining axes is follow-up work once the per-task artifacts are materialized.

This script reads only task metadata; it needs no GPU, container, or model.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


def canon_repo(url: str) -> str:
    """Canonicalize a repo URL to a stable fork-lineage key.

    Lowercases, strips the scheme (``https://``/``git://``/``ssh://``/``git@``),
    normalizes an ``scp``-style ``host:owner/repo`` to ``host/owner/repo``, and
    drops a trailing ``.git`` and trailing slashes.
    """
    u = (url or "").strip().lower()
    u = re.sub(r"^git\+", "", u)
    u = re.sub(r"^(https?://|git://|ssh://|git@)", "", u)
    u = u.replace(":", "/", 1)
    u = re.sub(r"/+$", "", u)
    if u.endswith(".git"):
        u = u[:-4]
    return u


def build(tasks: list[dict]) -> dict[str, dict[str, str]]:
    idmap: dict[str, dict[str, str]] = {}
    for task in tasks:
        task_id = task["task_id"]
        repo = canon_repo(task.get("project_main_repo") or "")
        project = repo or ("name:" + (task.get("project_name") or "unknown").strip().lower())
        idmap[task_id] = {"project": project, "provenance": task_id.split(":", 1)[0]}
    return idmap


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True, help="CyberGym tasks.json")
    parser.add_argument("--output", type=Path, required=True, help="identity map JSON to write")
    arguments = parser.parse_args()

    tasks = json.loads(arguments.tasks.read_text())
    idmap = build(tasks)
    arguments.output.write_text(json.dumps(idmap, indent=2, sort_keys=True) + "\n")

    projects = collections.Counter(record["project"] for record in idmap.values())
    provenance = collections.Counter(record["provenance"] for record in idmap.values())
    print(f"tasks: {len(idmap)}")
    print(f"distinct projects: {len(projects)}")
    print(f"top project sizes: {projects.most_common(5)}")
    print(f"provenance split: {dict(provenance)}")


if __name__ == "__main__":
    main()
