# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Archive export: gather the files behind a set of paths into a tar file."""

import io
import os
import tarfile

import errors
import guard

EXPORT_DIR = "exports"
MAX_NAME = 100


def collect(user_root, starts):
    """Expand resolved start paths into the sorted list of regular files.

    Folders are expanded recursively (links are followed, every folder is
    visited once). The user's own exports folder is never included.
    """
    skip = os.path.realpath(os.path.join(user_root, EXPORT_DIR))
    files = set()
    seen = set()
    pending = list(starts)
    while pending:
        real = pending.pop()
        if real in seen:
            continue
        seen.add(real)
        if os.path.isdir(real):
            if real == skip:
                continue
            for name, _kind in guard.list_dir(real, user_root):
                pending.append(os.path.realpath(os.path.join(real, name)))
        elif os.path.isfile(real):
            files.add(real)
    return sorted(files)


def member_name(user_root, real):
    return os.path.relpath(real, user_root).replace(os.sep, "/")


def build(user_root, files):
    """Return the bytes of a tar archive holding the given real files."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for real in files:
            name = member_name(user_root, real)
            if len(name) > MAX_NAME:
                raise errors.CommandError("path too long")
            data = guard.read_bytes(real, user_root)
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def table_of_contents(data):
    """Return [(member name, size)] for archive bytes made by build()."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tar:
            return [(m.name, m.size) for m in tar.getmembers()]
    except tarfile.TarError:
        raise errors.CommandError("bad archive")
