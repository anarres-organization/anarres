# Vero starting-policy requalification

**Status:** development-only design. Execution is not authorized until a new
controller lock and deployment receipt bind the revised limits. The completed
v5 result remains unchanged, and qualification and prospective repositories
remain unopened.

## Why the interaction contract must be requalified

The v5 measurement produced 32 infrastructure-valid fresh grades and zero
strict successes across 2,776 specification trials. Every attempt stopped at
the cumulative exported-token threshold after four to six controller steps.
Eight task trees changed, but the policy did not reach a strictly valid proof.

Two released evaluations show that this budget is below the regime used for
repository-scale proof engineering:

- [Vero](https://arxiv.org/abs/2608.13522) evaluates each repository for 90
  minutes. Its strongest configuration continues adding proof code throughout
  the run, and even slower agents can leave every proof route unfilled when the
  implementation phase consumes the budget.
- [Leanstral 1.5](https://mistral.ai/news/leanstral-1-5/) reports strong
  test-time scaling from 50,000 to 200,000, 1 million, and 4 million tokens per
  attempt. Its repository case study uses multiple context compactions and more
  than 2.7 million tokens.

These sources do not predict success on Vero. They show that a 50,000-token
controller threshold cannot qualify Leanstral for the long-horizon behavior it
was designed to exhibit. The next pass therefore measures whether additional
interaction budget produces strict support before any environment comparison
is attempted.

## Development-only budget ladder

The ladder uses `primepy` in proof mode. It is the smallest repository in the
frozen development panel, with nine scored specifications. Selection uses the
source inventory and does not inspect a qualification or prospective outcome.

### Stage A: 200,000-token qualification

Run one excluded calibration attempt with:

- the same model revision, Vibe revision, prompt, sandbox, task image, and fresh
  Vero grader as v5
- at most 200,000 actual exported input and output tokens
- at most 100 controller turns
- a 5,400-second wall-time limit
- the existing 200,000-token model context and 168,000-token compaction
  threshold
- no network access and no scientific retry.

The attempt passes interface qualification only if it reaches an expected-slot
edit, invokes a fresh build after the edit, and completes infrastructure-valid
grading. It establishes policy support only if at least one specification
passes strict grading.

### Stage B: one prespecified 1-million-token escalation

Stage B runs only when Stage A reaches an edit and fresh build but closes no
specification. It keeps the same repository, mode, policy, and grader while
raising the cumulative exported-token threshold to 1 million. Context remains
bounded at 200,000 tokens, so continued work requires the pinned Vibe
compaction path.

If Stage A fails to reach an edit and build, execution stops for an interface
audit. If Stage B also produces zero strict support, Leanstral is rejected as
the starting policy for this Vero contract. The next policy must have released
repository-level Lean evidence or a released Vero baseline before local
qualification.

## Support screen after calibration

Once one budget establishes strict support, a fresh development-only screen
runs one attempt for each of the four repositories in both proof modes. A later
repeated measurement is frozen only if that screen finds:

1. infrastructure-valid grading for every identity
2. nonzero strict coverage in at least two repositories
3. pooled strict success below 80 percent
4. no containment, marker, axiom, or fresh-build violation.

The screen is excluded from the repeated measurement and cannot rank candidate
environments. The repeated design retains independent attempts because mixed
success, usable signal density, and effective coverage cannot be estimated
from one attempt per repository.

## Decision boundary

The first admissible output is a starting policy with measurable development
support at a known interaction cost. Candidate construction follows only after
that gate passes. Downstream training remains blocked until at least three
candidate environments pass their source, containment, reward-integrity, and
measurement gates under the same qualified policy contract.
