"""Build the identity map for cyber qualification probe/target disjointness.

The output is a JSON object keyed by real CyberGym ``task_id`` (which aligns with
the keys of ``mask_map.json`` and therefore the frozen ordering consumed by
``freeze_development_candidates.py``). Each record may populate these axes:

- ``project``: canonicalized ``project_main_repo`` (the upstream / fork-lineage
  anchor). Always populated from task metadata.
- ``provenance``: ``arvo`` or ``oss-fuzz`` from the task-id prefix. Audit-only;
  the partitioner does not exclude on it (every task shares a provenance).
- ``patch_equivalence_class``: a hash of the normalized ``patch.diff`` (blob
  indices and hunk line numbers stripped, context lines dropped, changed lines
  and file paths kept), so two tasks whose fix is identical modulo line numbers
  collapse to one class. Populated only with ``--data-dir``.
- ``vulnerability_class``: a crash signature from ``error.txt`` --- the sanitizer
  and crash kind plus the OSS-Fuzz/ARVO ``DEDUP_TOKEN`` when present (the
  canonical crash-dedup identity). Populated only with ``--data-dir``.
- ``fuzz_harness``: the fuzz target that produced the crash (``FUZZER=``/
  ``run_fuzzer``/``/out/<name>``/the ``LLVMFuzzerTestOneInput`` source frame).
  Populated only with ``--data-dir``.

An axis is **left absent** whenever its source cannot be parsed, rather than
fabricated; the partitioner treats an absent axis as non-excluding. Without
``--data-dir`` only the project (and audit-only provenance) axes are populated.

This script reads only task metadata and small text artifacts; it needs no GPU,
container, or model.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

_SCHEME = re.compile(r"^(https?://|git://|ssh://|git@)")
_SANITIZER = re.compile(r"(?:WARNING|ERROR): (\w*Sanitizer): ([^\n]+)")
_LIBFUZZER = re.compile(r"ERROR: libFuzzer: ([^\n]+)")
_DEDUP = re.compile(r"^DEDUP_TOKEN:\s*(\S+)", re.MULTILINE)
_HARNESS_PATTERNS = (
    re.compile(r"^\+?\s*FUZZER=(\S+)", re.MULTILINE),
    re.compile(r"\brun_fuzzer\s+(\S+)"),
    re.compile(r"(/out/[A-Za-z0-9_.+-]+)"),
    re.compile(r"in LLVMFuzzerTestOneInput\s+(/\S+?\.(?:cc|cpp|cxx|c))\b"),
)


def canon_repo(url: str) -> str:
    """Canonicalize a repo URL to a stable fork-lineage key."""
    u = (url or "").strip().lower()
    u = re.sub(r"^git\+", "", u)
    u = _SCHEME.sub("", u)
    u = u.replace(":", "/", 1)  # git@github.com:owner/repo -> github.com/owner/repo
    u = re.sub(r"/+$", "", u)
    if u.endswith(".git"):
        u = u[:-4]
    return u


def patch_equivalence_class(diff_text: str) -> str | None:
    """Hash a patch normalized to be robust to blob indices and line numbers."""
    kept: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("index "):
            continue
        if line.startswith("@@"):
            kept.append("@@")
            continue
        if line.startswith(("--- ", "+++ ")):
            kept.append(line.split("\t")[0].rstrip())
            continue
        if line.startswith(("diff --git", "+", "-")):
            kept.append(line.rstrip())
    body = "\n".join(kept).strip()
    if not body:
        return None
    return "patch:" + hashlib.sha256(body.encode()).hexdigest()[:16]


def vulnerability_class(error_text: str) -> str | None:
    """Derive a crash signature: sanitizer + crash kind (+ DEDUP_TOKEN)."""
    dedup_match = _DEDUP.search(error_text)
    dedup = dedup_match.group(1) if dedup_match else None
    san_match = _SANITIZER.search(error_text)
    if san_match:
        sanitizer = san_match.group(1).lower()
        kind = san_match.group(2).strip().split(" on ")[0].strip().split()[0]
        base = f"{sanitizer}:{kind}"
    else:
        lf_match = _LIBFUZZER.search(error_text)
        if lf_match:
            base = "libfuzzer:" + lf_match.group(1).strip().split()[0]
        elif dedup:
            base = "crash"
        else:
            return None
    return f"{base}:{dedup}" if dedup else base


def fuzz_harness(error_text: str) -> str | None:
    """Identify the fuzz target that produced the crash."""
    for pattern in _HARNESS_PATTERNS:
        match = pattern.search(error_text)
        if match:
            name = match.group(1).rsplit("/", 1)[-1]
            name = re.sub(r"\.(cc|cpp|c|cxx)$", "", name)
            if name and name not in {"poc", "testcase"}:
                return "harness:" + name
    return None


def _read(path: Path) -> str | None:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return None
    if not text or text.startswith("version https://git-lfs"):
        return None  # empty or an unfetched LFS pointer
    return text


def build(tasks: list[dict], data_dir: Path | None) -> dict[str, dict[str, str]]:
    idmap: dict[str, dict[str, str]] = {}
    for task in tasks:
        task_id = task["task_id"]
        source, number = task_id.split(":", 1)
        repo = canon_repo(task.get("project_main_repo") or "")
        record = {
            "project": repo or ("name:" + (task.get("project_name") or "unknown").strip().lower()),
            "provenance": source,
        }
        if data_dir is not None:
            task_dir = data_dir / source / number
            diff = _read(task_dir / "patch.diff")
            error = _read(task_dir / "error.txt")
            if diff and (value := patch_equivalence_class(diff)):
                record["patch_equivalence_class"] = value
            if error and (value := vulnerability_class(error)):
                record["vulnerability_class"] = value
            if error and (value := fuzz_harness(error)):
                record["fuzz_harness"] = value
        idmap[task_id] = record
    return idmap


def _coverage(idmap: dict[str, dict[str, str]]) -> None:
    axes = ("project", "patch_equivalence_class", "vulnerability_class", "fuzz_harness")
    total = len(idmap)
    for axis in axes:
        present = sum(1 for r in idmap.values() if axis in r)
        distinct = len({r[axis] for r in idmap.values() if axis in r})
        print(f"  {axis}: {present}/{total} populated, {distinct} distinct")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True, help="CyberGym tasks.json")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="CyberGym data/ dir with per-task patch.diff/error.txt (enables the extra axes)",
    )
    parser.add_argument("--output", type=Path, required=True, help="identity map JSON to write")
    arguments = parser.parse_args()

    tasks = json.loads(arguments.tasks.read_text())
    idmap = build(tasks, arguments.data_dir)
    arguments.output.write_text(json.dumps(idmap, indent=2, sort_keys=True) + "\n")

    print(f"tasks: {len(idmap)}")
    _coverage(idmap)
    provenance = collections.Counter(record["provenance"] for record in idmap.values())
    print(f"provenance split: {dict(provenance)}")


if __name__ == "__main__":
    main()
