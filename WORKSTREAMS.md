# Workstreams

This page connects each Anarres workstream to its repository path, GitHub
issues, and Discord discussion channel. GitHub records scope, assignments,
decisions, and status. Discord supports questions and short-lived coordination.
Released methods and evidence remain in the repository.

## Research programs

| Workstream | Repository path | GitHub issues | Discord |
| --- | --- | --- | --- |
| Mathematics | [`experiments/mathematics/`](experiments/mathematics/) | [`area:mathematics`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Amathematics%22) | `#mathematics` |
| Agentic systems | [`experiments/agentic/`](experiments/agentic/) | [`area:agentic-systems`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Aagentic-systems%22) | `#agentic-systems` |
| Formal verification | [`experiments/cyber/formal-verification/`](experiments/cyber/formal-verification/) | [`area:formal-verification`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Aformal-verification%22) | `#formal-verification` |
| Vulnerability exploitation | [`experiments/cyber/qualification/`](experiments/cyber/qualification/) | [`area:vulnerability-exploitation`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Avulnerability-exploitation%22) | `#vulnerability-exploitation` |
| Molecular design | [`experiments/ai-for-science/molecular-design/`](experiments/ai-for-science/molecular-design/) | [`area:molecular-design`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Amolecular-design%22) | `#molecular-design` |
| Materials science | [`experiments/ai-for-science/materials-science/`](experiments/ai-for-science/materials-science/) | [`area:materials-science`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Amaterials-science%22) | `#materials-science` |
| Robotics | [`experiments/robotics/`](experiments/robotics/) | [`area:robotics`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Arobotics%22) | `#robotics` |
| Legal reasoning | [`experiments/legal/`](experiments/legal/) | [`area:legal`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Alegal%22) | `#legal` |
| Agentic finance | [`experiments/finance/`](experiments/finance/) | [`area:finance`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Afinance%22) | `#finance` |
| Surrogate models | [`experiments/surrogate-models/`](experiments/surrogate-models/) | [open surrogate-model issues](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20surrogate) | `#surrogate-models` |

Cross-domain research proposals begin in the
[`proposal`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3Aproposal)
queue and `#research-proposals`. A proposal becomes a maintained workstream when
it has an accepted scope, a repository path, an owner, and sustained work.

## Shared software

| Workstream | Repository paths | GitHub issues | Discord |
| --- | --- | --- | --- |
| CLI and adapters | [`crates/`](crates/), [`packages/`](packages/) | [`area:cli`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Acli%22) | `#cli-and-adapters` |
| Environment processing | [`data/`](data/) | [`area:environment-processing`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Aenvironment-processing%22) | `#environment-processing` |
| Website and documentation | [`docs/`](docs/), [`README.md`](README.md) | [`area:docs`](https://github.com/anarres-organization/anarres/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22area%3Adocs%22) | `#website-docs` |

Use `#help-and-support` for installation and usage questions. Use
`#pr-reviews` after a pull request is ready for review.

## How issues fit together

A research program may contain several independent projects. Give each bounded
project one parent issue, then attach its independently assignable tasks as
sub-issues. Apply one `area:*` label to the parent and every sub-issue.

```text
research program
└── parent issue for one project
    ├── source qualification
    ├── measurement
    ├── candidate construction
    ├── execution
    └── scoring and release
```

Use milestones for time-bounded releases or experimental freezes, not for
domains. Use `status:needs-design`, `status:ready`, `status:blocked`, and
`status:needs-review` to communicate the next action. A Discord message may
link to an issue, but it does not replace the issue's status or decision record.
