# Predictable utility of formal-verification environments

Formal-verification environments differ in proof language, repository context,
tool access, verifier behavior, and interaction cost. This workstream asks:

> For a fixed starting policy, target, tool setup, and budget, which training
> environment is expected to produce the greatest held-out improvement?

## Evidence at a glance

| Evidence | Result | Present boundary |
| --- | --- | --- |
| [Dafny and Verus training comparisons](public-evidence/README.md) | Verifier-filtered DafnySynth augmentation improves seven of eight matched comparisons and ties the eighth. Other studies show gains from target-matched data and verified feature coverage. | The studies use different models, verifiers, and outcomes, so their scores are not pooled. |
| [Vero source qualification](VERO_SOURCE_QUALIFICATION.md) | The pinned source, Lean runtime, reference build, grader controls, and repository-disjoint split pass qualification. | Qualification establishes a usable source and runtime, not a successful policy probe. |
| [Leanstral support screen](STARTING_POLICY_PROBE.md) | Leanstral produced no verified support under the frozen probe and budget ladder. | No training run is justified for that policy and environment. |
| [GPT-5.6 development screen](STARTING_POLICY_SELECTION.md) | One excluded development attempt solved all nine PrimePy specifications under fresh grading. | The current sandbox exposes more of the repository than intended and must be tightened before repeated measurement. |

A **support screen** asks whether the starting policy can produce any verified
success. **Containment** limits the model to the task workspace and approved
tools. **Fresh grading** reruns the verifier from a clean workspace rather than
trusting files left by the model.

## Start here

Install the formal-verification adapter from the repository checkout, then
inspect the released evidence and runtime qualification:

```bash
uv tool install ./data/formal-verification/vero
anarres formal status --repository .
anarres formal qualify-source --help
anarres formal qualify-runtime --help
anarres formal qualification --repository .
```

`qualify-source` checks the pinned Vero checkout. `qualify-runtime` verifies the
Lean toolchain, package lock, reference build, allowed tools, filesystem rules,
and resource limits without contacting a model. The `qualification` report
keeps the one-policy development result separate from the negative Leanstral
measurement.

## What the public evidence shows

The [public-evidence record](public-evidence/README.md) reconstructs decisions
from DafnySynth, VeruSyn, Re:Form, Formal Disco, and Vericoding, then audits
policy support in LeanLean, Vero, and Forall VeriSoftBench. Together these
studies show that:

- verifier-filtered and target-matched experience can improve downstream proof
  synthesis
- high raw verifier success can still select semantically weak specifications
- policy rankings change with the harness, objective, verifier, budget, and
  cost measure
- infrastructure failures and invalid proofs must remain separate from
  ordinary unsuccessful attempts.

These are complementary results, not one interchangeable benchmark score.

## What counts as an environment

A formal-verification environment includes the tasks and the executable system
that turns model actions into verifier feedback. A complete record fixes:

1. task identities, source revisions, and dependency closure
2. agent-visible files, tools, and repository state
3. build, proof-check, timeout, reset, and containment behavior
4. reward components and rules for invalid outputs
5. the starting policy, decoding setup, and interaction budget
6. the held-out repositories and protected capabilities used for evaluation.

A compiling file is not automatically correct. The verifier must reject
`sorry`, unapproved axioms, changed theorem statements, weakened
specifications, hidden reference proofs, and vacuous claims.

## Scientific target

For environment distribution $E$, starting policy $\pi_0$, fixed budget $C$,
and target vector $D$, utility is

$$
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D).
$$

The target keeps machine-checked completion, specification coverage, protected
capabilities, generated tokens, wall time, and verifier cost distinct. A new
training comparison must freeze candidate environments, predictions, budgets,
and evaluation rules before downstream outcomes are opened.

## Current boundary and next step

Vero is a qualified source with a model-free runtime preflight and one positive
development support result. Its reinforcement-learning utility remains
unvalidated. The next step is to enforce task-only containment, rerun the
negative controls, and repeat the support measurement under the corrected
workspace boundary. Training remains gated on that result.

Detailed records:

- [experiment plan](EXPERIMENT_PLAN.md)
- [source landscape](SOURCE_LANDSCAPE.md)
- [starting-policy probe](STARTING_POLICY_PROBE.md)
- [policy requalification](POLICY_REQUALIFICATION.md)
- [containment requalification](CODEX_CONTAINMENT.md)
- [continuation guide](CONTINUATION.md)
