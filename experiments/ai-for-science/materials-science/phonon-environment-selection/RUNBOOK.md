# Phonon selection execution runbook

This runbook advances the prospective study through source audit, starting-model
measurement, repeatability, and candidate freeze. It stops before candidate
training or external evaluation.

## 1. Pin the public inputs

Clone PhononScore and check out the revision recorded in `SOURCES.json`.
Download `PhononScore_data_splits_20261104.zip` from the recorded URL and verify
its SHA-256 before extraction.

Extract only:

```text
phononscore_data_20261104/dft_posttrain/
phononscore_data_20261104/splits/dft_posttrain_internal_ids.json
phononscore_data_20261104/splits/split_audit.json
phononscore_data_20261104/splits/summary.json
```

Keep `validation_mp20`, `test_mp20`, and `test_dft_pbe` unextracted. The source
audit fails if any of those directories appear under the data root.

## 2. Audit source identity

```bash
python scripts/audit_source.py \
  --data-root /path/to/phononscore_data_20261104 \
  --out /tmp/phonon_source_audit.json

python scripts/validate_protocol.py
```

Compare the reproduced source audit with `SOURCE_AUDIT.json`. The archive,
training manifest, labels, role counts, and CIF inventory must agree before
model loading.

## 3. Reproduce a small checkpoint measurement

Create the upstream PhononScore environment using its pinned environment file.
Generate the deterministic repeatability identities:

```bash
python scripts/measure_starting_model.py \
  --manifest /path/to/phononscore_data_20261104/dft_posttrain/manifest.json \
  --write-repeatability-ids /tmp/phonon_repeatability_ids.json
```

Take the first eight identities into a separate JSON list and run a smoke
measurement:

```bash
python scripts/measure_starting_model.py \
  --upstream-repo /path/to/PhononScore \
  --data-root /path/to/phononscore_data_20261104 \
  --record-ids /tmp/phonon_smoke_ids.json \
  --out /tmp/phonon_smoke_measurements.jsonl \
  --device cuda \
  --batch-size 2
```

The smoke pass must load the frozen checkpoint, preserve all eight record
identities, produce finite signal components and 256-dimensional embeddings,
and report the expected checkpoint and manifest digests.

## 4. Measure the eligible pool and repeatability sample

Run the full 7,809-record sweep:

```bash
python scripts/measure_starting_model.py \
  --upstream-repo /path/to/PhononScore \
  --data-root /path/to/phononscore_data_20261104 \
  --out /path/to/starting_model_measurements.jsonl \
  --device cuda \
  --batch-size 16
```

Run the frozen 128-record sample again in a fresh process:

```bash
python scripts/measure_starting_model.py \
  --upstream-repo /path/to/PhononScore \
  --data-root /path/to/phononscore_data_20261104 \
  --record-ids /tmp/phonon_repeatability_ids.json \
  --out /path/to/repeat_measurements.jsonl \
  --device cuda \
  --batch-size 16
```

Retain the JSONL files, metadata sidecars, environment lock, accelerator model,
driver version, wall time, and invocation. A retry repeats the same identities
and records its reason.

## 5. Freeze candidates

```bash
python scripts/freeze_candidates.py \
  --measurement /path/to/starting_model_measurements.jsonl \
  --repeat-measurement /path/to/repeat_measurements.jsonl \
  --out /path/to/FREEZE.json
```

The freezer verifies repeatability, nested memberships, atom-count matching,
and candidate overlap. A successful artifact contains exact memberships at all
three budgets, the prediction, the abstention rule, source hashes, measurement
hashes, and its own canonical digest.

## 6. Stop boundary

Do not extract external labels, start candidate training, or alter candidate
memberships at this stage. Candidate training begins only after a separate
launch audit verifies the freeze artifact and materializes all expected
arm-budget-seed configurations.
