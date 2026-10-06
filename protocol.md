# Protocol status and historical record

The reported results come from the October 2026 study. Its frozen protocol and amendment are preserved below. Independent reproduction remains pending and requires a separate approved plan.

## Historical protocol

These files are byte-identical copies from `downloads/msms-shortlist-results.tar.gz`, under `msms-shortlist-results/protocol/`. Their hashes were checked against the archive and migration audit.

| File | SHA-256 |
|---|---|
| [Frozen original](protocol/historical/protocol-frozen-original.md) | `aa2b30b5fe8b06e95a0793ef05c5d3ffc769fbc8e954a626fc71ae0b700531b6` |
| [Protocol with amendment A1](protocol/historical/protocol-with-amendments.md) | `56f0201795eb28b7299fb77908d4ddbbed8b42e873fa7656a4c9d4b0bd4fd3a2` |
| [Freeze receipt](protocol/historical/protocol-freeze-receipt.txt) | `a9f54a1105e2bf6fb3e0fa571f02d05257636145355f3cd08ac810ca9058c20d` |

The protocol was frozen on 4 October 2026 at 22:07:05Z, before test-fold scoring. It defines the MassSpecGym `formula_seed1` evaluation, candidate pools, methods M0–M5, Recall@5 primary outcome, tie handling, molecule-grouped bootstrap and validation-fitted decline thresholds. Amendment A1 adds exploratory window coverage. The freeze receipt is the original study's record; approval under this repository's research harness remains separate.

## Review and reproduction status

[Review fixes](docs/review-fixes.md) document the software corrections and their implications. Archived exploratory fusion scores were standardised with the target present before its removal. Their target-removed results therefore retain information from the removed target. Historical measurements remain unchanged; corrected fusion needs fresh calibration and evaluation.

The historical commands are in [companion/REPRODUCE.md](companion/REPRODUCE.md). A future reproduction plan must specify outputs, numeric tolerances, realistic compute and storage budgets, stopping rules, and treatment of corrected analyses. Generic scaffold settings in `study.json` do not define those requirements.

`make verify` checks software and evidence integrity. `make paper-imported` compiles archived results. Neither independently reproduces the study. Scientific `smoke` and `reproduce` targets remain gated pending an approved, implemented plan. Future plan amendments belong in `protocol/amendments/`.
