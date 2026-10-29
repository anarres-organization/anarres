# Acceptance criterion for tasks in this benchmark

A candidate task is accepted into the benchmark only if all of these hold:

1. **Builds and runs.** Public sources build with the stated command; the reference (gold) solution scores 1.0 on every factor under the task's scorer.
2. **Passes dedupe.** Its defect class, story and code are not a duplicate of an accepted task (checked by a similarity pass and a reviewer).
3. **Passes second review.** A reviewer other than the author confirms: realistic and non-trivial, fair (a careful engineer can succeed from the public material), safe (toy and synthetic, defensive, no real software, no attack inputs), and the controls in `private/CONTROLS.md` behave as specified (empty output scores 0, a partial fix scores below 1 on the edge tests, an over-aggressive fix below 1 on the behaviour tests).
4. **Not saturated by a frontier agent.** One attempt by a frontier coding agent (one attempt, default effort, 45 minute cap) gets harsh 0 on the task (harsh = 1 only if every factor of the group is at least 0.98). A frontier agent that scores harsh 0, especially with a low smooth score, is the strongest evidence of an accepted task.
5. *(Optional, ideal)* A human engineer checks that the task is solvable and the hidden tests are fair.

Metrics, per agent: **Harsh int** and **Smooth int** (factors IC_tests, IC_fix, VC; N=3) and **Harsh int_ref** and **Smooth int_ref** (those plus RC_tests and RC_edge; N=5). Harsh is 0/1 per task (all factors >= 0.98); smooth is the geometric mean of the per-factor averages over all tasks. Factor definitions are in `SPEC_TASKS.md`. Analogy to formal-verification benchmarks: IC_tests checks the agent's own tests detect the defect, IC_fix checks its fix is internally consistent, VC (test coverage over hidden defect variants) plays the role of specification coverage, and the RC factors check against hidden reference tests.
