"""Screen exact document reuse against protected LAB panels at a pinned revision."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from pathlib import Path

REVISION = "9e9fa7fe126103de1fceb2227b7c70bf59b67f73"


def git_output(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.PIPE).strip()


def verify_task_hashes(repo: Path, task_hashes: dict[str, str], revision: str = REVISION) -> int:
    """Match the inventory to a checkout of the pinned task JSON files."""
    if not repo.is_dir():
        raise ValueError("pinned source repository is unavailable")
    if git_output(repo, "rev-parse", "HEAD").decode() != revision:
        raise ValueError("source checkout is not at the pinned LAB revision")
    for task_id, expected in task_hashes.items():
        if not task_id or any(part in ("", ".", "..") for part in task_id.split("/")):
            raise ValueError("invalid source task identity")
        path = repo / "tasks" / task_id / "task.json"
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("source task JSON differs from the inventory")
    return len(task_hashes)


def screen_exact_titles(
    repo: Path, eligible: list[dict], probe: set[str], target: set[str]
) -> tuple[list[dict], dict]:
    """Exclude candidates sharing a normalized title with a protected task."""

    def title(task_id: str) -> str:
        task = json.loads((repo / "tasks" / task_id / "task.json").read_text())
        value = task.get("title")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("source task has no title")
        return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()

    probe_titles = {title(task_id) for task_id in probe}
    target_titles = {title(task_id) for task_id in target}
    probe_matches = {row["task_id"] for row in eligible if title(row["task_id"]) in probe_titles}
    target_matches = {row["task_id"] for row in eligible if title(row["task_id"]) in target_titles}
    excluded = probe_matches | target_matches
    return [row for row in eligible if row["task_id"] not in excluded], {
        "exact_title_matches_with_probe": len(probe_matches),
        "exact_title_matches_with_target": len(target_matches),
        "excluded_candidate_tasks": len(excluded),
        "remaining_candidate_tasks": len(eligible) - len(excluded),
        "outcomes_read": False,
    }


def audit_instruction_overlap(
    repo: Path, eligible: list[dict], probe: set[str], target: set[str]
) -> dict:
    """Count close instruction templates without reporting protected task identities."""

    def grams(task_id: str) -> set[tuple[str, ...]]:
        task = json.loads((repo / "tasks" / task_id / "task.json").read_text())
        instructions = task.get("instructions")
        if not isinstance(instructions, str):
            raise ValueError("source task has no instructions")
        words = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", instructions).casefold())
        return {tuple(words[i : i + 4]) for i in range(max(0, len(words) - 3))}

    candidate_grams = {row["task_id"]: grams(row["task_id"]) for row in eligible}
    result = {}
    for name, protected in (("probe", probe), ("target", target)):
        protected_grams = {task_id: grams(task_id) for task_id in protected}
        index: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for task_id, features in protected_grams.items():
            for feature in features:
                index[feature].add(task_id)
        best_scores = []
        for features in candidate_grams.values():
            related = set().union(*(index[feature] for feature in features)) if features else set()
            best_scores.append(
                max(
                    (
                        len(features & protected_grams[task_id])
                        / len(features | protected_grams[task_id])
                        for task_id in related
                    ),
                    default=0.0,
                )
            )
        result[name] = {
            "maximum_instruction_4gram_jaccard": max(best_scores, default=0.0),
            "candidate_tasks_at_or_above_0_5": sum(score >= 0.5 for score in best_scores),
            "candidate_tasks_at_or_above_0_7": sum(score >= 0.7 for score in best_scores),
        }
    result["outcomes_read"] = False
    return result


def screen_document_blobs(
    repo: Path,
    eligible: list[dict],
    probe: set[str],
    target: set[str],
    revision: str = REVISION,
) -> tuple[list[dict], dict]:
    """Exclude candidate tasks sharing an exact document blob with either panel."""
    if not repo.is_dir():
        raise ValueError("pinned source repository is unavailable")
    if git_output(repo, "rev-parse", f"{revision}^{{commit}}").decode() != revision:
        raise ValueError("source revision differs from the pinned LAB revision")

    eligible_ids = {row["task_id"] for row in eligible}
    if len(eligible_ids) != len(eligible):
        raise ValueError("duplicate candidate task identity")
    groups = {task_id: "eligible" for task_id in eligible_ids}
    groups.update({task_id: "probe" for task_id in probe})
    groups.update({task_id: "target" for task_id in target})
    if len(groups) != len(eligible_ids) + len(probe) + len(target):
        raise ValueError("candidate and protected task identities overlap")

    raw = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", revision, "tasks"],
        cwd=repo,
        stderr=subprocess.PIPE,
    )
    document_tasks: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    task_json_ids: set[str] = set()
    document_count = 0
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, path_bytes = item.split(b"\t", 1)
        _mode, kind, blob = metadata.split()
        if kind != b"blob":
            continue
        path = path_bytes.decode("utf-8")
        if not path.startswith("tasks/"):
            continue
        if path.endswith("/task.json"):
            task_json_ids.add(path.removeprefix("tasks/").removesuffix("/task.json"))
        if "/documents/" not in path:
            continue
        task_id = path.removeprefix("tasks/").split("/documents/", 1)[0]
        group = groups.get(task_id)
        if group:
            document_tasks[blob.decode()][group].add(task_id)
            document_count += 1

    if set(groups) - task_json_ids:
        raise ValueError("candidate or protected task absent from pinned source tree")
    target_collisions = {
        task_id
        for task_groups in document_tasks.values()
        if task_groups["target"]
        for task_id in task_groups["eligible"]
    }
    probe_collisions = {
        task_id
        for task_groups in document_tasks.values()
        if task_groups["probe"]
        for task_id in task_groups["eligible"]
    }
    excluded = target_collisions | probe_collisions
    summary = {
        "source_revision": revision,
        "scanned_document_files": document_count,
        "exact_blob_collisions_with_target": sum(
            bool(task_groups["target"] and task_groups["eligible"])
            for task_groups in document_tasks.values()
        ),
        "exact_blob_collisions_with_probe": sum(
            bool(task_groups["probe"] and task_groups["eligible"])
            for task_groups in document_tasks.values()
        ),
        "excluded_candidate_tasks": len(excluded),
        "remaining_candidate_tasks": len(eligible) - len(excluded),
        "outcomes_read": False,
    }
    return [row for row in eligible if row["task_id"] not in excluded], summary
