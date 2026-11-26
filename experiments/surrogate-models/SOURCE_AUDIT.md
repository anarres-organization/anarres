# Released-source audit

This audit identifies current Anarres studies that may support surrogate-model
research. A released outcome is necessary but not sufficient. Each source must
also expose candidate membership, prediction-time inputs, intervention
identity, target identity, costs, and grouping relationships.

| Program | Released evidence | Initial use | Main limitation |
| --- | --- | --- | --- |
| [Mathematics](../mathematics/) | Four model scales, four candidate environments per scale, two training seeds, and matched token budgets | Curve prediction and leave-one-scale-out ranking under one trainer | Only 16 scale-environment candidate units, each with two seed trajectories; the four labels recur by construction; the uniform-mixture test shows a composition-transfer failure |
| [Robotics](../robotics/) | Prospective PushT, Can, and Square panels plus retrospective multi-source comparisons | Within-panel ordering, regression events, abstention, and cost-aware replay | Simulators, policies, candidate definitions, and success endpoints differ across studies |
| [Materials science](../ai-for-science/materials-science/) | Retrospective public panels and a scored MLIP prospective test | Large retrospective ordering audit and one controlled prospective panel | Publication-conditioned panels are heterogeneous and cannot be treated as exchangeable training interventions |
| [Molecular design](../ai-for-science/molecular-design/) | Prospective RxnFlow environment selection and acquisition panels | Acquisition baselines and sequential label-budget replay | Assay acquisition predicts molecular labels, while the proposed surrogate predicts training-intervention utility; these are different decision levels |
| [Legal reasoning](../legal/) | Prospective SylloGym comparison and separate LAB regression-risk study | Abstention, regression-risk endpoints, and a small prospective panel | SylloGym has few candidates and uncertain differences; LAB contains one training intervention rather than a candidate-environment panel |
| [Agentic finance](../finance/) | Retrospective candidate-target panels and held-out source tests | Target-conditional ordering and regression-risk replay | No prospective environment-selection outcome has been released |

Formal verification, vulnerability exploitation, and customer-support agents
currently provide qualification or pre-training measurement evidence but no
released candidate-environment training comparison suitable for the first
replay benchmark. They may become prospective targets; they should not be
converted into surrogate labels before downstream interventions are complete.

## Readiness requirements

A source enters the replay benchmark only if all of the following can be
reconstructed without inference from prose:

- one complete candidate panel under a declared comparison contract
- the starting policy and target for that panel
- candidate information available at the prediction cutoff
- one identified downstream outcome per intervention arm
- grouping keys for seeds, checkpoints, tasks, and repeated evaluations
- infrastructure validity distinct from scientific outcome
- candidate-training and evaluation cost, or an explicit missing-cost marker
- chronology sufficient to exclude post-outcome fields from predictor inputs

The first implementation task is a read-only inventory that checks these fields
and reports missingness. It must not manufacture a common utility value or fill
missing costs with zero.

## Independent units

The independent unit is an intervention arm: one independently trained policy
under one candidate environment and training contract. Evaluation tasks,
criteria, targets, checkpoints, and repeated samples remain nested under that
arm. Training seeds may be modeled as repeated intervention arms when training
is independently rerun, but panel-level splitting keeps every seed and
checkpoint lineage together.

For transfer evaluation, the split unit is larger than the intervention arm:

- leave-one-scale-out for a scale-transfer claim
- leave-one-source-family-out for a source-transfer claim
- leave-one-study-out for a new-study claim
- leave-one-domain-out only for a cross-domain claim

Counts of tasks, checkpoints, or target rows must not be presented as counts of
independent training interventions.

## Recommended first release

The first release should include only panels that pass the readiness audit and
should publish an exclusion table for the rest. Mathematics is the clearest
single-study curve test. Robotics and the prospective materials panel provide
more varied candidate panels for decision replay. Other programs can be added
after their native records pass the same audit.

