# docvault

docvault is a small document store used by a (fictional) team wiki. Documents
live under a vault directory, one folder per user (`VAULT_ROOT/users/<name>/`).
A front end pipes commands to it, one per line, on stdin:

    python3 docvault.py VAULT_ROOT < commands.txt

Every user only ever sees their own folder, called the *user root* below.

## Commands

Commands are case-insensitive, arguments are separated by whitespace. Blank lines
and lines starting with `#` are ignored.

| Command | Effect |
|---|---|
| `USER name` | select the user (folder must exist) -> `OK user name` |
| `READ path` | print the lines of a file |
| `LIST [path]` | list a folder (default `.`): folders end in `/`, links in `@` |
| `ALIAS name target` | remember `target` under `@name` -> `OK alias name` |
| `ALIASES` | print `name -> target` lines (`(none)` if empty) |
| `EXPORT name path...` | write `exports/name.tar` into the user root -> `EXPORTED name: N files` |
| `TOC name` | print `member size` lines of an exported archive |
| `RUN path` | run the commands stored in a file, as a nested session |
| `ECHO text...` | print the text |

Paths are always relative to the user root; a leading `/` is not special
(`/docs/a.txt` is `docs/a.txt`). Parts such as `.` and `..` and links inside the
user root are fine as long as the final location is inside the user root.

An alias target is plain path text. A path argument that starts with `@name` has
that prefix replaced by the target (targets may start with another alias, up to
4 levels, otherwise `ERROR: alias loop`). `ALIAS` itself never fails because of
the target; the target is checked each time the alias is used. Aliases belong to
a user and are kept when switching users.

`EXPORT` expands every folder argument recursively (following links, each
folder once, never including the user's own `exports/` folder) and stores each
real file once, named by its real location relative to the user root, sorted.
Links that lead to neither a file nor a folder are skipped.

`RUN` executes the lines of a file in a nested session. The nested session starts
with the caller's user and aliases; `USER` and `ALIAS` inside it do not change
the caller. Output goes to the same stdout. Nesting is limited to 3 levels
(`ERROR: nesting too deep`).

## Safe behaviour (documented contract)

* **Containment.** Any request that resolves outside the user root gets
  `DENIED: outside root` on stdout, status 4 for that line, and processing
  continues with the next line. "Resolves" means the final location after alias
  expansion, `..` handling and following every link, including files and
  folders reached while a folder is being expanded. The check happens before
  existence is looked at, so a missing target outside the user root is also
  denied (not `ERROR: not found`). This applies to every command, including
  commands inside a `RUN` file and the `RUN` file itself.
* **EXPORT is all or nothing.** If any path, or anything reached while
  expanding a folder, resolves outside the user root, the whole line is denied
  and no archive is written or replaced.
* **Other errors** print `ERROR: <reason>` and use status 2 for that line:
  `usage ...`, `unknown command`, `no user selected`, `no such user`,
  `bad user name`, `bad alias name`, `unknown alias`, `alias loop`, `not found`,
  `not a file`, `not a folder`, `bad archive name`, `no such archive`,
  `bad archive`, `path too long`, `nesting too deep`.
* **Exit status** of the program is the highest line status (0, 2 or 4).
* **Internal invariant.** `guard.py` re-checks every file or folder before it
  is opened, written or listed. If one lies outside the user root the program
  prints `INVARIANT: ... outside user root` on stderr and exits with 86. In a
  correct build this never happens: the command layer must reject such
  requests first.
