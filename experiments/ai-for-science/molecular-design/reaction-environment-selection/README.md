# Prospective selection of molecular graph experience

**Status:** RxnFlow, MolGenBench code, the Version4 archive, an eight-target
qualification panel, its 24 structural fixtures, and reference docking on all
eight targets are qualified, together with the common synthesis environment and
the 1,000-update QED warm start. Two frozen starting-policy views were scored
against all eight targets. Every target passed the prespecified gates, and the
outcome-blind hash rule selected Q07820. The structured reward adapter passes valid,
malformed, filtered, timeout, repeat-call, batched, and RxnFlow v2.1 interface
checks. Version 3 measurement passes. The six construction-view memberships
are recorded. The complete-order Version 3 confirmation fails for generated
action cost, oracle time, and scaffold coverage, while the frozen Version 4
selector-fidelity confirmation passes all eight checks in both independent
views. The candidate-bank gate now authorizes freezing the matched training
and evaluation contracts. No target-training or evaluation outcome has been
inspected for this study.
The selected-target measurement extractor is qualified on the frozen 64-record
view with byte-identical graph representations across two independent runs.
The first large-batch scoring attempt stopped on a molecule-specific conformer
failure before producing candidate measurements. The version 2 reward contract
keeps the sampled views fixed, adds one deterministic conformer fallback, and
records fallback exhaustion as a scientific zero while preserving strict
infrastructure failures for the receptor, toolchain, Vina, process, and timeout.
The resulting version 2 views passed every signal, throughput, graph, and
cross-view stability check but failed the prespecified 0.90 unique-product
fraction in both views. That failed gate is preserved. Version 3 replaces the
fraction-only condition with an absolute support requirement of 2,048 unique
products and a 0.80 fraction floor, then tests both on two new independent views
before any bank membership or training outcome exists.
Those new views contain 3,367 and 3,436 unique canonical products, and every v3
per-view and two-view check passes. A subsequent audit found that the original
bank contract still named the failed v2 view seeds. Its bank-summary result is
preserved as non-authorizing. Version 2 binds the passing construction view and
a new untouched confirmation seed without changing the selectors or gate.
The first scoring attempt on that view encountered three boronic-acid products
outside the pinned Vina atom-type domain. The failure is preserved. Version 3
keeps the exact sampled view and records only Vina's exact unsupported-atom-
type error as scientific ineligibility; every other parser, receptor,
toolchain, process, and timeout failure remains an infrastructure failure.
The unchanged view then completes with no infrastructure failures. Five of the
eight bank-order coordinates pass, while generated-action cost, oracle time,
and scaffold coverage reach Spearman correlations of 0.371, 0.657, and 0.735,
below the frozen 0.8 threshold. This result triggers the prespecified
abstention before development training.
The version 3 failure remains preserved. A
pre-training diagnostic shows that all eight intended selector contrasts pass
in both frozen views, while the failed statistic also ranks banks that were not
designed to optimize each coordinate. Median or size-normalized oracle time and
generic Murcko scaffolds do not repair that complete ordering. Version 4 keeps
the construction memberships, selectors, estimators, and runtime unchanged. It
freezes a selector-fidelity gate against the neutral hash bank before drawing
one new confirmation view. That untouched view produces 4,029 valid scores and
67 molecule-specific scientific zeroes with no infrastructure failure. All
eight selector-fidelity checks pass in both views, authorizing the next
pre-outcome step without opening a target-training result.

## CLI projection

Install the native CLI and molecular adapter from a repository checkout:

```bash
cargo install --path crates/anarres-cli --locked
uv tool install ./experiments/ai-for-science/molecular-design/reaction-environment-selection
anarres adapter doctor molecular
```

The adapter exports the six construction-view banks as Anarres environment
profiles with eight reaction-bank coordinates:

```bash
anarres molecular status --repository . --json
anarres molecular profile --repository . \
  --output-dir .anarres/molecular-q07820
anarres qualify .anarres/molecular-q07820/q07820-hash_uniform.profile-input.json --json
anarres measure .anarres/molecular-q07820/q07820-hash_uniform.profile-input.json \
  --output .anarres/molecular-q07820/q07820-hash_uniform.profile.json
```

Each profile preserves the native contracts and artifact digests. The profiles
are schema-valid and carry the passing selector-fidelity qualification. This
gate authorizes freezing matched training and evaluation contracts; it does
not itself establish predictive utility or open target-training outcomes.
The adapter accepts an explicit `--repository` path, so the installed command
can run outside the checkout without searching for mutable evidence.

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
   freeze an eight-target qualification panel, validate the docking reward and
   common QED warm start on that panel, then select one source-valid,
   repeatable, and nondegenerate target without using post-training outcomes.
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

- identical weights from one RxnFlow v2.1.0 GINE-style starting policy
- the qualified 5,000-building-block example catalog
- 4 unimolecular and 26 bimolecular reaction templates with 28 synthon types
- one outcome-blind MolGenBench target and target-reward contract
- one online sampling, replay, optimizer, and update contract
- three matched generated-action and oracle budgets
- two prespecified training seeds
- one frozen evaluation contract.

The QED warm start contributes model weights only. Each target-training arm
starts with a fresh optimizer, scheduler, random-number state, and empty replay
buffer before its frozen bank is loaded. This prevents QED replay history or
optimizer state from becoming an unrecorded part of the intervention.
The weights-only handoff is implemented by
[`scripts/warm_start_weights.py`](scripts/warm_start_weights.py). Its interface
smoke preserves policy and sampling weights exactly while leaving the receiving
trainer at step zero with empty optimizer and replay state.

The preloaded bank remains fixed during target training. Fresh online
trajectories enter the common update batch but are not inserted into replay.
Every arm therefore receives the same number of online and replay trajectories
per update while retaining its selected experience distribution. Probe
generation and target-oracle cost are reported separately from post-training
compute.

The experience banks have equal membership. Overlap in molecule identity,
scaffold, reaction family, and graph representation is reported before
training.

`TARGET_SELECTION_CONTRACT.json` fixes two independent starting-policy views
and broad validity, signal, repeatability, and throughput gates. The final
target is the first passing member in the previously frozen hash order, so its
identity cannot be chosen to maximize a favorable training result.
`STARTING_POLICY_VIEWS.json` records both frozen view identities and confirms
that their validity and uniqueness gates pass.

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
- [AutoDock Vina atom-type table](https://github.com/ccsb-scripps/AutoDock-Vina/blob/develop/src/lib/atom_constants.h)
  and [boron-support issue](https://github.com/ccsb-scripps/AutoDock-Vina/issues/171)
- [HSX](https://www.biorxiv.org/content/10.64898/2026.10.01.755933v1.full)
- [OpenAI cell-free protein synthesis study](https://openai.com/index/gpt-5-lowers-protein-synthesis-cost/)
- [Anthropic drug-development collaborations](https://www.anthropic.com/research/early-progress-drug-development)

These sources establish relevance and evaluation requirements. They do not
establish that the planned predictor works.

## Current qualification state

The committed source audit verifies the exact RxnFlow release, source license,
5,000 unique example building blocks, 30 reaction templates, and 28 synthon
types. It also verifies the pinned MolGenBench evaluator code, MIT license, and
120-target identity list, together with two public test fixtures. Zenodo records
the 5.38 GB Version4 archive under CC BY 4.0 and publishes its MD5 digest. The
downloaded archive matches that digest and has SHA-256
`e52ab106f35c1376fe181a7172caaf11da86c2ba21f89af9236ddadc17cdfb43`.
Its 305,410 member paths are safe and unencrypted, and its 120 complete target
fixtures match the pinned identity registry. Published results and known-active
collections remain unopened.

The outcome-blind hash rule freezes an eight-target qualification panel:
P08254, O14757, Q07820, P00533, P21554, Q07343, P53350, and P16184. All 32
reference-ligand docking calls succeeded under two seeds and two repeats. The
same-seed repeats were exact, and the largest cross-seed affinity range was
0.812 kcal/mol. P53350 took substantially longer than the other controls, so
oracle wall time remains an explicit cost coordinate. The batched adapter also
passes the pinned RxnFlow v2.1 reward interface with finite nonnegative
`float32` output, exact duplicate reuse, and explicit zeroes for malformed or
missing molecules. Both starting-policy views are fully valid, and all 16
target-view score batches completed without infrastructure failures. Every
target passed the frozen signal, repeatability, and throughput gates. Q07820 is
the first passing member in the prespecified hash order and is therefore the
selected target. These audits do not open training outcomes, published model
results, or known-active collections.

## Reproduction

[`SOURCES.json`](SOURCES.json) records the pinned public inputs.
[`SOURCE_AUDIT.json`](SOURCE_AUDIT.json) contains only source-code hashes and
construction-fixture counts. [`PROTOCOL.json`](PROTOCOL.json) fixes the study
structure while listing every open gate. [`BATCH_REWARD_QUALIFICATION.json`](BATCH_REWARD_QUALIFICATION.json)
records the CPU-only batch and RxnFlow interface checks.
[`SYNTHESIS_ENVIRONMENT_QUALIFICATION.json`](SYNTHESIS_ENVIRONMENT_QUALIFICATION.json)
and [`WARM_START_CONTRACT.json`](WARM_START_CONTRACT.json) fix the common action
space and QED training recipe before the warm start is trained.
[`WARM_START_INTERFACE_QUALIFICATION.json`](WARM_START_INTERFACE_QUALIFICATION.json)
records a one-update CPU smoke of the complete environment, policy, optimizer,
trajectory-generation, and checkpoint path. The claim-bearing 1,000-update warm
start is recorded in [`WARM_START_QUALIFICATION.json`](WARM_START_QUALIFICATION.json).
Its weights-only starting-policy artifact has SHA-256
`effb789bf754231c6897e4b11f28ba644d51a103298ae3fc65a0687ad962976a`.
[`TARGET_SELECTION_CONTRACT.json`](TARGET_SELECTION_CONTRACT.json) and
[`STARTING_POLICY_VIEWS.json`](STARTING_POLICY_VIEWS.json) freeze the target
gate and both sampled views. [`TARGET_SELECTION_RESULT.json`](TARGET_SELECTION_RESULT.json)
records the complete aggregate gate audit, input digests, and selected target.
[`MEASUREMENT_CONTRACT.json`](MEASUREMENT_CONTRACT.json) fixes the larger
two-view probe and six development-bank rules before those samples are drawn.
[`MEASUREMENT_EXTRACTOR_QUALIFICATION.json`](MEASUREMENT_EXTRACTOR_QUALIFICATION.json)
records the deterministic operational and graph-feature smoke.
[`TARGET_REWARD_CONTRACT_V2.json`](TARGET_REWARD_CONTRACT_V2.json) and
[`MEASUREMENT_CONTRACT_V2.json`](MEASUREMENT_CONTRACT_V2.json) record the
pre-measurement scoring revision without redrawing either frozen view.
[`MEASUREMENT_RELIABILITY_RESULT_V2.json`](MEASUREMENT_RELIABILITY_RESULT_V2.json)
preserves the failed diversity gate and the passing reliability checks.
[`MEASUREMENT_CONTRACT_V3.json`](MEASUREMENT_CONTRACT_V3.json) freezes the
decision-aligned diversity gate and two new view seeds before they are sampled.
[`MEASUREMENT_RELIABILITY_RESULT_V3.json`](MEASUREMENT_RELIABILITY_RESULT_V3.json)
records the passing independent-view gate.
[`BANK_CONSTRUCTION_CONTRACT.json`](BANK_CONSTRUCTION_CONTRACT.json) fixes the
development-bank summaries and confirmation statistic before measurement
reliability is scored.
[`DEVELOPMENT_BANK_QUALIFICATION_V1.json`](DEVELOPMENT_BANK_QUALIFICATION_V1.json)
records the construction memberships and first confirmation reconstruction.
[`DEVELOPMENT_BANK_QUALIFICATION_AUDIT_V1.json`](DEVELOPMENT_BANK_QUALIFICATION_AUDIT_V1.json)
marks that result non-authorizing because its view seeds do not match the
version 1 bank contract. [`BANK_CONSTRUCTION_CONTRACT_V2.json`](BANK_CONSTRUCTION_CONTRACT_V2.json)
retains every selector and threshold while binding the qualified construction
view and a new untouched confirmation seed.
[`BANK_CONFIRMATION_SCORING_AUDIT_V2.json`](BANK_CONFIRMATION_SCORING_AUDIT_V2.json)
preserves the unsupported-boron failure and the unchanged view identity.
[`TARGET_REWARD_CONTRACT_V3.json`](TARGET_REWARD_CONTRACT_V3.json),
[`MEASUREMENT_CONTRACT_V4.json`](MEASUREMENT_CONTRACT_V4.json), and
[`BANK_CONSTRUCTION_CONTRACT_V3.json`](BANK_CONSTRUCTION_CONTRACT_V3.json)
freeze the narrow eligibility revision while retaining the sampled records,
memberships, selectors, coordinates, and confirmation threshold.
[`DEVELOPMENT_BANK_QUALIFICATION_V3.json`](DEVELOPMENT_BANK_QUALIFICATION_V3.json)
records the failed independent-view gate and the six non-authorizing
construction memberships.
[`BANK_CONFIRMATION_DIAGNOSTIC_V1.json`](BANK_CONFIRMATION_DIAGNOSTIC_V1.json)
records the sealed pre-training diagnosis. The action-count failure is driven
by incidental ordering among near-tied banks, realized oracle time remains a
runtime-specific cost, and exact scaffold uniqueness is nearly saturated.
[`BANK_CONSTRUCTION_CONTRACT_V4.json`](BANK_CONSTRUCTION_CONTRACT_V4.json)
freezes eight strict selector-versus-neutral contrasts and untouched seed
20261125 before that view is sampled. The scaffold diagnostic follows RDKit's
[generic Murcko scaffold](https://www.rdkit.org/docs/source/rdkit.Chem.Scaffolds.MurckoScaffold.html)
definition. Oracle time remains descriptive because Vina search work depends
on ligand size and flexibility under a fixed exhaustiveness setting, as
documented in the [Vina FAQ](https://autodock-vina.readthedocs.io/en/latest/faq.html).
[`DEVELOPMENT_BANK_QUALIFICATION_V4.json`](DEVELOPMENT_BANK_QUALIFICATION_V4.json)
records the untouched selector-fidelity result. All eight checks pass in both
independent views, while the earlier complete-order failure remains preserved
as a separate scientific result.

Audit local checkouts without reading target outcomes:

```bash
python scripts/audit_source.py \
  --rxnflow-repo /path/to/RxnFlow \
  --molgenbench-repo /path/to/MolGenBench \
  --out /tmp/reaction_source_audit.json
```

After downloading the Version4 archive, qualify its bytes and target-fixture
inventory without extracting or opening result contents:

```bash
python scripts/audit_molgenbench_archive.py \
  --archive /path/to/MolGenBench_Version4.zip \
  --out /tmp/MOLGENBENCH_ARCHIVE_AUDIT.json
```

Audit only the frozen target fixtures:

```bash
python scripts/audit_target_fixtures.py \
  --archive /path/to/MolGenBench_Version4.zip \
  --out /tmp/TARGET_FIXTURE_AUDIT.json
```

Create the pinned CPU docking environment and qualify the frozen panel after
extracting only its 24 audited fixture files:

```bash
conda env create -f oracle-environment.yml
conda run -n anarres-molecular-oracle \
  python scripts/qualify_docking_oracle.py \
  --fixtures /path/to/frozen-panel-fixtures \
  --targets P08254 O14757 Q07820 P00533 P21554 Q07343 P53350 P16184 \
  --output /tmp/ORACLE_QUALIFICATION.json
```

[`ORACLE_CONTRACT.json`](ORACLE_CONTRACT.json) fixes the released docking
implementation, runtime, seeds, repeatability thresholds, and reference-control
gate before panel qualification is scored. [`ORACLE_QUALIFICATION.json`](ORACLE_QUALIFICATION.json)
records the aggregate result and the digest of the raw machine report.
[`TARGET_REWARD_CONTRACT.json`](TARGET_REWARD_CONTRACT.json) fixes the
larger-is-better docking and QED reward, eligibility filters, timeout, and
failure semantics while final target identity remains open.
[`REWARD_ADAPTER_QUALIFICATION.json`](REWARD_ADAPTER_QUALIFICATION.json)
records valid, malformed, filtered, timeout, and repeat-call behavior without
selecting a target.

Validate the protocol:

```bash
python scripts/validate_protocol.py
```

[`RUNBOOK.md`](RUNBOOK.md) gives the authorized order from source
qualification through the prospective freeze. It stops before claim-bearing
training.
