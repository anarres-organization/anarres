# Phonon selection execution runbook

This runbook advances the prospective study from source audit through candidate
training and external evaluation. External CIFs are materialized without their
labels, every expected checkpoint is scored, and only then are held-out
manifests opened.

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

Protocol version 1.1 replaces the preliminary eight atom-count bins with 16
training-pool quantile bins. The complete training-visible measurement found a
1--192 atom range, and the preliminary bins missed the 3% cost-matching gate.
The revision was made before any candidate membership was written, and external
outcomes remained sealed.

## 6. Stop boundary

Materialize the 24-run launch matrix and common checkpoint-validation split:

```bash
python scripts/materialize_launch.py \
  --freeze /path/to/FREEZE.json \
  --protocol PROTOCOL.json \
  --manifest /path/to/dft_posttrain/manifest.json \
  --released-split /path/to/splits/dft_posttrain_internal_ids.json \
  --out-dir /path/to/launch
```

The materializer verifies the protocol and freeze digests, exact source
identities, nested candidate sets, split disjointness, and the complete
candidate-by-budget-by-seed matrix. Do not extract external labels or alter
candidate memberships. Candidate training begins only after the materialized
launch manifest and all split hashes pass a separate cache audit.

## 7. Build and audit candidate caches

```bash
python scripts/prepare_candidate_caches.py \
  --upstream-repo /path/to/PhononScore \
  --data-root /path/to/phononscore_data_20261104 \
  --launch-dir /path/to/launch \
  --out-dir /path/to/caches \
  --workers 12
```

The cache builder refuses existing output directories, verifies every split
hash, and requires the built train, validation, and internal-test identities to
equal the frozen split exactly.

## 8. Run the complete frozen matrix

After a one-epoch resource smoke, launch all expected runs:

```bash
python scripts/launch_candidates.py \
  --upstream-repo /path/to/PhononScore \
  --launch-dir /path/to/launch \
  --cache-dir /path/to/caches \
  --out-root /path/to/training \
  --device cpu \
  --workers 24
```

Each run verifies the launch and cache manifests, writes its contract before
training, and refuses to overwrite an existing directory. External panels may
be opened only after all 24 completion records pass and the orchestrator writes
`TRAINING_MANIFEST.json`.

## 9. Materialize label-blind external inputs

Verify that the training-manifest digest equals the value frozen in
`EVALUATION_CONTRACT.json`. Extract only the two panels' CIF members:

```bash
python scripts/prepare_external_inputs.py \
  --archive /path/to/PhononScore_data_splits_20261104.zip \
  --contract EVALUATION_CONTRACT.json \
  --out /path/to/external_inputs
```

The materializer refuses the external `manifest.json` and `id_prop.csv` files.
It hashes each CIF and records that labels remain unread. Build reusable graph
shards from those inputs:

```bash
python scripts/prepare_external_graph_cache.py \
  --upstream-repo /path/to/PhononScore \
  --inputs /path/to/external_inputs \
  --out /path/to/external_graph_cache
```

## 10. Complete every prediction before opening labels

```bash
python scripts/launch_external_predictions.py \
  --upstream-repo /path/to/PhononScore \
  --evaluation-contract EVALUATION_CONTRACT.json \
  --launch-dir /path/to/launch \
  --training-root /path/to/training \
  --data-root /path/to/phononscore_data_20261104 \
  --graph-cache /path/to/external_graph_cache \
  --out-root /path/to/external_predictions \
  --devices 0,1,2,3
```

Each checkpoint obtains normalization moments from its exact frozen training
subset. No moments are fit on either query pool. The launcher requires one
finite prediction per external CIF for all 24 runs and writes a hashed
`PREDICTION_MANIFEST.json` only when the matrix is complete.

## 11. Open labels and score once

```bash
python scripts/score_external_predictions.py \
  --archive /path/to/PhononScore_data_splits_20261104.zip \
  --evaluation-contract EVALUATION_CONTRACT.json \
  --launch-manifest /path/to/launch/LAUNCH_MANIFEST.json \
  --prediction-root /path/to/external_predictions \
  --out /path/to/external_results.json
```

This is the first step permitted to read either external manifest. It reports
the prespecified DFT-PBE metrics, MP20 results by generator source, the complete
candidate decisions, regret, frozen-order agreement, and seed-level winner
agreement. Any incomplete or changed prediction artifact fails before labels
are read.
