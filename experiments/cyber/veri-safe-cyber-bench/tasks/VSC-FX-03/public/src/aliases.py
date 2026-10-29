# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Per-user path aliases.

An alias maps a short name to a path (relative to the user's folder). A path
argument that begins with "@name" has that prefix replaced by the alias target;
a target may itself begin with another alias.
"""

import re

from errors import CommandError

ALIAS_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
MAX_ALIAS_DEPTH = 4


class AliasTable:
    def __init__(self, items=None):
        self._items = dict(items or {})

    def copy(self):
        return AliasTable(self._items)

    def define(self, name, target):
        if not ALIAS_NAME.match(name):
            raise CommandError("bad alias name")
        self._items[name] = target

    def items(self):
        return sorted(self._items.items())

    def expand(self, rel):
        """Replace a leading @name (repeatedly) by the alias target text."""
        depth = 0
        while rel.startswith("@"):
            head, _sep, rest = rel[1:].partition("/")
            if head not in self._items:
                raise CommandError("unknown alias")
            depth += 1
            if depth > MAX_ALIAS_DEPTH:
                raise CommandError("alias loop")
            rel = self._items[head] + ("/" + rest if rest else "")
        return rel
