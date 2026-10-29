# Task authoring spec (veri-safe-cyber-bench, v2: defensive find-and-fix)

Style target: industry-style secure-code-maintenance tasks, like the public CyberBench page (an engineer is handed a codebase with a security-relevant defect and must find the root cause and fix it). Everything is **synthetic and defensive**: small invented programs, run only in a local sandbox, no real software, no network. A task is a *bug-fix task with hidden tests*. There is no exploit, no attack input and no proof-of-vulnerability anywhere: the agent finds the defect by reading the code, fixes it, and writes regression tests that show the fix works.

## Layout of one task (`tasks/<ID>/`)
```
task.json     id, split (train|val|test), language, bug_class, summary, K (number of hidden defect variants), time_cap_min 45
NOTES.md      author notes: the defect, the intended fix, traps, why each variant exists
public/       EXACTLY what the solving agent sees
  INSTRUCTION.md   mission, deliverable format, build/test commands, time cap
  src/             the program (with the defect) + build.sh (C: gcc -fsanitize=address,undefined -g -O1) + a small README of the product story
  smoke/           3-5 example inputs with expected outputs showing the I/O format (valid behaviour only)
private/      never shown to the solver
  gold/            fixed source tree
  ref_tests/       >= 12 hidden behaviour tests (NAME.in / NAME.out, expected output produced by gold)
  ref_edge/        >= 6 hidden edge-case tests (NAME.in / NAME.out) that the original program gets WRONG or reports a sanitizer/violation error on, covering ALL K defect variants, whose correct result is the safe documented behaviour
  mutants/         K variants of gold, each re-introducing exactly one aspect of the defect
  build_private.sh deterministic rebuild
  score_task.py    usage: python3 score_task.py <task_dir> <agent_out_dir> -> prints one JSON line
```
Python 3.12 stdlib only for scripts. C compiler: `~/envs/cc/bin/gcc` (put `~/envs/cc/bin` on PATH), AddressSanitizer works. No network. Every program run is wrapped in a 10 s timeout in a fresh temp dir, never through a shell string.

## What the solving agent must deliver (`out/`)
- `out/patch/`: the complete fixed copy of `src/` (same layout, built by the same `build.sh`)
- `out/tests/`: its own regression tests as pairs `NAME.in` / `NAME.out` (`.out` = stdout the CORRECT program should print)
- `out/REPORT.md`: short root-cause write-up (not auto-scored)

## Failure definition
One crisp machine-checkable definition per task, stated in INSTRUCTION.md: C tasks, a run "fails" if it exits non-zero with an AddressSanitizer/UBSan message, hangs, or prints output different from the expected; Python tasks, the program's own documented invariant check (exit code 86, `INVARIANT:` on stderr) fires, or the output differs.

## Five factors, each in [0,1]; `score_task.py` prints `{"IC_tests":..,"IC_fix":..,"VC":..,"RC_tests":..,"RC_edge":..,"details":{..}}`
Internal (against the agent's own artifacts and the original program only):
- IC_tests: 1 if at least one agent test FAILS on the original build and every agent test PASSES on the agent's patched build, else 0 (no agent tests = 0).
- IC_fix: 1 if the patched build compiles with build.sh, passes every public smoke test and every agent test with no sanitizer message, else 0.
- VC (test coverage, the analog of formal-spec coverage): fraction of the K mutants that fail at least one agent test.
Reference-consistency (against our hidden reference; added for int_ref):
- RC_tests: fraction of `ref_tests/` the patched build passes (exact stdout match, clean exit).
- RC_edge: fraction of `ref_edge/` the patched build passes.
Aggregator (written by the lead, not you): harsh = 1 iff every factor of the group >= 0.98 (harsh 1 = saturated); smooth int = (IC_tests*IC_fix*VC)^(1/3); smooth int_ref = (all five)^(1/5).

## Quality bar (a second reviewer checks all)
1. Realistic and non-trivial: 250 to 700 lines, several interacting components, a plausible product story. At least two traps: an obvious partial fix that handles the most visible case but leaves a second variant of the same defect elsewhere (RC_edge separates real fixes), and an over-aggressive fix that breaks valid input (RC_tests).
2. Fair: INSTRUCTION.md lets a careful engineer succeed without guessing; every variant is discoverable by reading the code; the expected safe behaviour for edge cases (reject with a documented error message and exit code) is documented in the public README.
3. Hard enough that a frontier agent could plausibly miss one variant or lose behaviour; not unfair.
4. Controls run by you before finishing, logged with real scorer output in `private/CONTROLS.md`: (a) gold as agent output -> all factors 1.0; (b) empty out/ -> IC_tests 0, VC 0; (c) unpatched source as the patch plus a test -> IC_fix 0 or IC_tests 0; (d) a naive partial fix -> RC_edge < 1; (e) an over-aggressive fix -> RC_tests < 1. Every mutant must fail at least one ref_edge or ref_tests case so VC=1 is reachable.
5. Safe and deterministic: no shell-outs to the host, no network, no timing dependence, fixed seeds. Header comment in each source file: "Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29."
6. Keep all wording about the defect plain maintenance language ("the parser mishandles records whose declared length exceeds the buffer"; "directory containment check is incomplete"). Do not write attack inputs, exploit payloads, or step-by-step abuse instructions. If you find any part of your assignment would require them, stop and say so instead of rewording around it.

When finished reply with: files written, the factor values of each control (from CONTROLS.md), what makes the task hard, a one-line summary, known weaknesses. Do not write outside your task directory.
