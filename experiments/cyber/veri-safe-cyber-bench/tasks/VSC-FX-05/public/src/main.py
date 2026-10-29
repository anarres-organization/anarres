# Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
"""stockdesk: read command lines on stdin, write results on stdout.

Run:  python3 main.py < commands.in
Exit status: 0 on normal end of input, 86 if the internal invariant check
fails (message "INVARIANT: ..." on stderr).
"""

import sys

import commands
import invariant


def main():
    sess = commands.Session(sys.stdout)
    for line in sys.stdin:
        try:
            commands.run_line(sess, line.rstrip("\r\n"))
        except invariant.InvariantError as exc:
            sys.stdout.flush()
            sys.stderr.write("INVARIANT: %s\n" % exc)
            return invariant.EXIT_CODE
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
