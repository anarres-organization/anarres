# Materials MLIP candidate measurement v1

- Stability: development
- Revision: `v1-development`
- Scope: equal-atom OMat24 candidate environments measured under the frozen
  Nequix-MP-1 starting potential before candidate post-training

This convention projects the released MLIP phonon candidate bank into Anarres
environment profiles. The native candidate-bank artifact remains authoritative.
Profiles contain measurements made before candidate training and exclude
development or prospective phonon outcomes.

The measurement contract uses one deterministic starting-model evaluation per
retained structure. Every candidate contains exactly 50,000 processed atoms and
at most one configuration from each OMat24 parent. Candidate membership is
identified by the SHA-256 digest of its ordered native structure identities.

## `signal_density_per_atom`

Loss-weighted starting-model residual mass divided by processed atoms. For one
structure with atom count $n$, mean force-vector residual $r_f$, and mean
absolute stress residual $r_s$, the native mass is

$$
A = 20 n r_f + 5 r_s.
$$

The candidate coordinate is $\sum A / \sum n$. Its unit is
`loss_weighted_residual_per_atom`, its estimator is the atom-normalized sum over
retained structures, and its direction is contextual. The coefficients are
part of the frozen measurement contract and do not make force and stress
residuals physically interchangeable.

## `effective_signal_coverage`

Normalized effective sample size of the structure-level signal masses. For
$m$ retained structures with masses $A_i$,

$$
H = \frac{(\sum_i A_i)^2}{m\sum_i A_i^2}.
$$

The value lies between zero and one, with zero defined when total mass is zero.
Its unit is `fraction`, its estimator is the normalized effective sample size,
and its direction is contextual until downstream candidate outcomes validate a
decision rule.

## `chemical_system_entropy`

Normalized Shannon entropy over the retained structures' element-set labels.
The unweighted label frequency is used, and the entropy is divided by the log
of the number of observed labels. The value is zero for one observed label and
lies between zero and one otherwise. Its unit is `fraction`, and its direction
is contextual.

## `mean_target_affinity`

Arithmetic mean of each retained structure's maximum element-set Jaccard
similarity to the 16 checkpoint-qualification targets. Only element identities
from the qualification split enter this measurement. Development and
prospective phonon outcomes did not enter its construction. Its unit is
`fraction`, and its direction is contextual.

## `neighbor_edges_per_atom`

Total Nequix neighbor edges divided by processed atoms for the candidate. This
is a model- and cutoff-specific compute proxy, not a universal hardware-cost
estimate. Its unit is `neighbor_edges_per_atom`, and lower values indicate less
graph-processing work under the frozen model-input contract.

## `processed_atom_budget`

Total atom instances in the candidate environment. Its unit is
`processed_atoms`, and all profiles in the released draft equal 50,000. This
coordinate records the matched primary data budget. It does not imply that
neighbor-edge cost is matched.

## Qualification and edge cases

The adapter requires the pinned OMat24 source qualification, Nequix-MP-1 model
hash, frozen Alexandria target roles, overlap audit, complete 80,000-record
measurement validation, and the outcome-blind candidate-bank artifact. Missing
or nonfinite measurements fail export. Zero measurements are preserved.

The published bank remains a measurement-only draft. Its candidates are valid
for comparing pre-training coordinates, while the final training panel remains
unfrozen because neighbor-edge cost varies across candidates. This condition is
reported as a warning and never converted into a downstream outcome.
