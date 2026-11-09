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
prepared target artifacts remain open until the starting-policy gate passes.
`REWARD_ADAPTER_QUALIFICATION.json` verifies that malformed and filtered
molecules remain scientific zeroes, timeouts remain infrastructure failures,
and repeated valid calls are deterministic. `BATCH_REWARD_QUALIFICATION.json`
verifies deduplicated batch scoring and the pinned RxnFlow v2.1 reward
interface. Measure oracle throughput on the selected starting-policy
distribution before training.

The reward must provide adequate headroom under the common starting policy. A
floor or saturation result stops the study before candidate construction.

After the warm start passes integrity checks, follow
`TARGET_SELECTION_CONTRACT.json`. Generate both starting-policy views once,
score the same frozen samples against all eight qualified targets, apply every
gate, and select the first passing target in the prespecified hash order.

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

Generate two independent trajectory sweeps under the frozen target reward.
Each record must contain trajectory identity, product identity, reward,
validity and oracle status, generated-action cost, scaffold and ring system,
reaction sequence, route depth, graph summary, and frozen representation.

Compute all operational and graph coordinates separately in each probe view.
Apply the prespecified reliability and support gates. Failure produces an
abstention or a new versioned protocol.

## 6. Freeze development banks

Construct the six equal-size development banks from the eligible probe
trajectories. Record memberships, rule parameters, hashes, bank overlap,
scaffold overlap, reaction coverage, cost balance, and coordinate summaries.
Freeze the training and evaluation contracts before launching any development
arm.

## 7. Freeze the prospective decision

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
