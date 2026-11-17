# Health mental-support checkability v1

- Stability: development
- Revision: `v1-development`
- Scope: candidate response-checking environments for mental-health support
  conversations, measured under one frozen starting policy on fictional tasks

This convention transports a small set of coordinates from the mental-health
checkability study. It does not prescribe a mixture rule, does not imply that a
larger value is better, and makes no clinical validity claim. Native evidence
keeps the verifier kind (exact or lexical), the risk type, and the missingness
accounting.

The study uses fictional, synthetic tasks only. Nothing here is clinical advice.

## `verifier_pass_fraction`

Fraction of valid measured responses that pass the environment's declared
verifier. Unit: `fraction`. Direction is contextual. An environment near 1.0 is
at ceiling and gives little selection signal. An environment near 0.0 may
reflect a narrow verifier instead of a weak policy. The native record names the
verifier kind.

## `deterministic_criteria_fraction`

Fraction of the environment's scored criteria that an exact or documented rule
can decide without a model judge. Unit: `fraction`. This describes the
environment, not the policy.

## `mean_response_words`

Arithmetic mean word count of valid responses. Unit: `words_per_response`.

## `missingness_rate`

Fraction of expected responses that are absent or unparseable after
infrastructure accounting. Unit: `fraction`. A malformed or missing response is
not converted into a failed check, and an infrastructure failure is not a
scientific zero.

## Verifier kinds

Exact verifiers (score arithmetic and cutpoint lookup for PHQ-9 and GAD-7
answers) and lexical verifiers (regular-expression rules for safety,
validation, and thought-record structure) have different error profiles. The v1
profiles carry both under `verifier_pass_fraction` and `anarres design` reports
the pair as using different coordinate definitions. A later revision should
split them into separate coordinates.

## Judge boundary

LLM-judge outcomes on fictional replies are a linked evaluation record, not a
coordinate of this convention, until an experiment validates a judge against
expert labels.
