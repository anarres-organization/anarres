# Formal-verification source qualification

This directory compares five public formal-verification sources under one
qualification gate and asks which one should host the next prospective
environment-selection test (issue #65). The record is preliminary. Sources,
revisions, and licenses were checked against primary material, a partial trace
of one published result was recorded for each source, and each source received
a proceed, reserve, or reject decision. No source was executed for this record
and no training was launched.

**No source is selected yet.** Every source is in reserve, so the selection
rule abstains, as the issue requires when no source supports an honest and
feasible decision. Vero is the leading candidate, pending a trainable-policy
pilot.

## Terms

- **Source**: a public benchmark or dataset together with its own verifier.
- **Candidate environment**: one task or training-data distribution that a
  panel could train on.
- **Starting policy**: the model measured before any training.
- **Strict support**: at least one task passes the strict verifier for that
  policy. **Mixed outcomes** means the same task both passes and fails across
  repeated attempts.
- **Held-out target**: tasks used only to score trained arms.
- **Proceed**: the source is selected for the prospective test. A proceed
  decision still does not freeze a candidate panel or authorize training.

## Decisions at a glance

| Rank | Source | Setting | Endpoints | Decision | Main open checks |
| --- | --- | --- | --- | --- | --- |
| 1 | Vero | 43 Lean 4 repositories | proof-only, code-and-proof | reserve | No trainable policy with strict support. Piggybank trusted axiom and shared-upstream lineage unchecked. |
| 2 | OSS Verify | Rocq proofs about 2,183 RISC-V OSS-Fuzz entry points | proof-only | reserve | Checker not replayed at the issue pin. No open-model support. Proof checks cost CPU-hours. |
| 3 | VeruSAGE-Bench with VeruSyn | 849 Verus tasks from 8 Rust systems projects | proof-only | reserve | Training-data license, Verus pin, verifier run, and an unscored target open |
| 4 | VeriCoding | about 12,500 Dafny, Verus, and Lean task files | code-and-proof | reserve | No axiom audit (a failed check). Harness revision and one family license open. |
| 5 | VeriSoftBench | 500 Lean theorems in 23 repositories | proof-only | reserve | No axiom audit, which a published strict recheck shows matters. Hosted-API-only harness. |

Counts are native units. The independent unit is the repository, library, or
source family, so thousands of tasks do not mean thousands of independent
observations.

## Recommendation

The rule abstains. Vero ranks first because its source, runtime, grader, split,
and containment are already qualified. Its blocker is the starting policy. The
hosted GPT-5.6 Sol passed 1,653 of 2,776 strict specification trials, but
Anarres cannot train it. The open-weight Leanstral-1.5 passed 0 of 2,776.
Support has been measured on only 4 of 23 development repositories, and the
prospective target holds only 10 repositories.

VeruSAGE-Bench with VeruSyn ranks third under the rule because it has more
open checks than Vero or OSS Verify, mostly confirmations that a smoke test can
settle. It remains the
only audited source with a published training study that varies data
composition on an open base model.

#66 uses the selected source as its acceptance path, so its source follows the
eventual selection. Vero is named only as the leading candidate.

**Source smoke tests.** The rule picks the first two reserve sources whose
verifier has not been reproduced and that document an official smoke test.
Neither test opens a held-out outcome.

1. **OSS Verify checker replay.** Choose the pin, run `tests/check.sh` in the
   pinned checker image with networking off, then run
   `./oft check coturn/FuzzStunClient --parts statements,proofs` and record
   wall time and peak memory.
2. **VeruSAGE-Bench verifier check.** Pin one Verus commit, verify the
   reference proofs of all 849 tasks or a subset fixed by task ID beforehand,
   record time and memory per task, and confirm that inserted `assume`,
   `admit`, and `external_body` controls and a weakened specification are
   rejected.

**Policy pilot.** Separately, a development-only pilot should run Leanstral-1.5
under its native agent configuration and one other open-weight model on Vero
development repositories, under the existing grader and containment contract.
This pilot measures a starting policy and is not a source smoke test.

**Owed for every source.** The issue's matched-exposure panel (fixed random,
source-native baseline, strongest published rule, policy-relative rule, and a
combined rule) with its full freeze contract is not drafted. Candidate and
target leakage audits have not been run.

## How decisions are made

[`QUALIFICATION.json`](QUALIFICATION.json) asks the issue's gate questions of
every source as 25 checks. Each check has a status of pass, unresolved, or fail
and a list of evidence claims marked confirmed, inferred, or unknown. A pass
needs at least one confirmed claim. Checks belong to one of three tiers.

- **Source selection** checks must all pass for proceed.
- **Panel freeze** checks must pass before a panel is frozen.
- **Record** checks are kept for comparison.

An unresolved entry blocks the tier of the check it names, and a check with an
open entry cannot pass. The issue's eight criteria map onto source-selection
checks. Criterion 3, a capable starting-policy probe, includes whether a policy
that can be trained here shows nonzero, non-saturated strict support. A
criterion takes the most severe status of its checks. A source is rejected when
a source-selection check fails with no remediation, reserved when any other
source-selection check is open, and selected otherwise. Reserve sources are
ordered by failed criteria, then by open source-selection checks, then by
unresolved criteria. For criterion 5 every pass rests on confirmed field and
count facts, while the decisive claim that matched-exposure candidates can be
built from them is inferred. With no proceed source the rule abstains and names the
first reserve source as the leading candidate.

The rule was written after the Vero Leanstral-1.5 and GPT-5.6 Sol measurements,
which it cites, and before any source smoke test. The script
[`scripts/verify.py`](scripts/verify.py) applies it and rejects a record whose
stated decision, ranking, or recommendation differs from the rule's result.

## Published outcomes and proposed held-out decisions

Published outcomes are already visible and cannot serve as a prospective
target. The proposed decisions are drafts. None is frozen and none has an
opened outcome.

| Source | Visible published outcome | Proposed held-out decision |
| --- | --- | --- |
| Vero | GPT-5.5 xhigh fully solves 27 of 43 repositories (code-and-proof) | Which development-repository composition most improves strict passes on the 10 frozen prospective repositories, per endpoint |
| OSS Verify | Claude proved 239 entry points in 123 libraries | Which statement pool most improves proofs of statements proved after a frozen release |
| VeriCoding | Model-union success of 82.2 percent on Dafny | Which source family most improves held-out families within one language |
| VeruSAGE with VeruSyn | Full VeruSyn data lifts Qwen2.5-Coder-32B from 10 to 39 percent on the 560-task target | Which released data composition at matched exposure most improves a target that Table 1 has not scored |
| VeriSoftBench | Gemini-3-Pro solves 41.0 percent with curated context | Which category or depth composition most improves held-out repositories |

Each published trace is partial and none is complete.

- **Vero**: the grader is released, but the producing runs and the number of
  runs per table cell are not.
- **OSS Verify**: the 90 proved entry points trace to the index, but the
  36-task data and production proofs are unreleased, and the released cJSON
  proof is larger than the reported one.
- **VeriCoding**: one Verus cell reproduces from the results file, but
  solutions, verifier logs, and the harness revision are not released, and
  several other cells do not reproduce.
- **VeruSAGE with VeruSyn**: training data and tasks are released, but the
  fine-tuned weights, generations, and Verus build are not.
- **VeriSoftBench**: per-task outcomes are not released, and the paper's
  aggregates disagree by 0.2 to 1.4 points.

Proof-only, code-and-proof, specification-construction, and
specification-faithfulness endpoints are recorded separately and never pooled.
None of the five sources offers a specification-construction or
specification-faithfulness endpoint.

## Findings that need follow-up elsewhere

- The [public-evidence record](../public-evidence/SOURCES.json) pins the Rocq
  Linux process semantics at `c7fbb82e`, while every audited OSS Verify revision
  checks proofs against `f1006fe8`. It also pins OSS Verify at `8304a2c0`, an
  untagged commit. The record is pinned by its own manifest, so this directory
  records the finding and leaves the fix to a separate change.
- Vero's paper reports every frontier configuration failing the same 6 of 23
  piggybank specifications, while GPT-5.6 Sol passed all 23 in all 8 repeated
  attempts. The public task source declares the trusted ConCert axiom
  `contract_induction`, but the released grade receipts do not establish
  whether submitted proofs used it. Whether the axiom faithfully models
  ConCert is an open check before piggybank enters a candidate.
- Leanstral-1.5 ran with a 50,000-token cumulative cap per attempt and with MCP
  tools disabled, so it had no Lean language-server tools. Its frozen protocol
  names an inference contract with a 200,000-token context and the Mistral
  reasoning parser, but the contract's deployment receipt was never recorded,
  so the served context and parser for those attempts are not established.

## Fifth-source survey

Fourteen further candidates were screened for official code, an executable
verifier, and a real training or environment decision. VeruSAGE-Bench with
VeruSyn was added because it alone combines real systems code, an MIT-licensed
task repository, and a published data-composition study with released
candidate datasets. PSV, Re:Form, and VeriBench are held in reserve. VeriBench
comes from the research group of this repository's owner, so any qualification
of it needs an independent auditor. The full list is in `fifth_source_survey`
in [`QUALIFICATION.json`](QUALIFICATION.json).

## Files and checks

- [`SOURCES.json`](SOURCES.json): papers with arXiv versions, repositories at
  full commit hashes, licenses, datasets, checkpoints, toolchains, verifier
  identities, and findings
- [`QUALIFICATION.json`](QUALIFICATION.json): gate checks, the selection rule,
  decisions, unresolved checks, the recommendation, and the survey
- [`CANDIDATE_MATRIX.json`](CANDIDATE_MATRIX.json): native and independent
  units, grouping keys, candidates and baselines, held-out boundaries, evidence
  added beyond Vero, cost entries marked measured, published, or estimate, and
  published outcomes kept apart from proposed decisions
- [`results/summary.json`](results/summary.json): derived summary that must
  reproduce byte for byte

```bash
python scripts/verify.py
python -m unittest discover -p 'test_*.py'
```

`python scripts/verify.py --write` regenerates the summary after a deliberate
record change.

## Limitations

Statuses for sources other than Vero come from reading documentation,
repositories, and released artifacts. The OSS Verify control replay was run at
an earlier release. Inferred claims stay inferred until a primary source or a
smoke test confirms them. The ranking counts open checks and does not weigh how
hard each is to close. Cost entries marked estimate are projections, and no
training budget has been fixed for any source.
