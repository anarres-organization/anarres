# Mental-health checkability

This pilot asks which parts of mental-health support behavior a rule can check,
and how closely two model judges follow those rules on fictional replies.

Every task is fictional and synthetic. Nothing here is clinical advice, and no
result is evidence of clinical validity. Evidence tier: exploratory, small
counts, one author for the transcripts.

## Results at a glance

| Question | Result | Counts |
| --- | --- | --- |
| Does the exact PHQ-9 and GAD-7 scorer work as a verifier? | Yes. It accepted every gold answer, rejected every corrupted copy, and marked every unparseable output invalid. | 24/24, 24/24, 24/24 |
| Do the lexical rules match construction labels? | On clear transcripts yes, on subtle ones less. | 12/12 clear, 8/12 subtle |
| Do two policies score instruments correctly? | Both at ceiling. | 24/24 each |
| Do the policies pass crisis-cue safety replies? | Judges and rules agree: Grok 4.7 0/8, Claude Sonnet 5.5 6/8. | see [RESULTS.md](RESULTS.md) |
| Do two judges agree? | Yes on policy replies, mixed on thought records. | 31/31 and 20/24 |

The headline for design is that arithmetic scoring is exactly checkable but at
ceiling, so it gives little selection signal. The informative behaviors
(asking directly about suicidal thoughts, not endorsing a risky plan) need a
judge, and the lexical rules are too narrow to replace one.

## Layout

| Path | Content |
| --- | --- |
| `PROTOCOL.json` | Frozen design, predictions, and two dated amendments |
| `scripts/` | Fixture builder, checkers, prompt builders, scoring, profile export |
| `fixtures/` | Fictional tasks and transcripts |
| `prompts/` | Policy and judge prompts used for every model call |
| `results/` | Raw model outputs, scores, profile inputs, and native CLI output |
| `RESULTS.md` | Ledger with each prediction marked met, missed, or untested |
| `SOURCES.md` | Public literature scan with how deeply each item was read |
| `RUNBOOK.md` | How to reproduce each step with no paid API and no GPU |
| `CKPT.md` | State and next step |

## Reproduce the offline parts

```bash
python3 experiments/health/mental-health-checkability/test_checkers.py
python3 experiments/health/mental-health-checkability/scripts/run_verifier_controls.py
python3 experiments/health/mental-health-checkability/scripts/score_runs.py
```

See [RUNBOOK.md](RUNBOOK.md) for the model-call steps.
