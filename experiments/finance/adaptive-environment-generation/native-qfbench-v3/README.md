# Native QF-Bench contract refinement

This experiment tests whether a narrower numerical contract can repair the v2
development regression before any portfolio credit-risk target is opened. The
candidate distinguishes one-step conditional risk from unconditional variance
and fixes the timing of rolling signals, month-end allocations, and realized
returns. It also retains the cross-file and tail-risk invariants that repaired
the earlier credit-migration development task.

The task split and source remain those frozen for v2. The v3 candidate is
derived only from committed v1 and v2 development records and primary finance
references. Target and protected outcomes, tests, and reference solutions
remain excluded.
