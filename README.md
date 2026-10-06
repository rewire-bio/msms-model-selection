# Formula-free MS/MS molecular shortlisting

Standalone study repository, migrated from the model-selection article series.

- [Original detailed article](article/original.md)
- [Executable companion](companion/README.md)
- [Protocol status and index](protocol.md), including the [frozen historical protocol](protocol/historical/protocol-frozen-original.md), the [protocol with amendment A1](protocol/historical/protocol-with-amendments.md) and the [freeze receipt](protocol/historical/protocol-freeze-receipt.txt)
- [Review fixes and known limitations](docs/review-fixes.md)
- [Source provenance](evidence/import-manifest.json)
- [Manuscript (PDF)](paper/build/main.pdf) and [LaTeX source](paper/main.tex)

## Status

The original measurements (runs of 3–5 October 2026) and code are imported. The study followed a protocol frozen on 2026-10-04 before any test-fold score existed; that protocol is archived as historical evidence under `protocol/historical/`. It is not an approval under this repository's harness.

A LaTeX manuscript reporting these **existing** results is in [`paper/main.tex`](paper/main.tex). Provenance for the manuscript is in [`evidence/paper-migration/`](evidence/paper-migration/): claims ledger, content-coverage map, build receipt, independent AI review and status.

Independent reproduction is **pending**. No reproduction plan has been written or approved, and none has been executed. No new experiment, human approval, human review or independent reproduction is claimed.

Code review (GitHub issues #1–#9) found defects in the companion CLI, the training queue, the paper validator and the analysis code. One affects how an archived exploratory result should be read: the fusion target-absent abstention numbers. See [`docs/review-fixes.md`](docs/review-fixes.md). Archived measurements are kept unchanged.

## Make targets

| Target | What it does | What it does not do |
|---|---|---|
| `make verify` | Inexpensive checks: SHA-256 of imported files and archive members against recorded digests, extraction of evidence from the archive, and companion regression tests on small synthetic inputs | Does not download data, train, score or recompute any benchmark number. Passing it is not scientific verification. |
| `make paper-imported` | Formats archived values into `paper/generated/` and compiles `paper/main.tex` (system Python, local TeX Live, `rsvg-convert`) | Runs no experiment, data download, model inference or environment creation. A successful build is not reproduction. |
| `make smoke`, `make reproduce` | Intentionally disabled. They stop with an error explaining that no approved, implemented reproduction plan exists. | They do not run the historical workflow. |

Validation status is recorded in [`docs/review-fixes.md`](docs/review-fixes.md). The historical benchmark workflow is documented command by command in [`companion/REPRODUCE.md`](companion/REPRODUCE.md). It needs external data and hours of training, and it is not wired to any make target.

## Licences

The repository will hold the detailed methods and paper; the blog will provide a shorter accessible explanation. Original third-party licences and notices remain applicable; no blanket relicensing is applied.
