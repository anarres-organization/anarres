# Materials residual audit v1

- Stability: development
- Revision: `v1-development`
- Scope: a frozen starting interatomic potential evaluated on a candidate set
  with reference energy and force labels

This convention supports the synthetic CLI fixture. A real adapter must retain
structure identity, composition, reference method, physical units, split role,
and starting-model revision in its native evidence.

## `force_residual_rmse`

Root mean squared difference between starting-model and reference force
components over retained structures. Unit: `electronvolt_per_angstrom`. Its
direction is contextual because both negligible and extreme residuals can be
uninformative for a finite training budget.

## `chemical_system_coverage`

Normalized effective count over the declared chemical-system labels. Unit:
`normalized_effective_system_count`. The adapter must define the label and
weighting rule in its measurement contract.

## `reference_label_cost`

Number of structures requiring reference labels for the candidate. Unit:
`reference_structures`. This is a count, not a hardware-independent estimate of
wall-clock or monetary cost.
