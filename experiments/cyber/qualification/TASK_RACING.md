# Matched-task sequential comparison of raw variation and token yield

An exploratory extension of the conditional Bernoulli calculations. No CyberGym outcomes are used, no new Level-2 estimate is claimed, and no training-utility claim is made.

## Estimands and proof

For each complete matched task pair, the two environments provide G binary rewards and the total generated output tokens L. Let M = 2k(G-k)/(G(G-1)), the raw absolute LOO advantage per rollout, and C=L/(G B), where B is the frozen per-rollout token cap. Both lie in [0,1], and C>0. The repository's raw token yield is 10^6 E[M]/(B E[C]), estimated descriptively by the corresponding ratio of sums. Unlike a pooled success rate, this preserves task clusters and the token denominator. Admission filters and token weighting are not modelled. Under conditionally iid binary draws, M/2 estimates within-task reward variance; without that assumption it is only observed raw variation.

For independent identically distributed matched tasks, the normalized variation difference is M_B-M_A. For two independent task pairs i,j define X = (M_Bi C_Aj - M_Ai C_Bj + M_Bj C_Ai - M_Aj C_Bi)/2. X is in [-1,1]; its expectation equals E[M_B]E[C_A]-E[M_A]E[C_B]. Its sign identifies the raw yield ordering because both expected token denominators are positive. Cross-task products avoid the covariance error in multiplying mass and length measured on the same task.

Process disjoint adjacent blocks of two independent tasks, in frozen order. For each endpoint, under the directional null E[X | past] <= 0, each product of (1+lambda X), 0<lambda<1, is a nonnegative supermartingale. A fixed equal-weight mixture remains a supermartingale. Ville's inequality bounds the probability of crossing 2/alpha_endpoint for either direction by alpha_endpoint via a union bound. Use alpha/2 for each endpoint, giving joint familywise error at most alpha. This is a finite-sample anytime-valid test, not an estimate of power or an optimal allocation theorem. Correlated task clusters, adaptive task selection, verifier changes and non-frozen token caps invalidate the stated contract.

## Synthetic regression evidence

8 unit tests passed locally. Four synthetic scenarios (400 replications each, 300 matched task pairs maximum, G=8, cap=100, fixed seed, family alpha=.05):

| Scenario | Variation rejection | Raw-yield rejection | Mean stop among yield rejections |
|---|---:|---:|---:|
| heterogeneous mirror rates, same token count | 0/400 | 0/400 | — |
| same conditional reward law, 720 vs 120 tokens | 1/400 | 400/400 | 64.305 task pairs |
| unequal expected raw mass but equal token yield | 400/400 | 0/400 | — |
| all repeats perfectly dependent | 0/400 | 0/400 | — |

The simulations are diagnostic only, not universal power guarantees. Tests enumerate small paths under asymmetric mean-zero laws, check exact expectation by enumeration, validate raw mass against the repository equation, reject duplicate task IDs and exceeded caps, and preserve first crossing. The reference simulation script is included separately. Full repository make check has not been run in the isolated execution environment; no prospective data were accessed.

Next: freeze a level-2 measurement contract with independent task/project clusters, record full generated lengths including failed attempts, and compare to fixed-horizon cluster-level inference at matched cost. A lack of rejection is not an equivalence claim.
