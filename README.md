# Formula-free MS/MS molecular shortlisting

Standalone study repository, migrated from the model-selection article series.

- [Original detailed article](article/original.md)
- [Executable companion](companion/README.md)
- [Source provenance](evidence/import-manifest.json)
- [Manuscript (PDF)](paper/build/main.pdf) and [LaTeX source](paper/main.tex)

## Status

The original measurements and code are imported. A LaTeX manuscript reporting these **existing** results is
in [`paper/main.tex`](paper/main.tex), with the compiled PDF at [`paper/build/main.pdf`](paper/build/main.pdf).
Rebuild it with `make paper-imported` (system Python and local TeX Live only; it formats archived metrics
and compiles, and runs no experiment, data download, model inference or environment creation). Provenance for
the manuscript is in [`evidence/paper-migration/`](evidence/paper-migration/): claims ledger, content-coverage
map, build receipt, independent AI review and status.

Independent reproduction is **pending**: `protocol.md` is an unconfigured, unapproved scaffold and has not been
executed. The generic harness configuration must not be used to claim verified results. Follow the companion
README for the original runnable workflow. No new experiment, human approval, human review or independent
reproduction is claimed by this migration.

The repository will hold the detailed methods and paper; the blog will provide a shorter accessible explanation. Original third-party licences and notices remain applicable; no blanket relicensing is applied.
