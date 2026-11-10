# Molecular reaction-bank measurement v1

- Stability: development
- Revision: `v1-development`
- Scope: fixed replay banks constructed from a frozen RxnFlow starting policy

This convention describes one target-specific molecular experience bank before
post-training. The native study fixes the RxnFlow policy, synthesis environment,
MolGenBench target, docking and eligibility contract, bank size, and two-view
confirmation rule. A profile exposes construction-view summaries for one bank.
The independent view qualifies the stability of the six-bank ordering and does
not contribute members or get averaged into a coordinate.

All coordinates use the 512 unique molecules in the frozen construction-view
bank. The direction of reward and coverage coordinates is contextual because
their relationship to downstream policy utility has not yet been evaluated.
Lower generated-action and oracle costs retain their direct operational
interpretation.

## `mean_target_reward`

Arithmetic mean of the frozen Q07820 terminal reward. The reward is
`max(-vina_affinity, 0) * QED` after the study's molecular eligibility and
failure contract. Unit: `docking_qed_reward`. A molecule-specific eligibility or
conformer failure is preserved as an explicit scientific zero in the native
probe and remains outside the eligible bank pool. A ligand atom type rejected
by the pinned Vina parser is also explicit scientific ineligibility. Every
other parser, receptor, toolchain, docking-process, and timeout failure remains
an infrastructure failure and cannot enter a bank or this mean as zero. Role:
`target_affinity`. Sample unit: eligible bank molecule. Direction: contextual
until downstream utility is scored.

## `mean_generated_action_count`

Arithmetic mean number of molecular construction actions in a sampled RxnFlow
trajectory. Unit: `generated_molecular_actions_per_trajectory`. Role: `cost`.
Sample unit: bank trajectory. Direction: lower.

## `mean_oracle_seconds`

Arithmetic mean selected-target oracle wall time among bank members. Unit:
`seconds_per_molecule`. This is realized wall time under the pinned oracle
runtime rather than a hardware-independent compute measure. Role: `cost`.
Sample unit: eligible bank molecule. Direction: lower.

## `unique_scaffold_fraction`

Number of distinct achiral Bemis--Murcko scaffolds divided by bank size. Acyclic
molecules use the study's explicit sentinel. Unit: `fraction`. Role:
`coverage`. Sample unit: bank. Direction: contextual.

## `unique_ring_systems_per_record`

Number of distinct connected ring-system signatures divided by bank size. Rings
belong to one system when they share at least one atom. Unit:
`ring_systems_per_record`. Role: `coverage`. Sample unit: bank. Direction:
contextual.

## `unique_route_fraction`

Number of distinct ordered reaction-name sequences divided by bank size. Unit:
`fraction`. Role: `coverage`. Sample unit: bank. Direction: contextual.

## `unique_reaction_families`

Count of distinct reaction families represented by the bank. Unit:
`reaction_families`. Role: `coverage`. Sample unit: bank. Direction:
contextual.

## `embedding_mean_nearest_neighbor_distance`

Arithmetic mean nearest-neighbor Euclidean distance within the bank after the
frozen RxnFlow GINE state embeddings are centered on the eligible construction
pool, projected by deterministic full SVD onto at most 32 nonzero components,
scaled by the retained singular values, and L2-normalized. Unit:
`normalized_embedding_distance`. Role: `coverage`. Sample unit: eligible bank
molecule. Direction: contextual.

## Readiness and edge cases

A bank is ready for profile comparison only when source, target, starting-policy,
measurement-reliability, and bank-confirmation checks pass under matching
contracts and seeds. The adapter rejects missing memberships, nonfinite values,
digest mismatches, and any record that opened target-training outcomes. No
uncertainty interval is exported because the native study estimates ordering
stability across views rather than coordinate-level sampling intervals. Profile
conformance does not establish that any coordinate predicts post-training
utility.
