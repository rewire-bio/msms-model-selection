# Formula-free MS/MS molecular shortlisting

Standalone study repository, migrated from the model-selection article series.

- [Latest detailed article with corrected fusion results](article/blog-research-version-20261006.md) — preserved before the shorter blog replacement
- [Original detailed article](article/original.md)
- [Executable companion](companion/README.md)
- [Protocol status and index](protocol.md), including the [frozen historical protocol](protocol/historical/protocol-frozen-original.md), the [protocol with amendment A1](protocol/historical/protocol-with-amendments.md) and the [freeze receipt](protocol/historical/protocol-freeze-receipt.txt)
- [Review fixes and known limitations](docs/review-fixes.md)
- [Source provenance](evidence/import-manifest.json)
- [Manuscript (PDF)](paper/build/main.pdf) and [LaTeX source](paper/main.tex)

## Status

The original measurements (runs of 3–5 October 2026) and code are imported. The study followed a protocol frozen on 2026-10-04 before any test-fold score existed; that protocol is archived as historical evidence under `protocol/historical/`. It is not an approval under this repository's harness.

A cached-score correction on 6 October 2026 recomputed fusion separately within each candidate pool and recalibrated its thresholds on validation. The selected mass weight (0.55), official-deduplicated fusion Recall@5 (64.8%), all single-method results and all paired contrasts are unchanged. Expanded-pool fusion Recall@5 changes from 43.9% to **42.7%**. At the validation-fitted false-nomination threshold, fusion covers **17.4%** of target-present queries, with **88.4%** Recall@5 among nominated queries and **10.4%** false nominations on target-removed queries.

The [corrected evidence index](evidence/corrected-analysis/current.json) binds numerical tables, comparisons and receipts to their checksums. The [paper](paper/build/main.pdf) uses these corrected outputs and unchanged historical supplementary evidence. Original archives and articles remain intact. See [correction protocol](protocol/amendments/2026-10-06-corrected-analysis.md) and [review fixes](docs/review-fixes.md).

**Independent training reproduction remains pending.** This correction reuses saved component scores, nonfusion ranks and candidate pools; it does not retrain models, regenerate pools or establish original data authenticity. The 28 cached input files (401.7 MB) are locally available and hash-identified, but are not distributed in Git. Their manifest source URLs document provenance; they are not direct downloads of those files.

## Make targets

| Target | What it does | What it does not do |
|---|---|---|
| `make verify` | Inexpensive checks: SHA-256 of imported files and archive members against recorded digests, extraction of evidence from the archive, and companion regression tests on small synthetic inputs | Does not download data, train, score or recompute any benchmark number. Passing it is not scientific verification. |
| `make paper-imported` | Validates historical and corrected saved evidence, formats tables into `paper/generated/` and compiles `paper/main.tex` (system Python, local TeX Live, `rsvg-convert`) | Runs no experiment, data download, model inference or environment creation. A successful build is not reproduction. |
| `make corrected-analysis` | Recalculates fusion and analysis from the hash-verified cached inputs | No retraining or new pools. |
| `make reproduce-corrected` | Repeats the cached-score correction from inputs supplied through `MSMS_CACHED_INPUT_ROOT`, compares deterministic outputs and rebuilds the paper | Requires the original cached files and local TeX tools; does not reproduce training. |
| `make smoke`, `make reproduce` | Intentionally disabled. They stop with an error explaining that no approved, implemented reproduction plan exists. | They do not run the historical workflow. |

Validation status is recorded in [`docs/review-fixes.md`](docs/review-fixes.md). The historical benchmark workflow is documented command by command in [`companion/REPRODUCE.md`](companion/REPRODUCE.md). It needs external data and hours of training, and it is not wired to any make target.

## Licences

The repository will hold the detailed methods and paper; the blog will provide a shorter accessible explanation. Original third-party licences and notices remain applicable; no blanket relicensing is applied.
