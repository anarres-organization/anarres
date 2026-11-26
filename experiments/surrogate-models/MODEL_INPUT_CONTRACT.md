# Surrogate model input contract

This contract separates information available when a candidate is proposed
from the outcome used to fit or score a surrogate. It creates two deterministic
views of the released intervention corpus:

- `MODEL_INPUTS.jsonl` contains prediction-time features.
- `MODEL_LABELS.jsonl` contains protected outcomes and scoring identities.

The files join through an opaque `join_key` derived from the record identity.
That key is transport metadata and must be removed before model fitting. The
resolvable `record_id` appears only in the protected label view. Line order has
no scientific meaning.

## Prediction-time features

The feature payload contains:

- domain and evidence level
- cost fields known before training
- the native `prediction_time` object released by the contributing study.

Native measurements remain nested and namespaced. The builder does not rename
unlike quantities into shared coordinates, fill missing values with zero, or
derive features from outcomes.

The builder recursively removes hashes, digests, paths, filenames, record
pointers, and frozen candidate predictions. Record, source, study, panel,
candidate, run, seed, and lineage identities never enter `features`. A native
fixed rule remains a separate baseline rather than an input shortcut for a
learned model.

## Protected labels

The label view retains the fields needed to reconstruct the scientific unit and
score a decision: source, study, panel, candidate, seed, lineage, native outcome,
and cost status. A training loader may open labels only for records in its
training fold. Evaluation code may open held-out labels only after predictions
for that fold have been written.

Outcomes remain in native units. Materials records retain their released
panel-normalized utility and regret; the builder does not create a universal
cross-domain target.

## Model views

The same input artifact supports three fixed views:

1. `metadata` uses domain, evidence level, and known cost fields.
2. `structured` adds the native prediction-time object.
3. `record_conditioned` serializes the structured view as canonical JSON.

The record-conditioned serialization is a transport format, not a claim that a
language model understands every native measurement. Later text, code, trace,
image, structure, or video assets require a licensed artifact manifest and
reconstruction checks before they may be added.

## Rebuild and verify

```bash
python experiments/surrogate-models/build_model_views.py
python experiments/surrogate-models/build_model_views.py --check
python -m unittest experiments/surrogate-models/test_build_model_views.py
```
