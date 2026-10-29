# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""Command handlers for docvault sessions.

A session reads one command per line. Each command prints its result on
stdout; execute() returns the line's status code (0 ok, 2 error, 4 denied).
"""

import os
import re
import sys

import aliases
import archive
import guard
import vpaths
from errors import CommandError, Denied

USER_NAME = re.compile(r"[A-Za-z0-9_-]+\Z")
ARCHIVE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
MAX_DEPTH = 3

KIND_SUFFIX = {"dir": "/", "link": "@", "file": ""}


def emit(text=""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


class Session:
    def __init__(self, vault_root, depth=0, user=None, user_root=None, tables=None):
        self.vault_root = vault_root
        self.depth = depth
        self.user = user
        self.user_root = user_root
        self.tables = tables if tables is not None else {}

    # -- session plumbing -------------------------------------------------

    def child(self):
        """A nested session for RUN: starts as a copy of this one."""
        tables = {name: table.copy() for name, table in self.tables.items()}
        return Session(self.vault_root, self.depth + 1, self.user,
                       self.user_root, tables)

    def execute(self, line):
        text = line.strip()
        if not text or text.startswith("#"):
            return 0
        parts = text.split()
        handler = self.HANDLERS.get(parts[0].upper())
        try:
            if handler is None:
                raise CommandError("unknown command")
            return handler(self, parts[1:]) or 0
        except Denied:
            emit("DENIED: outside root")
            return 4
        except CommandError as exc:
            emit("ERROR: " + str(exc))
            return 2

    def _need_user(self):
        if self.user_root is None:
            raise CommandError("no user selected")
        return self.user_root

    def _aliases(self):
        self._need_user()
        return self.tables[self.user]

    def _locate_file(self, rel):
        """Map a path argument to a real regular file in the user's folder."""
        user_root = self._need_user()
        expanded = self._aliases().expand(rel)
        joined = vpaths.join_user(user_root, expanded)
        if not vpaths.within_text(user_root, joined):
            raise Denied()
        real = os.path.realpath(joined)
        if not os.path.exists(real):
            raise CommandError("not found")
        if not os.path.isfile(real):
            raise CommandError("not a file")
        return real

    # -- commands ---------------------------------------------------------

    def cmd_user(self, args):
        if len(args) != 1:
            raise CommandError("usage: USER name")
        name = args[0]
        if not USER_NAME.match(name):
            raise CommandError("bad user name")
        users_dir = os.path.realpath(os.path.join(self.vault_root, "users"))
        candidate = os.path.realpath(os.path.join(users_dir, name))
        if (candidate == users_dir or not vpaths.within_real(users_dir, candidate)
                or not os.path.isdir(candidate)):
            raise CommandError("no such user")
        self.user = name
        self.user_root = candidate
        self.tables.setdefault(name, aliases.AliasTable())
        emit("OK user " + name)

    def cmd_read(self, args):
        if len(args) != 1:
            raise CommandError("usage: READ path")
        real = self._locate_file(args[0])
        data = guard.read_bytes(real, self.user_root)
        for text_line in data.decode("utf-8", "replace").splitlines():
            emit(text_line)

    def cmd_list(self, args):
        if len(args) > 1:
            raise CommandError("usage: LIST [path]")
        rel = args[0] if args else "."
        user_root = self._need_user()
        vpaths.resolve_real(user_root, rel)
        expanded = self._aliases().expand(rel)
        target = os.path.realpath(vpaths.join_user(user_root, expanded))
        if not os.path.exists(target):
            raise CommandError("not found")
        if not os.path.isdir(target):
            raise CommandError("not a folder")
        entries = guard.list_dir(target, user_root)
        if not entries:
            emit("(empty)")
        for name, kind in entries:
            emit(name + KIND_SUFFIX[kind])

    def cmd_alias(self, args):
        if len(args) != 2:
            raise CommandError("usage: ALIAS name target")
        self._aliases().define(args[0], args[1])
        emit("OK alias " + args[0])

    def cmd_aliases(self, args):
        pairs = self._aliases().items()
        if not pairs:
            emit("(none)")
        for name, target in pairs:
            emit(name + " -> " + target)

    def cmd_echo(self, args):
        emit(" ".join(args))

    def cmd_run(self, args):
        if len(args) != 1:
            raise CommandError("usage: RUN path")
        real = self._locate_file(args[0])
        if self.depth >= MAX_DEPTH:
            raise CommandError("nesting too deep")
        data = guard.read_bytes(real, self.user_root)
        child = self.child()
        worst = 0
        for text_line in data.decode("utf-8", "replace").splitlines():
            worst = max(worst, child.execute(text_line))
        return worst

    def cmd_export(self, args):
        if len(args) < 2:
            raise CommandError("usage: EXPORT name path...")
        name = args[0]
        if not ARCHIVE_NAME.match(name):
            raise CommandError("bad archive name")
        user_root = self._need_user()
        table = self._aliases()
        starts = []
        for raw in args[1:]:
            real = vpaths.resolve_real(user_root, table.expand(raw))
            if not os.path.exists(real):
                raise CommandError("not found")
            starts.append(real)
        files = archive.collect(user_root, starts)
        data = archive.build(user_root, files)
        out_dir = vpaths.resolve_real(user_root, archive.EXPORT_DIR)
        guard.make_dir(out_dir, user_root)
        guard.write_bytes(os.path.join(out_dir, name + ".tar"), user_root, data)
        emit("EXPORTED %s: %d files" % (name, len(files)))

    def cmd_toc(self, args):
        if len(args) != 1:
            raise CommandError("usage: TOC name")
        if not ARCHIVE_NAME.match(args[0]):
            raise CommandError("bad archive name")
        user_root = self._need_user()
        real = vpaths.resolve_real(
            user_root, archive.EXPORT_DIR + "/" + args[0] + ".tar")
        if not os.path.isfile(real):
            raise CommandError("no such archive")
        members = archive.table_of_contents(guard.read_bytes(real, user_root))
        if not members:
            emit("(empty)")
        for member, size in members:
            emit("%s %d" % (member, size))

    HANDLERS = {
        "USER": cmd_user,
        "READ": cmd_read,
        "LIST": cmd_list,
        "ALIAS": cmd_alias,
        "ALIASES": cmd_aliases,
        "ECHO": cmd_echo,
        "RUN": cmd_run,
        "EXPORT": cmd_export,
        "TOC": cmd_toc,
    }
