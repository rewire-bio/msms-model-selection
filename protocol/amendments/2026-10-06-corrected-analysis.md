# Cached-score correction amendment — 2026-10-06

Status: frozen for the user-authorized cached-score correction. The user requested “do the corrected analysis please” after the stated cached-score scope and 15–30 minute estimate; coordinator records this authorization, with no claim of a new preregistration. This retrospective correction does not claim preregistration. The original protocol and measurements remain immutable.

## Scope and purpose

Recompute exploratory fusion with pool-specific normalization, removing the target before computing normalization for the target-absent pool. Recheck every reported method using the corrected analysis code. Reuse frozen candidate pools, saved component scores and nonfusion ranks from the original formula_seed1 validation/test experiment. No training, inference, new candidate pools, changed data, downloads or additional test-set optimization are permitted.

## Frozen choices

The input manifest identifies each existing file by relative path, size and SHA-256. Validation and test spectra and molecular grouping come from the unchanged metadata and formula_seed1 split. Component methods are mass, MSAlign, Emb-Cos and DeepSets. Fusion combines MSAlign and mass after independent z-normalization within each evaluated pool. Official-raw normalization weights candidates by their original multiplicity. Target-absent normalization excludes the target before calculating moments.

Choose mass weight on validation expected-tie official-deduplicated Recall@5 from 0, 0.05, …, 1; ties select the smaller weight. Apply it once to test. Retain 2,000 molecule-grouped bootstrap replicates with seed 20261004, Recall@1/5/20, strict and expected tie rules, original contrasts, confidence definitions, validation-selected thresholds, and descriptive test risk–coverage curves. The corrected failure handling remains active; no predictions are intentionally removed.

Compare all shared numeric historical and corrected columns with absolute tolerance 1e-8 and relative tolerance zero. Missing or duplicate comparison keys are errors. Require invariance for nonfusion metrics, contrasts and abstention, and official-deduplicated fusion recall estimates and intervals. Stop and investigate any violation rather than silently accepting it. Other fusion pools and target-absent thresholds may change. Record their before/after values even when unchanged. Historical target-absent fusion values describe post-scoring deletion and cannot support target-unavailable performance claims.

## Execution and evidence

Use the companion Python 3.11 environment with NumPy 1.25.0, pandas 2.2.1 and h5py 3.11.0. The standalone command is:

```
companion/.venv/bin/python scripts/reanalyse.py --config configs/corrected-analysis.json --output evidence/corrected-analysis/run-ID --work-dir results/run-ID-scores
```

The default input root is `.research/corrected-inputs`, populated with byte-identical copies of the original cached inputs. `--input-root` may select another directory with the same relative paths. `--validate-only` verifies hashes without calculating scientific results. The harness can supply `--config` and `--output`; an existing empty output directory is allowed. Never overwrite existing outputs or historical files.

Save small analysis tables, comparison tables, curves, weight selection, finite deterministic `results.json`, command logs and a separate runtime/source/input-hash receipt. Large fusion score/rank files stay under ignored `results/`. The receipt uses portable path tokens. Budget: 900 seconds per execution, at most two attempts, and 4096 MB working storage under the parent harness. A failed or interrupted attempt is retained and is not a completed correction. This workflow reproduces the cached-score correction only, not the original training experiment.

## Execution record and independent correction reproduction

The first correction completed at source revision `70b53a7` in run `aed83c1f079c445c9afcc07654268302`. A second reference execution records the same scientific design after adding finite result pointers and the clean reproduction route; it is not another model selection or parameter search. Both attempts are retained. Independent cached-score reproduction has its own 900-second limit and copies validated inputs supplied through `MSMS_CACHED_INPUT_ROOT`; those raw cached inputs are not currently publicly downloadable. It reruns the fixed correction, requires byte-identical deterministic analysis artifacts, and regenerates the paper in an ignored temporary source tree. `make reproduce-corrected` produces `results/reproduction/results.json` and `results/reproduction-paper.pdf` without modifying tracked evidence, figures or manuscript files. Original training reproduction remains outside this scope.
