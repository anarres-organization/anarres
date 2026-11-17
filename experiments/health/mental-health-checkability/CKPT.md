# Checkpoint

State: exploratory pilot complete on fictional tasks. Protocol frozen before
any run, with two dated amendments (A1, A2) that left every prediction
unchanged.

Done: sources scan, fixtures, verifier controls, two policy runs, two judge
passes on transcripts, one judge pass on policy replies, native CLI flow.

Amendment A3 (2026-11-16): one validation vignette was replaced and both
judges re-graded the two affected items. Results unchanged. See RESULTS.md.

Open flaws found:

- The thought-record rubric clause "content drawn from the user's facts"
  fails gold replies that invent illustrative evidence. One judge followed the
  clause literally and lost four items. A revised rubric is a new version and
  has not been run.
- The lexical empathy rule R1 is too narrow. It marks control replies as
  failures that both judges pass.
- One judge shares a model family with the fixture author, so its 24/24 on
  transcripts may be optimistic.
- The exact and lexical verifiers share one coordinate in the v1 convention.

Next step: one decision for the owner, listed in the reply, on whether to run a
second round with a revised rubric and a larger transcript set written by a
second author.

Checks run: unit tests (14 pass), ruff format and ruff check on the health
directory, repository hygiene, prose style. `anarres validate` passed on all
profiles. Not run: the repository schema validator (its Python dependencies
were unavailable offline), Rust checks, and the full `make check`.

After the freeze, `scripts/checkers.py` received only a ruff format pass and a
lint-suppression comment. Rerunning every score script reproduced the committed
result files byte for byte. Raw model outputs and prompts were renamed (`.jsonl`
and `.prompt`) with contents unchanged, so the prose-style check does not read
quoted model text.
