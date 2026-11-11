# Native QF-Bench improvement loop

This experiment tests whether a finance agent can use observed failures to
construct a better resource environment for later quantitative-finance tasks.
It uses the public QF-Bench task contract: each task runs in an air-gapped
container and is scored by deterministic unit tests against a hand-written
reference solution.

The experiment follows the same evidence order as the legal and robotics
programs:

1. pin an external benchmark and define the prediction unit
2. freeze development, target, and protected tasks before model execution
3. observe failures only on the development tasks
4. construct procedure-only, executable-helper, and combined candidates
5. measure each candidate without opening target outcomes
6. select or abstain with the released finance decision rule
7. compare the selected candidate with no update and retain-all on sealed tasks
8. preserve misses, regressions, cost, and the complete chronology.

## Task family

The first panel focuses on risk analytics. Round 1 transfers from data
preparation and VaR/ES estimation to standard VaR and extreme-value tasks.
Round 2 transfers from dynamic covariance and credit migration to portfolio
credit-risk tasks. EWMA decomposition and tail-index estimation remain shared
protected cases.

The ten task identities and their agent-facing instruction hashes are fixed in
[`TASK_SPLIT.json`](TASK_SPLIT.json). Selection used only public task metadata,
instructions, difficulty, and financial workflow tags. No agent result,
verifier output, test implementation, or reference solution informed the
split.

## Candidate environments

Each round produces three scoped candidates from development failures:

- `procedure`: a concise diagnostic and implementation procedure
- `executable`: tested reusable numerical helpers with a minimal interface
- `combined`: the union of the procedure and executable helper.

`no_update` remains the baseline. Candidate measurements map into the released
`anarres finance decide` schema through a fixed rubric in
[`PROTOCOL.json`](PROTOCOL.json). The selector abstains when its top candidates
fall inside the released 0.2 margin. A selected candidate must also pass its
own tests and cannot regress on the development control.

## Outcomes

The primary outcome is deterministic task pass rate on the sealed target set.
Protected-task pass rate, target regret, candidate size, model tokens, wall
time, and verifier failures remain separate outcomes. The main success
criterion is that the selected candidate beats `no_update` and is no worse
than `combined` within the observed target panel. The second round tests
whether newly observed failures lead to a better subsequent decision.

## Current status

The QF-Bench source, task partition, candidate types, measurement rubric, and
success criteria are frozen. The pinned sandbox builds locally, and the oracle
passes the `historical-var-data-prep` smoke task. No model-generated development
or target outcome has entered the experiment record.

The checked-in runner remains a research implementation rather than an
installed finance-adapter policy probe. It does not yet provide a dry planning
contract, an explicit adapter execution gate, or a complete finance profile
that separates successful, failed, missing, and infrastructure-invalid
attempts. The finance adapter therefore leaves `policy-probe` undeclared.
