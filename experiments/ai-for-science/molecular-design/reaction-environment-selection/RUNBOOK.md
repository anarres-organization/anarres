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
  --output-dir /tmp/replay-training-smoke \
  --report /tmp/REPLAY_TRAINING_SMOKE_V1.json
```

The smoke uses two online and two replay trajectories for one update. It must
start with an empty optimizer and replay buffer, load the complete fixed bank,
produce finite loss and gradient diagnostics, write a checkpoint, and preserve
the replay-bank size. This is an interface qualification and cannot be scored
as an environment outcome.

## 8. Instantiate and qualify the endpoint

Create the endpoint environment from `endpoint-environment.yml`. This matches
the MolGenBench Version4 package pins and PoseCheck commit. Compute reference
pose metrics once per target, then derive the target-relative thresholds:

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
