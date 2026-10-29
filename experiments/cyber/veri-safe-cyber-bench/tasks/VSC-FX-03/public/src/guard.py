# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Filesystem access helpers with a built-in safety net.

Every read, write and directory listing done on behalf of a user goes through
this module. The functions re-check the real location of the path against the
user's folder and stop the program with exit code 86 if it lies outside. The
command layer is expected to have rejected such requests long before this
point, so the check should never fire in a correct build.
"""

import os

INVARIANT_EXIT = 86


def _violation(action):
    import sys

    sys.stdout.flush()
    sys.stderr.write("INVARIANT: " + action + " outside user root\n")
    sys.stderr.flush()
    raise SystemExit(INVARIANT_EXIT)


def _checked(path, root, action):
    real = os.path.realpath(path)
    if os.path.commonpath([real, root]) != root:
        _violation(action)
    return real


def read_bytes(path, root):
    real = _checked(path, root, "read of file")
    with open(real, "rb") as handle:
        return handle.read()


def write_bytes(path, root, data):
    real = _checked(path, root, "write of file")
    with open(real, "wb") as handle:
        handle.write(data)


def make_dir(path, root):
    real = _checked(path, root, "creation of folder")
    os.makedirs(real, exist_ok=True)


def list_dir(path, root):
    """Return sorted (name, kind) pairs; kind is 'dir', 'link' or 'file'."""
    real = _checked(path, root, "listing of folder")
    found = []
    with os.scandir(real) as entries:
        for entry in entries:
            if entry.is_symlink():
                kind = "link"
            elif entry.is_dir(follow_symlinks=False):
                kind = "dir"
            else:
                kind = "file"
            found.append((entry.name, kind))
    found.sort()
    return found
