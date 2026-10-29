# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Path helpers for mapping user supplied paths into a user's folder.

All paths typed by users are relative to the user's folder. A leading slash is
not special: "/docs/a.txt" means "docs/a.txt" inside the folder.
"""

import os

from errors import Denied


def clean_rel(rel):
    return rel.lstrip("/")


def join_user(user_root, rel):
    """Join a user supplied path onto the user's folder (text only)."""
    return os.path.join(user_root, clean_rel(rel))


def within_text(user_root, joined):
    """Quick containment test on the joined path text.

    Used by the single-file commands, which only need to know whether the
    request stays below the user's folder.
    """
    return joined.startswith(user_root)


def within_real(user_root, real):
    """True when an already resolved path is the folder or lies below it."""
    return real == user_root or real.startswith(user_root + os.sep)


def resolve_real(user_root, rel):
    """Resolve a user supplied path and require it to stay in the folder."""
    real = os.path.realpath(join_user(user_root, rel))
    if not within_real(user_root, real):
        raise Denied()
    return real
