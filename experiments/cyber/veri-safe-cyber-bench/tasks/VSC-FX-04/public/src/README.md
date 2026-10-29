<!-- Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. -->
# sesscache

`sesscache` is a small, invented session cache used in a training exercise. A
front-end service keeps a few "sessions" in memory (an id plus a payload
buffer). This tool replays a text command script on stdin against that cache
and prints one reply per command, so the cache logic can be tested without the
service around it.

Build: `sh build.sh` (produces `./sesscache`, built with AddressSanitizer and
UBSan). Run: `./sesscache < script.in`. The exit status is always 0 for a
correct run.

## Data model

* A session has an id (1 to 15 characters from `A-Z a-z 0-9 _ . -`), a payload
  buffer of 1 to 4096 bytes, a reference count `refs`, a pin count `pins` and a
  "last used" time.
* The cache holds at most 6 sessions and at most 8192 payload bytes in total.
* Every session is reachable from three places: the hash index, the LRU list
  (most recently used first) and, while `pins > 0`, the pin set that `stats`
  uses for its pinned-bytes figure.
* The clock is logical. It starts at 0 and advances by one at the start of
  every command line, including lines that turn out to be errors. Blank lines
  and lines starting with `#` are ignored and do not advance the clock.
  "idle" of a session is `clock - last used`.

## Commands

| command | meaning |
|---|---|
| `open ID [SIZE]` | create a session with a payload of SIZE bytes (default 16), `refs=1`. If ID is already open, add one reference instead (SIZE is ignored) and mark it recently used. |
| `touch ID` | mark the session recently used |
| `touch ID pin` / `touch ID unpin` | also add / remove one pin |
| `close ID` | drop one reference; the session is removed when `refs` reaches 0 |
| `evict ID` | remove the session at once, whatever its `refs` |
| `expire AGE` | remove every unpinned session whose idle time is at least AGE, oldest first |
| `dump` | list the sessions, most recently used first |
| `stats` | print the counters |

## Replies

| situation | reply (one line on stdout) |
|---|---|
| new session | `ok opened ID size=S` (preceded by `note: evicted OLD (capacity)` when room had to be made) |
| id already open | `ok reopened ID refs=N` |
| `touch` | `ok touched ID`, `ok pinned ID pins=N`, `ok unpinned ID pins=N` |
| `close`, references remain | `ok released ID refs=N` |
| `close`, last reference | `ok closed ID` |
| `evict` | `ok evicted ID` |
| `expire` | `expired ID` for each removed session (oldest first), then `ok expired N skipped=M` |
| `dump` | `dump: N sessions`, then per session `  ID refs=R pins=P size=S sum=C idle=T` |
| `stats` | two lines, see below |

### Documented safe behaviour

* **Missing or closed ids.** `touch`, `close` and `evict` on an id that is not
  in the cache (never opened, closed, evicted, or expired) print
  `error: no such session` and processing continues. This holds for every way a
  session can have left the cache.
* **Pinned sessions are protected.** `evict ID` on a pinned session prints
  `error: session pinned` and changes nothing. `close ID` on a pinned session
  whose `refs` is 1 prints `error: session pinned` and changes nothing.
  `expire` never removes a pinned session; it counts it in `skipped` and in the
  `pinned_skips` counter instead (only sessions that were old enough count).
  `touch ID unpin` on a session with no pins prints `error: not pinned`.
* **Capacity.** Opening a new id in a full cache first removes the least
  recently used session that is not pinned (`note: evicted ...`). If every
  session is pinned the reply is `error: cache full`.
* **A failed open changes nothing.** An open fails with `error: open failed`
  when SIZE is 0, larger than 4096, or would push the payload total over 8192.
  This check comes first (before the capacity check). After a failed open the
  cache is exactly as it was before the command: nothing was added, nothing was
  evicted, no counter other than `open_failed` and `errors` moved (the clock still advances), and the id
  can be opened again later.
* **Syntax errors.** `error: unknown command`, `error: bad id`,
  `error: bad number` (not a plain decimal of at most 9 digits),
  `error: usage: ...`, `error: too many arguments` (more than 4 words),
  `error: line too long` (more than 254 characters before the newline). Each prints one line and
  processing continues.

### stats

```
stats: sessions=N pinned=P pinned_bytes=B pool=U/8192
stats: opened=.. reopened=.. closed=.. evicted=.. expired=.. open_failed=.. pinned_skips=.. errors=..
```

`sessions` is the number of sessions in the cache, `pinned` the number of
pinned sessions, `pinned_bytes` their payload bytes, `pool` the payload bytes
held. `evicted` counts both `evict` and capacity evictions. `errors` counts
every `error:` line printed.

## Maintenance note

Object lifetime handling in this code base has been reported as inconsistent:
under some command sequences a session can be released twice or used after it
has been removed from the cache. The reply behaviour above is the contract; the
fix must not change any reply for a command sequence that already works.
