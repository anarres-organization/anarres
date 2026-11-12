# Reaction-environment selection runbook

This runbook implements the qualification stages in `PROTOCOL.json`. It stops
before claim-bearing training. Commands may use local paths, but committed
artifacts must contain source identities and hashes rather than machine paths.

## 1. Reproduce the source audit

Check out the two public repositories at the commits in `SOURCES.json`, then
run:

```bash
python scripts/audit_source.py \
  --rxnflow-repo /path/to/RxnFlow \
  --molgenbench-repo /path/to/MolGenBench \
  --out /tmp/reaction_source_audit.json
diff -u SOURCE_AUDIT.json /tmp/reaction_source_audit.json
python scripts/validate_protocol.py
```

Stop on a commit, hash, inventory, or license mismatch.

## 2. Qualify the MolGenBench archive

Download `MolGenBench_Version4.zip` from the pinned Zenodo record. Record its
byte size, SHA-256 digest, published MD5 digest, and applicable terms. Extract
only the code-independent fixture metadata needed to enumerate candidate
targets. Do not inspect reference-active performance or published model-result
directories.

Audit the archive without extracting or opening result contents:

```bash
python scripts/audit_molgenbench_archive.py \
  --archive /path/to/MolGenBench_Version4.zip \
  --out /tmp/MOLGENBENCH_ARCHIVE_AUDIT.json
```

Freeze an eight-target qualification panel from the complete archive inventory:

```bash
python scripts/freeze_target_panel.py \
  --archive-audit /path/to/MOLGENBENCH_ARCHIVE_AUDIT.json \
  --panel-size 8 \
  --out /path/to/TARGET_PANEL_FREEZE.json
```

Run the same small starting-policy probe on every target in that panel. Select
one target by the outcome-blind hash rule in `PROTOCOL.json` after each eligible
target passes file integrity, oracle repeatability, reference-control behavior,
starting-policy validity, and pre-RL headroom. Serialize the eligible target
IDs, selection hash, selected identity, and all exclusion reasons.

Before installing the docking stack, audit only the selected structural
fixtures inside the archive:

```bash
python scripts/audit_target_fixtures.py \
  --archive /path/to/MolGenBench_Version4.zip \
  --out /tmp/TARGET_FIXTURE_AUDIT.json
```

Create the runtime from `oracle-environment.yml`, extract only the audited
fixture triplets, and run the frozen qualification contract:

```bash
conda env create -f oracle-environment.yml
conda run -n anarres-molecular-oracle \
  python scripts/qualify_docking_oracle.py \
  --fixtures /path/to/frozen-panel-fixtures \
  --targets P08254 O14757 Q07820 P00533 P21554 Q07343 P53350 P16184 \
  --output /tmp/ORACLE_QUALIFICATION.json
```

Stop if a reference call fails, a fixed-seed repeat changes, cross-seed
affinity exceeds the frozen range, or the reference control misses its gate.
The committed aggregate report passes all four checks for the eight-target
panel. This qualifies reference docking behavior without selecting a final
target or authorizing training.

Create an outcome-free qualification file using only the fields accepted by
`freeze_target.py`, then freeze the identity:

```bash
python scripts/freeze_target.py \
  --qualification /path/to/TARGET_QUALIFICATION.json \
  --out /path/to/TARGET_FREEZE.json
```

## 3. Qualify the target reward

Implement one adapter that maps an RxnFlow terminal molecule to the frozen
target oracle. Test valid ligands, malformed molecules, oracle timeouts, and
repeat calls. Infrastructure failures remain separate from scientific reward.
Freeze docking preparation, random seeds, box definition, pose count, timeout,
and every qualifying-hit threshold.

`TARGET_REWARD_CONTRACT.json` fixes the terminal reward as the product of QED
and larger-is-better docking reward, together with the Veber-style eligibility
gate used by the official RxnFlow docking task. Final target identity and
prepared target artifacts were held open until the starting-policy gate passed.
`REWARD_ADAPTER_QUALIFICATION.json` verifies that malformed and filtered
molecules remain scientific zeroes, timeouts remain infrastructure failures,
and repeated valid calls are deterministic. `BATCH_REWARD_QUALIFICATION.json`
verifies deduplicated batch scoring and the pinned RxnFlow v2.1 reward
interface. `TARGET_SELECTION_RESULT.json` records the completed throughput and
headroom gates and freezes Q07820 before candidate construction.

The first 4,096-attempt scoring pass stopped on a molecule-specific conformer
failure before producing candidate measurements. `TARGET_REWARD_CONTRACT_V2.json`
adds one deterministic random-coordinate fallback. Exhausting both conformer
attempts is a scientific zero for that molecule; receptor, ligand-toolchain,
Vina, process, and timeout failures still abort the batch. Reuse the unchanged
views under `MEASUREMENT_CONTRACT_V2.json`; do not redraw either seed.

The reward must provide adequate headroom under the common starting policy. A
floor or saturation result stops the study before candidate construction.

After the warm start passes integrity checks, follow
`TARGET_SELECTION_CONTRACT.json`. Generate both starting-policy views once,
score the same frozen samples against all eight qualified targets, apply every
gate, and select the first passing target in the prespecified hash order.

After all 16 target-view score files are complete, apply the frozen gate with:

```bash
python scripts/select_target.py \
  --results-dir /path/to/complete/target-view-scores \
  --contract TARGET_SELECTION_CONTRACT.json \
  --starting-views STARTING_POLICY_VIEWS.json \
  --oracle-qualification ORACLE_QUALIFICATION.json \
  --output /tmp/TARGET_SELECTION_RESULT.json
```

Stop if the result abstains. Commit the aggregate decision and its gate values,
not machine paths or raw per-molecule oracle records.

## 4. Train and qualify the common warm start

Build the public example construction space as specified by
`SYNTHESIS_ENVIRONMENT_QUALIFICATION.json`, and verify its RxnFlow content
signature. Train one RxnFlow v2.1.0 QED warm start using
`warm-start-qed.yaml` and the execution settings frozen in
`WARM_START_CONTRACT.json`. Record the complete configuration, weights-artifact hash, catalog and
reaction fixture hashes, software environment, and smoke results. Export the
policy and sampling-model weights with `scripts/warm_start_weights.py`, which
excludes QED optimizer, scheduler, replay, and random-number state. Every
target-training arm loads those identical weights into a fresh trainer before
its frozen replay bank is preloaded. Set `num_replay_insert: 0` so fresh online
trajectories never replace the selected bank. Keep online and replay batch sizes
identical across arms.

`WARM_START_INTERFACE_QUALIFICATION.json` records the reduced one-update CPU
smoke. `WARM_START_QUALIFICATION.json` records the completed 1,000-update run,
its integrity counts, and the weights-only starting-policy identity.

## 5. Measure the starting policy

The original two 4,096-attempt views are preserved in
`MEASUREMENT_RELIABILITY_RESULT_V2.json`. They passed every signal,
throughput, graph, and cross-view stability check but failed the prespecified
0.90 unique-product fraction in both views. Do not use them to qualify a bank.

Follow `MEASUREMENT_CONTRACT_V3.json`. Generate two new independent
4,096-attempt
trajectory sweeps under the frozen Q07820 target reward. The construction view
is the only source of development-bank members; the confirmation view measures
reliability and independently reconstructs bank summaries.
Each record must contain trajectory identity, product identity, reward,
validity and oracle status, generated-action cost, scaffold and ring system,
reaction sequence, route depth, graph summary, and frozen representation.

Join samples, selected-target scores, and the frozen encoder representation
with `scripts/extract_starting_measurements.py`. Verify the checkpoint and both
input digests before accepting its manifest. The committed extractor
qualification is byte-identical across two runs on the 64-record smoke view.

After both complete view artifacts pass their digest checks, apply the frozen
reliability gates with:

```bash
python scripts/qualify_measurements.py \
  --contract MEASUREMENT_CONTRACT_V3.json \
  --records /path/to/construction-records.jsonl \
  --manifest /path/to/construction-manifest.json \
  --records /path/to/confirmation-records.jsonl \
  --manifest /path/to/confirmation-manifest.json \
  --output /tmp/MEASUREMENT_QUALIFICATION.json
```

Compute all operational and graph coordinates separately in each probe view.
The version 3 diversity gate requires at least 2,048 unique canonical products
and a unique fraction of at least 0.80 in each new view. All other gates remain
unchanged. Failure produces an abstention or a new versioned protocol.

## 6. Freeze development banks

Construct the six equal-size development banks from the eligible probe
trajectories. Record memberships, rule parameters, hashes, bank overlap,
scaffold overlap, reaction coverage, cost balance, and coordinate summaries.
Use `scripts/qualify_development_banks.py` to reconstruct all six selectors on
the independent confirmation view and apply the frozen bank-order correlation
gate before accepting the construction-view memberships.
Freeze the training and evaluation contracts before launching any development
arm.

`DEVELOPMENT_BANK_QUALIFICATION_V1.json` preserves the first reconstruction,
but its audit marks the result non-authorizing because the version 1 bank
contract named the failed v2 view seeds. Follow
`BANK_CONSTRUCTION_CONTRACT_V2.json` binds the seed-20261122 construction
memberships to untouched seed 20261124. Its first scoring attempt exposed three
boronic-acid products outside the pinned Vina atom-type domain and produced no
bank-confirmation result. Preserve that failure and follow
`TARGET_REWARD_CONTRACT_V3.json`, `MEASUREMENT_CONTRACT_V4.json`, and
`BANK_CONSTRUCTION_CONTRACT_V3.json`. Rescore the exact seed-20261124 view,
retain the seed-20261122 memberships, and require the same rank gate before
development training. Do not redraw either view or change a selector,
coordinate, bank size, statistic, or threshold.

`DEVELOPMENT_BANK_QUALIFICATION_V3.json` records the completed result. Target
reward, graph-embedding coverage, reaction-family coverage, ring-system
coverage, and route coverage pass. Generated-action cost, oracle time, and
scaffold coverage fail the frozen 0.8 rank-correlation gate. Stop here. The six
construction memberships are useful measurement records but cannot authorize
the training schedule smoke or a development arm under this protocol.

`BANK_CONFIRMATION_DIAGNOSTIC_V1.json` diagnoses that failure without reading
training outcomes. All eight intended selector-versus-neutral contrasts pass
in both views. Alternative oracle-time and scaffold summaries do not recover
the complete six-bank ordering. Follow `BANK_CONSTRUCTION_CONTRACT_V4.json`,
which retains the seed-20261122 construction memberships and every estimator,
selector, and runtime setting. Generate untouched seed 20261125 once, rebuild
the six banks on that view, and require all eight strict selector-fidelity
checks in both views. Preserve the descriptive full-order correlations. A
failed selector-fidelity check returns the study to abstention.

`DEVELOPMENT_BANK_QUALIFICATION_V4.json` records the completed untouched
confirmation. All eight selector-versus-neutral checks pass in both views, so
the candidate-bank gate authorizes freezing the matched training and
evaluation contracts. Preserve the Version 3 failure and the Version 4 pass as
separate results. Neither result contains target-training outcomes.

## 7. Materialize and smoke-test replay training

The public sampler export omits internal states and backward route
probabilities. Reconstruct them from the pinned synthesis environment rather
than substituting approximate values. The materializer resolves each oriented
synthon action against the action space available at that state, replays the
route, and recomputes the backward probability over the same route set used by
RxnFlow.

```bash
python scripts/materialize_replay_bank.py \
  --env-dir /path/to/qualified-environment \
  --samples /path/to/view_v3_20261122.jsonl \
  --records /path/to/records_v3_20261122.jsonl \
  --qualification DEVELOPMENT_BANK_QUALIFICATION_V4.json \
  --bank hash_uniform \
  --output /tmp/hash_uniform.replay.json
```

Before target training, compare reconstructed replay objects with fresh full
trajectories produced by the pinned RxnFlow policy. Require exact states,
actions, and products, and backward log probabilities within an absolute
tolerance of `1e-12`. Then run the reduced interface smoke:

```bash
python scripts/smoke_replay_training.py \
  --config /path/to/warm-start-config.yaml \
  --env-dir /path/to/qualified-environment \
  --warm-start /path/to/warm_start_weights.pt \
  --replay-bank /tmp/hash_uniform.replay.json \
  --prepared-target /path/to/prepared_Q07820 \
  --oracle-python /path/to/qualified-oracle/bin/python \
  --output-dir /tmp/replay-training-smoke \
  --report /tmp/REPLAY_TRAINING_SMOKE_V1.json
```

The smoke uses two online and two replay trajectories for one update. It must
start with an empty optimizer and replay buffer, load the complete fixed bank,
produce finite loss and gradient diagnostics, write a checkpoint, and preserve
the replay-bank size. This is an interface qualification and cannot be scored
as an environment outcome.

Before claim-bearing execution, repeat the smoke with `--num-online 64
--num-replay 64 --device cuda` on the intended accelerator and runtime. This
exercises the frozen batch shape without changing the one-update interface-only
scope. Set the retrosynthesis and reward worker counts explicitly to the values
planned for the matched runs. Pass the qualified docking environment through
`--oracle-python`; this makes docking-runtime selection explicit and records
the oracle executable digest and package versions.

After the endpoint gate passes and the matched contract is frozen, run each
development arm with the contract-enforcing entry point:

```bash
python scripts/run_matched_training.py \
  --config target-training-q07820.yaml \
  --env-dir /path/to/qualified-environment \
  --warm-start /path/to/warm_start_weights.pt \
  --replay-bank /path/to/hash_uniform.replay.json \
  --prepared-target /path/to/prepared_Q07820 \
  --oracle-python /path/to/qualified-oracle/bin/python \
  --output-dir /path/to/run-output \
  --arm hash_uniform \
  --seed 20261108 \
  --preflight-only
```

The runner accepts only the six frozen development arms and two frozen seeds.
The preflight checks the released contract, configuration, starting-policy
weights, complete replay payload, prepared target, bank identity, and
qualification digest without loading the trainer. Run it for every arm and
seed, then remove `--preflight-only` to train. The runner also verifies the
complete log, online-sample count, immutable replay content, and required
checkpoints before writing `MATCHED_TRAINING_RUN.json`. To continue an
interrupted run, provide a full checkpoint through `--resume-from`; optimizer,
scheduler, replay, and random-number state are restored from that checkpoint.

## 8. Instantiate and qualify the endpoint

Create the endpoint environment from `endpoint-environment.yml`. This matches
the MolGenBench Version4 package pins and PoseCheck commit. Install Medchem's
checksum-pinned Lilly 2.1 tools inside the environment before scoring:

```bash
medchem install-lilly
```

The endpoint producer checks all three executables before scoring and stops if
the optional runtime is absent or incompatible. Compute reference pose metrics
once per target, then derive the target-relative thresholds:

```bash
python scripts/compute_reference_pose_metrics.py \
  --sdf /path/to/Q07820_reference_active_molecules_vina_docked.sdf \
  --protein /path/to/Q07820_prep.pdb \
  --pocket /path/to/Q07820_prep.pdb \
  --output /tmp/Q07820_reference_pose_metrics.csv \
  --jobs 16

python scripts/derive_qualifying_hit_thresholds.py \
  --contract QUALIFYING_HIT_CONTRACT_V1.json \
  --docked-actives /path/to/Q07820_reference_active_molecules_vina_docked.sdf \
  --interactions /path/to/Q07820_reference_active_molecules_vina_docked_interaction_scores.csv \
  --strain /tmp/Q07820_reference_pose_metrics.csv \
  --clashes /tmp/Q07820_reference_pose_metrics.csv \
  --output /tmp/Q07820_REFERENCE_THRESHOLDS_V1.json
```

The committed threshold artifact records the source archive, evaluator and
PoseCheck revisions, input hashes, finite support, and missingness. Recomputed
output must match it before candidate evaluation. Score a fixed starting-policy
sample with `scripts/score_qualifying_hits.py`. Stop if the panel has any
infrastructure failure, zero unique qualifying molecules, or support that
depends on a single molecule. Molecule-specific failures remain in the fixed
attempt denominator.

Follow `STARTING_POLICY_ENDPOINT_QUALIFICATION_CONTRACT_V1.json` for the
starting-policy panel. Draw seed 20261126 exactly once for 4,096 attempts with
the frozen weights, synthesis environment, beta, temperature, and checkpoint
preference. Invalid attempts are not retried. Run the full endpoint on every
returned molecule and retain any missing attempts as scientific zeroes in the
fixed denominator. Require zero infrastructure failures, at least 16
qualifying attempts, at least eight unique qualifying molecules, and no single
canonical molecule contributing more than one quarter of qualifying attempts.
Only a passing result authorizes fixing 4,096 evaluation attempts per policy,
seed, and checkpoint in the matched contract.

Preserve the docked poses with the deterministic endpoint producer before
running the MolGenBench pose metrics:

```bash
python scripts/dock_endpoint_panel.py panel \
  --samples /path/to/starting_policy_seed20261126.jsonl \
  --prepared-target /path/to/prepared_Q07820 \
  --attempts 4096 \
  --sample-seed 20261126 \
  --contract q07820-starting-policy-endpoint-qualification-v2 \
  --output-dir /path/to/endpoint-docking \
  --output-records /path/to/endpoint-docking/attempts.jsonl \
  --report /path/to/endpoint-docking/report.json
```

The producer docks each unique canonical molecule once under the frozen seed,
maps duplicate molecules back to their original attempts, and records missing
or molecule-specific failures without retrying them. Any timeout, receptor,
toolchain, process, or unclassified conversion failure invalidates the panel.

The preserved v1 endpoint execution exposed one narrower case: 11 molecules
completed Vina docking but produced invalid-valence poses that RDKit could not
represent as valid 3D molecules. The frozen v2 contract classifies only that
exact condition as a scientific zero. It reruns the complete unchanged sample;
all broader Open Babel, receptor, Vina, process, timeout, and toolchain failures
remain infrastructure failures.

Compute the full native endpoint record from those preserved poses:

```bash
python scripts/score_endpoint_metrics.py \
  --docking-records /path/to/endpoint-docking/attempts.jsonl \
  --protein /path/to/Q07820_prep.pdb \
  --pocket /path/to/Q07820_pocket10.pdb \
  --reference-actives /path/to/Q07820_reference_active_molecules_vina_docked.sdf \
  --reference-interaction-scores /path/to/Q07820_reference_active_molecules_vina_docked_interaction_scores.csv \
  --attempts 4096 \
  --contract q07820-starting-policy-endpoint-qualification-v2 \
  --output-records /path/to/endpoint-metrics.jsonl \
  --report /path/to/endpoint-metrics-report.json
```

This compatibility producer calls the pinned MolGenBench metric definitions
directly. It preserves the original-molecule contract for validity, QED, SA,
and chemistry filters, and the docked-pose contract for PoseBusters, strain,
clashes, and interactions. It reconstructs the native interaction-weight map
from the pinned reference fingerprints and verifies every released reference
score before candidate scoring. The frozen thresholds remain unchanged.

Finally, score the endpoint records with `scripts/score_qualifying_hits.py` and
apply `scripts/apply_starting_policy_endpoint_gate.py` to the resulting score,
the frozen sample and contract, and both producer reports. The gate command
validates the hash-linked evidence chain before emitting a compact result. That
result is the only artifact that authorizes matched training. A failed gate
remains a scientific result and stops the study before training.

## 9. Freeze the prospective decision

After all development arms are complete and scored, fit the operational and
graph-aware predictors. Construct the two prospective banks without opening
their training outcomes. Serialize:

- predictor forms and coefficients
- both bank memberships and hashes
- utility forecasts at all three budgets
- predicted pair ordering
- uncertainty and abstention rules
- training seeds and expected artifact inventory.

Only a completed freeze artifact authorizes prospective training.

The released analysis path keeps each transition executable and hash-bound.
After all development endpoint panels pass the matrix gate, score their utility
curves without reading either prospective arm:

```bash
python scripts/gate_endpoint_evaluation.py \
  --panel-kind development \
  --panels-root /path/to/development-endpoints \
  --output /path/to/DEVELOPMENT_ENDPOINT_GATE.json

python scripts/score_development_results.py \
  --gate /path/to/DEVELOPMENT_ENDPOINT_GATE.json \
  --panels-root /path/to/development-endpoints \
  --output /path/to/DEVELOPMENT_RESULTS.json
```

Construct and independently qualify the two prospective banks, then freeze the
operational and graph-aware ridge models, forecasts, empirical uncertainty,
and abstention decisions:

```bash
python scripts/freeze_prospective_decision.py \
  --development-results /path/to/DEVELOPMENT_RESULTS.json \
  --prospective-banks /path/to/PROSPECTIVE_BANKS.json \
  --output /path/to/PROSPECTIVE_FREEZE.json
```

Prospective training is authorized only by that completed freeze. After every
prospective endpoint passes the same native integrity checks, score it against
the frozen forecast:

```bash
python scripts/gate_endpoint_evaluation.py \
  --panel-kind prospective \
  --panels-root /path/to/prospective-endpoints \
  --output /path/to/PROSPECTIVE_ENDPOINT_GATE.json

python scripts/score_prospective_results.py \
  --development-results /path/to/DEVELOPMENT_RESULTS.json \
  --forecast-freeze /path/to/PROSPECTIVE_FREEZE.json \
  --gate /path/to/PROSPECTIVE_ENDPOINT_GATE.json \
  --panels-root /path/to/prospective-endpoints \
  --output /path/to/PROSPECTIVE_RESULTS.json
```

The scorer verifies the frozen implementation hash, candidate identities,
complete arm-seed-budget matrix, and every qualifying-hit report before it
opens a comparison. It reports curve error, two-bank ordering, allocation
regret, abstention, and seed-level winner agreement.
