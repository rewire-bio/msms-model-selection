# Independent methods review: cached-score correction

Verdict: PASS for the bounded cached-score correction, not independent reproduction of original training.

Reviewed run: `aed83c1f079c445c9afcc07654268302`, clean source revision `70b53a7e07f2cd60125d1433d455af28999c735a`. Runtime receipt reports Python 3.11.13, NumPy 1.25.0, pandas 2.2.1, h5py 3.11.0, input/config/protocol/source hashes and passed command exits. Historical inputs and outputs are preserved.

## Method and evidence

The corrected fusion standardizes components independently over the evaluated pool, excludes the target before computing absent-pool moments, and weights official-raw moments by multiplicities. Frozen validation-only grid and complete validation Recall@5 curve match historical values; selected mass weight remains 0.55. Thresholds are fitted from validation scores and applied once to test. Test risk-coverage curves remain descriptive. No checkpoint training or model rescoring occurred.

Independent input checks established all finite float32 component scores, exact component and metadata row alignment, matching target IDs and score/pool lengths, 9,631 validation spectra and 10,648 test spectra. Molecular grouping is disjoint: 1,428 validation and 1,421 test molecules, zero overlap. Frozen input hashes establish identity of available cached files; they do not independently authenticate raw upstream downloads or retrain models.

Runner pre-review concerns were resolved: missing historical numeric columns fail comparisons; weight grid/mode and full historical validation curve are checked; source revision/dirty status/start UTC are recorded; fold and target identity checks run before analysis.

## Independent numerical checks

- Recomputed 372 pool/spectrum score slices independently using direct weighted sums, mean and population SD, across 31 evenly spaced spectra in each fold and all six pool types. Expected saved float32 scores exactly matched corrected artifacts: maximum absolute discrepancy 0.
- Recomputed all 16 validation/test coverage and absent false-nomination rates across four fusion thresholds from exported rank files and threshold values. Every rate matched to absolute tolerance 1e-12.
- Confirmed comparison tables contain 180 metric rows, 90 contrast rows and 20 abstention rows. Exactly 22 metric rows changed: fusion expanded1024 (6), official_raw (6), sub16 (4), sub64 (6). All primary official_dedup fusion metrics and all single-method metrics remained unchanged. All 90 contrasts remained unchanged. Four fusion abstention rows changed; other abstention rows remained unchanged.
- Ran all nine fusion regression tests successfully, including perturbation of excluded target scores without altering absent scores or rank output.

Threshold serialization note: read CSV threshold values with round-trip float precision (or Python's float parser). pandas default CSV parsing shifts the fusion margin tau_fn10 threshold by one ULP and drops one validation boundary observation when recalculating its rate. The saved decimal value and reported rates are consistent; using `float_precision='round_trip'` reproduces them. This is not a change to the scientific method or reported test results.

## Result interpretation

Fusion top-score threshold calibrated to validation absent false nomination <=10% now gives test present coverage 17.364763%, nominated Recall@5 88.372093%, and absent false nomination 10.443276%. These are retrospective correction measurements. They support the controlled target-removal experiment with per-pool normalization; they do not measure real-world missing-target prevalence or guarantee deployment risk. Main model-selection conclusions based on unchanged official-deduplicated measurements and C1–C3 comparisons remain supported within the original study's limitations.

Acceptance applies to this recorded run. A later clean repetition should match deterministic analysis artifacts before it becomes the canonical reference. Paper/blog integrity additionally requires corrected source mappings, regenerated affected figures/tables, and removal of obsolete pending-correction statements.

## Canonical second-run binding

Final reference run `2fc267cbade54b009d6a8b24d70724b3`, clean source `d7a28788ed2b39a18bdaa8d563aa98ffe5514d04`, passed. Independently compared all six analysis artifacts, three comparison tables and fusion-weight JSON against the reviewed first run: all ten files are byte-identical. Extended finite result pointers correctly reflect those measurements. This report's PASS therefore also applies to the canonical second run promoted under `evidence/corrected-analysis/20261006/`.

Clarification checked during paper review: mass/margin tau_fn10 has validation absent false nomination 9.998962% (10.0% rounded). Its 11.6% table entry is test present coverage; test absent false nomination is 11.7%. The validation calibration rule does not guarantee the same held-out test rate. Table headers/captions must clearly distinguish these columns.
