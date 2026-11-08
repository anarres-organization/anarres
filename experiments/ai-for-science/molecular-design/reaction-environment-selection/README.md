# Prospective selection of molecular graph experience

**Status:** RxnFlow and MolGenBench code revisions qualified. The MolGenBench
dataset, target reward, common warm start, and candidate memberships remain
open. No training or evaluation outcome has been inspected for this study.

## Research question

This study asks whether a short sweep under a starting molecular graph policy
can predict which replay experience bank will produce the greatest
target-specific improvement at a fixed generation and oracle budget. The
decision concerns training experience rather than a static molecular library:
which synthesized trajectories should a policy learn from when every arm uses
the same target, action space, reward, and trainer?

The study uses RxnFlow v2.1.0 as the reaction-based graph policy and
MolGenBench Version4 as the planned target-evaluation contract. The first loop
is computational. It measures virtual-screening utility and makes no claim
about biological efficacy without experimental validation.

## Why the graph structure matters

Reaction trajectories contain information that a scalar reward cannot
represent. Two experience banks can have similar docking scores and costs while
covering different scaffolds, ring systems, reaction families, route depths,
and regions of the policy's graph representation. The central comparison asks
whether these graph-aware measurements improve prediction beyond reward signal,
validity, reliability, and oracle cost.

The first graph claim concerns environment measurement and selection. A
GINE-versus-GPS architecture comparison remains a later nested study. Deferring
that ablation keeps the initial intervention focused on experience and avoids
multiplying eight environments across separately initialized models.

## Research-first progression

The study advances through five gates.

1. **Qualify the public sources.** Pin code revisions, verify construction
   fixtures, record licenses, and keep target outcomes sealed.
2. **Qualify the target and starting policy.** Verify the MolGenBench archive,
   select a target without outcome access, validate the docking reward, and
   train one common QED warm start.
3. **Measure and freeze experience banks.** Generate two independent probe
   views under the starting policy, audit coordinate reliability, and serialize
   six development banks plus two prospective banks.
4. **Run matched post-training.** Keep the checkpoint, action space, reward,
   online sampling, replay ratio, optimizer, and budgets fixed. Only the
   preloaded replay bank changes.
5. **Open and score target outcomes.** Compare complete utility curves,
   prospective pair ordering, allocation regret, uncertainty, and the
   incremental value of graph-aware measurements.

An earlier gate cannot be repaired after downstream outcomes are opened. A
failed source, oracle, signal, or reliability gate yields an abstention or a
new versioned protocol.

## Fixed intervention contract

RxnFlow supports online trajectories and replay experience. The cleanest first
intervention therefore uses one fixed molecular construction space and varies
only replay-bank membership. Changing building-block catalogs or reaction
templates across arms would alter the action space and could make a common
checkpoint incompatible with some environments.

Every intervention arm shares:

- one RxnFlow v2.1.0 GINE-style starting policy
- the qualified 5,000-building-block example catalog
- 4 unimolecular and 26 bimolecular reaction templates with 28 synthon types
- one outcome-blind MolGenBench target and target-reward contract
- one online sampling, replay, optimizer, and update contract
- three matched generated-action and oracle budgets
- two prespecified training seeds
- one frozen evaluation contract.

The experience banks have equal membership. Overlap in molecule identity,
scaffold, reaction family, and graph representation is reported before
training.

## Candidate panel

Six banks support model development.

| Development bank | Starting-policy information |
| --- | --- |
| Hash-uniform | Trajectory identity only |
| Reward signal | Reward variation with deterministic diversity and cost ties |
| Validity and cost | Valid products and successful oracle calls per generated action |
| Scaffold coverage | Bemis-Murcko scaffolds and ring systems |
| Route coverage | Reaction families and route depth |
| Graph-embedding coverage | Frozen starting-policy molecular representations |

After development outcomes are scored, the operational and graph-aware
predictors are frozen. Two untouched banks then form the prospective decision.

| Prospective bank | Frozen information |
| --- | --- |
| Operational hybrid | Reward signal, reliability, validity, and oracle cost |
| Graph-aware hybrid | Operational coordinates plus scaffold, ring, reaction, route, and representation coverage |

The prospective freeze records both bank memberships, complete utility curves,
their ranking at every budget, an uncertainty interval, and an abstention rule
before either bank is trained.

## Outcome contract

Raw docking score is not the primary endpoint. The primary outcome is the
fraction of unique molecules that pass a frozen multi-gate qualifying-hit
contract. The contract combines target docking with molecular validity,
drug-likeness and chemical filters, pose validity, strain, clash, and target
interaction criteria. Supporting MolGenBench metrics retain QED, synthetic
accessibility, uniqueness, molecular and scaffold diversity, PoseBusters
validity, strain energy, RMSD, interaction score, and clash score.

Known actives are reserved for oracle validation and hit-recovery reporting.
They do not select the target, construct an experience bank, or tune the
predictor. A prospective result is scored only after every expected arm,
budget, and seed passes identity, completeness, and infrastructure-validity
checks.

## Frontier alignment

RxnFlow provides a maintained synthesis-aware molecular policy, and its public
v2.1 release supports external target conditioning and objective preferences.
HSX extends this policy family to large-scale multi-objective generation with
experimental validation. MolGenBench shows why a broader endpoint is needed:
target docking, pose realism, chemical filters, synthesizability, and
interaction quality can disagree. Current closed-loop work at OpenAI and
Anthropic further motivates a progression from computational selection to
experimental feedback when the first utility loop succeeds.

Primary sources:

- [RxnFlow paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/24d36eee157559e0d2549455fba28f6a-Paper-Conference.pdf),
  [v2.1.0 release](https://github.com/SeonghwanSeo/RxnFlow/releases/tag/v2.1.0),
  and [source](https://github.com/SeonghwanSeo/RxnFlow)
- [MolGenBench paper](https://www.nature.com/articles/s41467-026-78105-8),
  [source](https://github.com/Intelligent-Drug-Discovery-Lab/MolGenBench),
  and [Version4 data record](https://doi.org/10.5281/zenodo.20233505)
- [HSX](https://www.biorxiv.org/content/10.64898/2026.10.01.755933v1.full)
- [OpenAI cell-free protein synthesis study](https://openai.com/index/gpt-5-lowers-protein-synthesis-cost/)
- [Anthropic drug-development collaborations](https://www.anthropic.com/research/early-progress-drug-development)

These sources establish relevance and evaluation requirements. They do not
establish that the planned predictor works.

## Current qualification state

The committed source audit verifies the exact RxnFlow release, source license,
5,000 unique example building blocks, 30 reaction templates, and 28 synthon
types. It also verifies the pinned MolGenBench evaluator code, MIT license, and
two public test fixtures. Zenodo records the 5.38 GB Version4 archive under CC
BY 4.0 and publishes its MD5 digest. The archive has not been downloaded or
inspected, so its SHA-256 digest and content inventory remain open.

The next valid action is source and oracle qualification on a CPU node. No GPU
training is justified until the target-reward adapter, common warm start, and
starting-policy headroom pass their gates.

## Reproduction

[`SOURCES.json`](SOURCES.json) records the pinned public inputs.
[`SOURCE_AUDIT.json`](SOURCE_AUDIT.json) contains only source-code hashes and
construction-fixture counts. [`PROTOCOL.json`](PROTOCOL.json) fixes the study
structure while listing every open gate.

Audit local checkouts without reading target outcomes:

```bash
python scripts/audit_source.py \
  --rxnflow-repo /path/to/RxnFlow \
  --molgenbench-repo /path/to/MolGenBench \
  --out /tmp/reaction_source_audit.json
```

Validate the protocol:

```bash
python scripts/validate_protocol.py
```

[`RUNBOOK.md`](RUNBOOK.md) gives the authorized order from source
qualification through the prospective freeze. It stops before claim-bearing
training.
