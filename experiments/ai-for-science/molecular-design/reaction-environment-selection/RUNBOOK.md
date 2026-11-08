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

Select one target by the outcome-blind hash rule in `PROTOCOL.json` after every
eligible target passes file-integrity and oracle-input checks. Serialize the
eligible target IDs, selection hash, selected identity, and all exclusion
reasons.

## 3. Qualify the target reward

Implement one adapter that maps an RxnFlow terminal molecule to the frozen
target oracle. Test valid ligands, malformed molecules, oracle timeouts, and
repeat calls. Infrastructure failures remain separate from scientific reward.
Freeze docking preparation, random seeds, box definition, pose count, timeout,
and every qualifying-hit threshold.

The reward must provide adequate headroom under the common starting policy. A
floor or saturation result stops the study before candidate construction.

## 4. Train and qualify the common warm start

Train one RxnFlow v2.1.0 QED warm start on the qualified example construction
space. Record the complete configuration, weights-artifact hash, catalog and
reaction fixture hashes, software environment, and smoke results. Export the
policy and sampling-model weights without QED optimizer or replay state. Every
target-training arm loads those identical weights into a fresh trainer before
its frozen replay bank is preloaded.

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
