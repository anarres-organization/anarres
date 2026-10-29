# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""docvault: a tiny document store served from a root directory.

Usage: python3 docvault.py VAULT_ROOT < commands

Commands are read from stdin, one per line (see README.md). The exit status is
the highest status code of any line: 0 ok, 2 error, 4 denied. Status 86 means
the internal safety check stopped the program.
"""

import os
import sys

from commands import Session


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: docvault.py VAULT_ROOT\n")
        return 64
    vault_root = os.path.realpath(argv[1])
    if not os.path.isdir(vault_root):
        sys.stderr.write("docvault: no such vault root\n")
        return 66
    session = Session(vault_root)
    worst = 0
    for line in sys.stdin:
        worst = max(worst, session.execute(line))
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
