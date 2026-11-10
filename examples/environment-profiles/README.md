# Cross-domain environment profiles

These synthetic fixtures demonstrate the domain-neutral environment-profile
contract. They are software examples, not experimental evidence.

- `robotics-*.profile-input.json` preserves episode success variation, task
  coverage, action-step cost, and explicit termination semantics.
- `materials-*.profile-input.json` preserves starting-model force residuals,
  chemical-system coverage, and reference-label cost.
- `legal-*.profile-input.json` preserves readiness, eligible-response
  availability, reward discrimination, token cost, truncation, reliability,
  and missingness. LAB regression risk remains a separate evaluation record.

Coordinate definitions are compared only within a compatible domain, starting
subject, and measurement contract. The CLI does not compare robotics success
variation with a materials residual or infer an optimal environment from either
fixture.

```bash
anarres measure examples/environment-profiles/robotics-a.profile-input.json \
  --output .anarres/robotics-a.profile.json
anarres measure examples/environment-profiles/robotics-b.profile-input.json \
  --output .anarres/robotics-b.profile.json
anarres design .anarres/robotics-a.profile.json .anarres/robotics-b.profile.json
```
