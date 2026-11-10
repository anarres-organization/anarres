# Robotics CUPID candidate measurement v1

This convention describes pre-training measurements for candidate demonstration
sets in the prospective RoboMimic Can v1.4.1 study. It preserves the study's
native CUPID influence rankings, operator tiers, and demonstration lengths. It
does not reinterpret them as RLVR advantage mass or as downstream policy
performance.

## Measurement subject and contract

The subject is the three-checkpoint scoring-policy ensemble frozen by the
study. Each checkpoint produces a CUPID performance-influence score for every
demonstration using closed-loop rollouts that contain both successes and
failures. The native pipeline converts each checkpoint's scores to ordinal
ranks, averages those ranks by demonstration, and freezes candidate membership
before candidate-policy outcomes are opened.

Profiles are comparable only when they share the same source dataset digest,
scoring-policy ensemble, aggregation rule, adapter revision, and complete
coordinate definitions.

## Coordinates

### `mean_cupid_rank_percentile`

For demonstration $i$, let $r_{si}\in\{0,\ldots,n-1\}$ be its ordinal CUPID
rank at scoring checkpoint $s$, with larger ranks denoting larger influence
scores. For candidate $E$,

$$
R(E)=\frac{1}{|E|(n-1)}\sum_{i\in E}\frac{1}{S}\sum_{s=1}^{S}r_{si}.
$$

The unit is rank percentile, the sample count is the number of selected
demonstrations, and ties follow the frozen numeric demonstration-ID rule. This
coordinate measures the candidate's position under the pre-training influence
estimator. Its direction is contextual until candidate outcomes test whether
higher ranks imply greater downstream utility.

### `operator_tier_effective_coverage`

Let $n_k(E)$ be the number of selected demonstrations from operator tier $k$
for the three frozen tiers. Coverage is

$$
T(E)=\frac{(\sum_k n_k(E))^2}{3\sum_k n_k(E)^2}.
$$

The value lies in $(0,1]$ for a nonempty candidate and equals one when the three
tier counts are equal. It measures coverage of the released operator strata,
not semantic task diversity.

### `mean_demonstration_action_steps`

This is the arithmetic mean of the official episode lengths for the selected
demonstrations. Its unit is action steps per demonstration. It is a property of
the candidate data, not the equal optimizer-step budget used for candidate
training.

### `measurement_rank_reliability`

This is the mean of the three pairwise Spearman correlations among the ordinal
rank vectors from the three scoring checkpoints. It is shared by candidates
from one freeze because it qualifies the measurement procedure, not an
individual subset.

## Qualification and edge cases

The closed-loop probe must contain both success and failure episodes at every
scoring checkpoint, every candidate membership digest must match the frozen
record, and the reliability gate must satisfy its preregistered Spearman and
top-half Jaccard thresholds. Failed checks remain failed qualification states;
they are never converted into zero-valued rewards or imputed coordinates.

An empty candidate has no valid profile. Nonfinite influence scores, missing
demonstrations, inconsistent episode lengths, opened candidate outcomes, and
source or protocol digest mismatches invalidate export. Zero or negative
finite measurements remain valid when a future native record defines them;
the adapter does not clamp measured values.

## Scientific boundary

The five profiles are native pre-outcome measurements for one simulated
manipulation task. CLI conformance shows that the candidates can be compared
without losing their robotics semantics. It does not establish that CUPID
rank, tier coverage, or action length predicts candidate-policy utility. That
claim requires the separately gated outcome comparison.
