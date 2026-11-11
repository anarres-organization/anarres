# Molecular environment source format

`rxnflow-molecular-environment-v1` describes the native inputs required before
an endpoint measurement. Its root contains `molecular-source.json`.
`anarres.toml` is added later by `anarres init` and is not part of the native
revision.

## Required objects

The declaration binds the following objects by relative path and SHA-256:

- a tab-separated canonical-SMILES and stable-ID building-block catalog.
- reaction templates with stable template IDs and explicit compatible
  building-block IDs.
- a prepared reaction-environment directory and its preparation report.
- a candidate RxnFlow replay bank with stable trajectory and molecule IDs.
- a weights-only starting policy with a content-addressed revision.
- a prepared target directory and target manifest.
- oracle, chemical-filter, docking, and deterministic probe contracts.
- training trajectory IDs and reserved evaluation-attempt IDs.
- source revisions, licenses, and the paths covered by each license.

The replay bank is an input to measurement and training. A scored bank bundle,
environment profile, endpoint result, or downstream utility record is not a
valid source object.

## Static qualification

`anarres qualify` checks hashes, stable identities, duplicate policy, reaction
compatibility, replay membership, target fixtures, runtime contracts, failure
semantics, source licenses, and partition separation. It does not import the
model runtime, sample a policy, run chemical filters or docking, or inspect a
training outcome. Native chemistry and docking remain in their qualified Python
environments.

The oracle contract must preserve three distinct states: molecule-specific
scientific zero, infrastructure failure, and missing score. The probe contract
fixes its attempt count, seed, and batch size. A Q07820 execution also binds the
released matched-evaluation and endpoint-contract hashes.

## Probe output

`anarres probe` writes `PROBE_PLAN.json` before execution. The plan binds the
source revision, policy revision, target, attempts, evaluation seed, runtimes,
and the five released producer stages. Passing `--execute` runs those stages in
order. Each completed stage records command and output digests, allowing a
later invocation to verify and resume the same plan. A changed source, policy,
contract, command, or output is rejected.

The final endpoint record measures one policy under one environment contract.
It does not establish cross-environment utility, authorize training outside the
frozen study gate, or convert endpoint outcomes into profile coordinates.
