# Prospective phonon-selection result

The first prospective materials decision is complete. The frozen prediction
selected signal + coverage at 256, 512, and 1,024 structures, with the complete
order signal + coverage, signal, coverage, then hash-uniform. The prediction did
not transfer to the formula-disjoint DFT-PBE panel. Coverage leads at 256 and
512 structures, while hash-uniform leads at 1,024.

## Primary DFT-PBE result

Values are two-seed mean Top-100 stable rates. Utility is the change from the
released starting checkpoint, whose Top-100 stable rate is 85.0%.

| Candidate | 256 | 512 | 1,024 |
| --- | ---: | ---: | ---: |
| Hash-uniform | 77.0% (-8.0 pp) | 79.5% (-5.5 pp) | **87.0% (+2.0 pp)** |
| Signal | 84.0% (-1.0 pp) | 76.0% (-9.0 pp) | 65.5% (-19.5 pp) |
| Coverage | **84.5% (-0.5 pp)** | **87.0% (+2.0 pp)** | 84.0% (-1.0 pp) |
| Signal + coverage | 80.0% (-5.0 pp) | 66.0% (-19.0 pp) | 66.0% (-19.0 pp) |

The frozen point prediction is correct at 0/3 budgets. Mean allocation regret
is 15.5 percentage points, and the complete predicted order attains 27.8%
pairwise accuracy. The seed-level winner agrees at 2/3 budgets. The released
full-data DFT checkpoint reaches 92.0%, seven points above the starting model.

The conclusion is not metric-specific. At 512 and 1,024 structures, the signal
and signal + coverage arms also have worse ROC AUC, Brier score,
minimum-frequency MAE, and continuous pairwise concordance than coverage or
hash-uniform. [`RESULTS_SUMMARY.json`](RESULTS_SUMMARY.json) records all
prespecified metrics and seed means.

## Secondary MP20 result

The starting checkpoint has a 78.75% macro Top-100 stable rate across eight
generator sources. No candidate mean exceeds it.

| Candidate | 256 | 512 | 1,024 |
| --- | ---: | ---: | ---: |
| Hash-uniform | 72.81% | 70.63% | **74.00%** |
| Signal | **75.75%** | **72.06%** | 70.06% |
| Coverage | 72.50% | 70.81% | 71.75% |
| Signal + coverage | 75.56% | 70.44% | 58.25% |

The full-data DFT checkpoint reaches 67.63% on this panel. DFT post-training can
therefore improve the matched DFT-PBE panel while reducing transfer to the MP20
generator suite. The result summary reports each generator source before macro
averaging.

## Post-outcome composition audit

The frozen rules matched structure count and kept mean atom count within 1.81%
of hash-uniform, but they did not match the training-label distribution. The
source reservoir is 85.3% stable at the -0.1 THz threshold. Signal selection
concentrates much more heavily on unstable, high-loss structures.

| Candidate | 256 stable | 512 stable | 1,024 stable |
| --- | ---: | ---: | ---: |
| Hash-uniform | 84.8% | 85.7% | 85.1% |
| Signal | 38.3% | 53.5% | 66.3% |
| Coverage | 81.6% | 81.4% | 81.6% |
| Signal + coverage | 47.7% | 58.0% | 67.1% |

This audit provides a concrete candidate explanation for the prospective miss:
informativeness and representation coverage did not preserve the target
distribution, and adding more selected structures strengthened that shift. The
audit is descriptive because it was performed after external scoring. It does
not convert the failed prediction into a successful test or isolate label shift
as the sole cause.

## Integrity and next test

All 24 candidate checkpoints and both released references produced complete,
finite predictions for 1,000 DFT-PBE and 6,400 MP20 structures before either
external manifest was opened. The prediction manifest has SHA-256
`90eee150f6d49521afe72aa9dad171f2ca196bbce2161c2e17e10ae82f87f558`.
Independent rescoring reproduces result digest
`46cca8be36d155a08100222ef3e00a73fb2e8870a44a30fa26ef616f43e300a2`.

The next confirmatory study should cross model-relative signal with an explicit
distribution-matching constraint and score it on a new untouched panel. The
current external panels now support retrospective analysis only. This keeps the
main lesson falsifiable: high measured update signal is not sufficient for
useful materials post-training when the selected set changes which physical
regimes the model sees.
