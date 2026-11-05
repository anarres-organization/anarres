from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".rst", ".txt"}
CONTRAST_PATTERNS = (
    re.compile(r"\b(?:It|This|That) is not\b"),
    re.compile(r"\bnot (?:just|merely|only)\b", re.IGNORECASE),
)


def tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = result.stdout.decode().split("\0")
    return [
        ROOT / path
        for path in paths
        if Path(path).suffix in TEXT_SUFFIXES and not path.startswith(".uv-cache/")
    ]


def prose_lines(path: Path):
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def main() -> int:
    failures: list[str] = []
    for path in tracked_text_files():
        for number, line in prose_lines(path):
            relative = path.relative_to(ROOT)
            if "—" in line:
                failures.append(f"{relative}:{number}: replace the em dash")
            for pattern in CONTRAST_PATTERNS:
                if pattern.search(line):
                    failures.append(
                        f"{relative}:{number}: state the claim directly "
                        "instead of using contrast framing"
                    )
            if re.match(r"\s*(?:[-*]|\d+\.)\s+.*;\s*$", line):
                failures.append(f"{relative}:{number}: remove the list-ending semicolon")

    if failures:
        print("Prose style check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Prose style check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
