# Review fixes

Review of commit `87a96d572a459c830d4df3191812cf97fe62de79` identified nine issues. The fixes preserve historical measurements and distinguish software validation from scientific reproduction.

## Changes

| Issue | Fix |
|---|---|
| [#1](https://github.com/rewire-bio/msms-model-selection/issues/1) | Replaced the π fixture with a protocol index. Extracted the frozen historical protocol, amendment and receipt; their hashes match the archive. |
| [#2](https://github.com/rewire-bio/msms-model-selection/issues/2) | Separated inexpensive verification and imported-paper compilation from scientific reproduction. Scientific targets require an approved, implemented plan. |
| [#3](https://github.com/rewire-bio/msms-model-selection/issues/3) | Training queue failures produce a failing exit status instead of reporting success. |
| [#4](https://github.com/rewire-bio/msms-model-selection/issues/4) | Paper validation checks the evidence inputs actually consumed against their recorded hashes. |
| [#5](https://github.com/rewire-bio/msms-model-selection/issues/5) | Discard unusable peaks; refuse spectra with none remaining. Refuse non-finite ranking scores before sorting or nomination. |
| [#6](https://github.com/rewire-bio/msms-model-selection/issues/6) | Preserve isotope labels while removing stereochemistry. The shared helper changes future CLI candidates and generated benchmark pools; historical files remain unchanged. |
| [#7](https://github.com/rewire-bio/msms-model-selection/issues/7) | Malformed charge or collision energy refuses the affected spectrum while valid batch members retain outputs. NaN energy remains a missing-value sentinel; infinity is refused. |
| [#8](https://github.com/rewire-bio/msms-model-selection/issues/8) | Handle missing and failed spectra explicitly in abstention analysis, preserving the intended denominator. |
| [#9](https://github.com/rewire-bio/msms-model-selection/issues/9) | Standardise fusion components within each actual candidate pool. Label archived fusion results with their historical target-removal limitation. |

## Effect on reported results

The review does not establish that the primary single-method benchmark is invalid. Every row of the archived `companion/results/metrics.csv` and `mces1-cheap-baselines-metrics.csv` records zero missing or failed spectra. The missing-spectrum defect is therefore not known to have changed those measurements.

Archived exploratory fusion scores were standardised over `official_dedup` with the target present and reused across pool variants. Removing the target afterwards leaves its influence in the remaining scores. Archived target-removed thresholds, coverage and false-nomination rates do not establish performance when fusion receives a genuinely target-absent pool. These numbers remain unchanged and are qualified in the paper.

Corrected per-pool standardisation also changes future subset and expanded-pool fusion calculations. Corrected thresholds and measurements require fresh calibration and evaluation. No new scientific run or independently reproduced result is reported here.

The isotope bug was demonstrated with user-supplied labelled candidates. The review did not establish its occurrence in the historical benchmark. New pool generation uses the corrected shared helper and must record that normalization change.

## Validation and remaining work

The CLI suite passes **33 regression tests**, covering isotope identity and mass filtering, stereo equivalence, invalid peaks, direct embedding input preparation, NaN and infinite scores, malformed metadata in mixed batches, argument guards and the shipped missing-energy example. The three historical protocol copies match their archived SHA-256 values.

`make verify` passed all **60 regression tests** (7.235 seconds). Evidence extraction checked **14 archive members**, generated **16 files**, and found **zero mismatches**; the ledger generated **23 evidence-linked claims with input integrity checks**. `make paper-imported` built **27 pages** with **zero LaTeX or BibTeX warnings**. All 27 pages were rendered and inspected in contact sheets; pages 1, 7, 12 and 23 were also inspected individually. No clipping or overlapping content was found. These checks validate software behavior, evidence integrity and compilation; they do not independently reproduce scientific results. `companion/REPRODUCE.md` remains the unchanged historical command record; its `protocol.md` reference means the archived study protocol linked from the root index.

Independent reproduction remains pending. Generic `study.json` scaffold budgets and tolerances do not define a reproduction plan; an owner-approved plan must specify realistic resources, acceptance criteria and how corrected analyses will be reported separately from archived results.

## Corrected cached-score analysis (6 October 2026)

The owner requested reanalysis using saved scores and pools. The correction now replaces fusion pool-variant and abstention values in the maintained paper. All nonfusion results, paired contrasts, official-deduplicated fusion metrics, the selected weight and its validation grid remain unchanged. Expanded-pool fusion Recall@5 is 42.7% (previously 43.9%); top-score abstention covers 17.4% of present queries (previously 21.8%), with 88.4% Recall@5 among nominated and 10.4% false nominations. Exact values, intervals and all differences are in `evidence/corrected-analysis/20261006/`.

The earlier validation and pending-correction statements above describe the first fixes PR. The new correction does not overwrite those historical inputs and does not claim independent training reproduction.
