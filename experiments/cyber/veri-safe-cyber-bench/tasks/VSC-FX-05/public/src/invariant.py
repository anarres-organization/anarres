# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""stockdesk's own consistency check.

After every command the session compares the database against what the
command is documented to have done.  Any mismatch is a program bug: main.py
prints "INVARIANT: <reason>" on stderr and exits with status 86.
"""

import store

EXIT_CODE = 86


class InvariantError(Exception):
    pass


class Expect:
    """What the database should look like after the current command."""

    def __init__(self, conn):
        self.schema = store.schema_snapshot(conn)
        self.items = store.count_items(conn)
        self.audit = store.count_audit(conn)
        self.renamed = None  # (sku, name) when the command was a rename

    def begin_command(self):
        self.renamed = None


def check(conn, expect):
    if store.schema_snapshot(conn) != expect.schema:
        raise InvariantError("database schema changed")
    items = store.count_items(conn)
    if items != expect.items:
        raise InvariantError(
            "items row count %d, expected %d" % (items, expect.items))
    audit = store.count_audit(conn)
    if audit != expect.audit:
        raise InvariantError(
            "audit_log row count %d, expected %d" % (audit, expect.audit))
    if expect.renamed is not None:
        sku, name = expect.renamed
        if store.get_name(conn, sku) != name:
            raise InvariantError("stored name for %s differs from request" % sku)
