# LAB execution contract

The LAB execution contract pins the two runtimes that turn a qualified task set
into scored starting-policy evidence. The agent stage and judge stage remain
separate because they can use different models, dependencies, retry rules, and
credentials.

Create a JSON draft with schema version
`anarres.legal-lab-execution-contract.v1`, then qualify it with:

```bash
anarres legal lab-contract \
  --input /path/to/contract-draft.json \
  --output /path/to/lab-execution-contract.json
```

The command validates the record, sorts unordered fields, computes
`contract_sha256`, and writes deterministic JSON. It does not start a model,
grader, scheduler, or GPU job. Credentials are inherited only when a later
runtime is explicitly executed and are rejected if they appear in the record.

## Required identity

The source section binds the contract to one environment ID, LAB revision,
license, and task-set digest. The starting-policy stage records:

- model, model revision, checkpoint, and checkpoint revision
- harness name, version, revision, and package digest
- system prompt, skills, tools, sandbox image, and document access
- turn limit, sampling settings, shell timeout, finish behavior, and compaction

The judge stage independently records the grader harness and package, judge
models and revisions, rubric prompt, document conversion, parallelism, and
retry behavior. This follows LAB's native split between agent execution and
criterion-level grading.

## Outcome and validity contract

Each rubric criterion has a binary pass or fail verdict. The headline outcome
is task all-pass, which requires every criterion to pass for each judge in the
pinned judge profile. Criterion pass rate, document coverage, tool behavior,
artifact completion, latency, tokens, retries, and cost remain diagnostics.

The contract names every condition that invalidates execution. Model or judge
outages, sandbox failures, document-conversion failures, ungraded criteria,
missing artifacts, unfinished runs, and contract mismatches remain separate
from legal task failure. A missing required deliverable can count as a
scientific failure only when the execution and grading pipeline are otherwise
valid.

## Protected outcomes

The target scope records workflows, practice areas, diagnostics, and protected
outcomes. Protected workflow and practice-area outcomes must remain unavailable
before the governing freeze. The contract qualifies a future execution path.
A training-utility claim requires completed starting-policy and intervention
evidence.

## Native LAB references

The field design follows the public LAB harness and evaluation contract:

- [LAB architecture](https://github.com/harveyai/harvey-labs/blob/main/docs/architecture.md)
- [LAB evaluation methodology](https://github.com/harveyai/harvey-labs/blob/main/docs/eval-strategies.md)
- [LAB tutorial](https://github.com/harveyai/harvey-labs/blob/main/docs/tutorial.md)

Pin a LAB release or commit for claim-bearing work because the task set,
harness, and scoring implementation can change between releases.
