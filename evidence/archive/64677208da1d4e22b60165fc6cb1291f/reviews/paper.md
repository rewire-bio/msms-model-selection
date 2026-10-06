# Corrected paper review — 6 October 2026

Verdict: ready after final rebuild. Automated Codex review, not human scientific review.

Scope: paper/main.tex, corrected generated fusion tables and macros, corrected PNGs, evidence/corrected-analysis/20261006 outputs, and rendered PDF pages 1, 10, 12, 22 and 23. No external literature re-verification, independent training or model inference was performed.

## Findings and disposition

- Availability wording initially implied the historical downloadable code archive matched maintained companion/. Parent corrected this to distinguish maintained code, historical archives and separately indexed corrected evidence.
- Abstract initially described all results as existing results without naming reanalysis. Parent corrected the abstract wording.
- No further actionable discrepancy in the corrected scientific claims was found. A preliminary concern about the mass-margin validation threshold was rechecked and withdrawn: validation is 10.0%; the adjacent 11.6% is test coverage.

## Evidence checks

- Corrected fusion official-deduplicated Recall@5 remains 64.8%; chosen mass weight remains 0.55.
- Pool-size Recall@5 fusion rows are 97.3%, 86.0%, 64.8%, 42.7% for 16, 64, official deduplicated, expanded; generated Table 10 and corrected pool chart agree.
- Corrected fusion top 1/fn 10 threshold 3.1241, coverage 17.4% [14.1,21.1], covered Recall@5 88.4% [81.0,94.1], false nominations 10.4% [8.1,13.1] match CSV, main table, supplemental table and chart.
- Other fusion threshold rows match corrected CSV. Unchanged primary/nonfusion claims remain consistent with comparison receipts.
- Correction methods explicitly remove target before absent-pool normalization and use multiplicity weighting in raw pools, validation-only threshold fitting and saved scores without retraining.
- Historical supplementary precursor/instrument fusion strata remain appropriate because official-deduplicated fusion scoring is unchanged.
- Historical tie-rule figure includes only nonfusion methods; retaining it does not hide changed raw-pool fusion scores.
- Sources distinguish corrected tables from historical supplement and original article. Independent training reproduction remains explicitly pending.

## Visual checks

Rendered pages 1, 10, 12, 22, 23 show clear status box, corrected curves and legends, readable tables and no observed clipping or overlapping content. Build log search found no overfull boxes or undefined references in reviewed build. The final rebuild after availability/abstract edits still needs ordinary build verification.

Blog workspace and its existing article URL are preserved. Blog’s runnable Python example matched corrected CSV outputs exactly; corrected pool/abstention PNGs are copied and visually checked. Immutable study commit pin is still pending parent commit.

## Final clean reproduction review

PASS. Reviewed the full 27-page contact sheet from the final clean reproduction PDF and full-resolution correction pages 12 and 23. No clipping, overlap, missing content or changed-number inconsistency observed. Final figures/tables retain corrected fusion coverage 17.4%, false nomination 10.4%, and threshold 3.1241; the complete source/reproduction check reports 11 deterministic outputs identical. This is automated artifact review and cached-score reproduction only, not original training reproduction or human scientific review.

- Source commit: `8b650adabc3f2cd833acb778dd7dd140d0f0e6f6`.
- Reproduction ID: `9dcf6d1ddcef434daa87ac7e3067f8d9`.
- PDF SHA-256: `11c8ac0be311e017054cefb96092abb11493696e6ac95749ac27b2b777bf6cf4`.
- Contact sheet: `.research/review-reports/final-contact.png`.
- Canonical corrected analysis index at review: 

```json
{
  "schema_version": 1,
  "status": "passed",
  "scope": "cached-score correction; no retraining or independent training reproduction",
  "run": "evidence/corrected-analysis/20261006",
  "run_id": "2fc267cbade54b009d6a8b24d70724b3",
  "artifacts": {
    "evidence/corrected-analysis/20261006/analysis/abstention.csv": "c3f3d195623c51c31c5ed19e5c6843f8a1b26589212cbdedc0529e0a075c0dd8",
    "evidence/corrected-analysis/20261006/analysis/contrasts.csv": "cd83a417c18fdb03e7a063c07fcd146f512b25403aa89b4937880324430e661a",
    "evidence/corrected-analysis/20261006/analysis/metrics.csv": "472a309b48634618018708bf7553ace45b37232f36436a345c28f26f1974b39c",
    "evidence/corrected-analysis/20261006/analysis/pool-sizes.csv": "7ba18122e5a2a77e296f0d037f3bc82ede24286ff0c7924b40862e935d5533b5",
    "evidence/corrected-analysis/20261006/analysis/random-repeats.json": "d6e58d93e93c3c4f8043ea6507ed93652cb27edbb3f4f345cb85955c543c6156",
    "evidence/corrected-analysis/20261006/analysis/risk-coverage-curves.json": "f39d9a1308f044e72aec9871701cf23d72a4da09102b2feae7603753099145b7",
    "evidence/corrected-analysis/20261006/comparison-abstention.csv": "5a165f8a420ffae81e6ce7d7e0fbbb2e0fb2314319ac9e2d30f1b43b7fa8c8da",
    "evidence/corrected-analysis/20261006/comparison-contrasts.csv": "0b14b32778d90ce67bb8df5a2e9f8c67199c29f4bfb69ce4415ab90a07732d4d",
    "evidence/corrected-analysis/20261006/comparison-metrics.csv": "9a5b363ebdb632557984dff24e4936855c3d8cfd5153fcd993647d7765e8e387",
    "evidence/corrected-analysis/20261006/execution.log": "fc9787d4672b412659af332e1d322fb7eafecbf968fae2e3b764559b1ec72f63",
    "evidence/corrected-analysis/20261006/fusion-weight.json": "cdc2386f6c10f9c3f677386119e7b10ab261494f54b15c0cea28d69cd32b4ef6",
    "evidence/corrected-analysis/20261006/results.json": "5c7651d64222d03139e18bb201610b630509ad9b1c3fc3a5400264188992f718",
    "evidence/corrected-analysis/20261006/run-receipt.json": "5c0ab90cca0990e196aed8eaa516126238e2223995339c116202ae3e498b4533",
    "paper/figures/corrected/02-pool-size-stress.png": "fa3837600c4ebfa4f54d7a6d786c587b22b7a343223006c24a3e07c6a1252679",
    "paper/figures/corrected/04-decline-to-nominate.png": "29dd93309e66e0c0fa5e05fdbcbf8e6c328d90c557fed96104212d9bd51e0e0d"
  }
}
```
