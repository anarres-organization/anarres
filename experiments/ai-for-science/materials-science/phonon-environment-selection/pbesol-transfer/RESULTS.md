# Prospective PBEsol transfer result

## Result

The earlier PBE ordering transferred partially to the independently frozen
PBEsol panel. It selected the best candidate at two of three post-training
budgets and achieved 72.2% pairwise agreement with the complete frozen orders.
Mean allocation regret was 5.5 percentage points of Top-100 stable rate.

| DFT post-training budget | Frozen best | Observed best | Frozen-best rate | Best rate | Regret | Order agreement |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 256 | coverage | coverage | 71.5% | 71.5% | 0.0 pp | 50.0% |
| 512 | coverage | hash-uniform | 59.5% | 76.0% | 16.5 pp | 83.3% |
| 1,024 | hash-uniform | hash-uniform | 70.5% | 70.5% | 0.0 pp | 83.3% |

The two seeds agreed on the winning candidate at 512 and 1,024 structures. At
256 structures, one seed favored hash-uniform and the other favored coverage.
The 512-structure miss is therefore the largest and clearest failure of the
transferred ordering.

## Absolute performance

The panel contains 359 dynamically stable structures under the source's
$-0.1$ THz threshold. The starting checkpoint reaches a 76.0% Top-100 stable
rate, and the full-data DFT-post-trained reference reaches 75.0%. No candidate
improves on the starting checkpoint's Top-100 rate. The best candidate matches
it at 512 structures and falls below it at the other budgets.

| Candidate | 256 | 512 | 1,024 |
| --- | ---: | ---: | ---: |
| hash-uniform | 68.5% | **76.0%** | **70.5%** |
| signal | 64.0% | 58.0% | 58.5% |
| coverage | **71.5%** | 59.5% | 64.5% |
| signal + coverage | 66.0% | 56.5% | 65.0% |

Values are two-seed mean Top-100 stable rates on the same 1,000-structure
panel. The non-monotonic budget response and the absence of absolute gain show
that a training-data rule can retain useful relative information while failing
to improve transfer to a new functional and workflow.

## Interpretation

This experiment tests a real prospective decision. The candidate memberships,
training runs, complete PBE-derived orderings, PBEsol panel, and every checkpoint
prediction were fixed before PBEsol labels were opened. The 256- and
1,024-structure decisions transfer, while the 512-structure decision does not.
The result supports partial transfer of environment rankings across DFT
workflows, not a general claim that the selected post-training data improves
PBEsol screening.

The boundary is also informative. Most panel structures appeared in the
starting checkpoint's MatterSim-labeled pretraining corpus, but the PBEsol
phonon outcomes and workflow were new. The panel is disjoint by material
identity and reduced composition from the claim-bearing DFT post-training
reservoir and earlier DFT test panel. A future test should construct candidates
from measurements tied more directly to cross-functional robustness rather
than copying the PBE ordering unchanged.

## Integrity

The scorer verified the PBEsol shard checksum, panel freeze, evaluation
contract, launch manifest, committed prediction manifest, all 24 candidate
completion records, both reference completion records, and every prediction
file before opening any outcome. Two independent executions produced identical
files with SHA-256
`5680ce844d5917daa08c33fbac66f7c86efe5921c9b77909d53b50d7adb2b397`.
The canonical score digest recorded inside the artifact is
`f012887c7f8b1652f6d0579e9cd3c198f71c8c676a6c66f0ee33060b706fe3ff`.
