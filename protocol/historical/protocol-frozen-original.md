# Frozen evaluation protocol: formula-free MS/MS shortlisting (article 335)

Status: **FROZEN** at the timestamp recorded in `evidence/protocol-freeze-receipt.txt` (SHA-256 of this file). Written before any test-fold outcome of any method was computed or viewed. Smoke runs used only training and validation rows (S02 to S04; S03 and S04 used a split file whose "test" rows are validation rows). Amendments, if any, go in section 12 with a date and reason; the original text above them is not edited.

## 1. Question and decision

A metabolomics researcher has an MS/MS spectrum with a trustworthy precursor m/z, adduct and charge, and a frozen list of candidate structures whose monoisotopic masses lie within 10 ppm of the implied neutral mass. They can examine five structures by orthogonal means (standards, retention time, orthogonal fragmentation). Which formula-free ranking method should produce those five, and when should it decline to nominate?

A shortlist is a set of structures to confirm, not an identification. Recall@5 is the primary decision metric.

## 2. Data, split and populations

- Dataset: MassSpecGym as processed by the MSAlign authors (Zenodo 10.5281/zenodo.22830464, `massspecgym.zip`, MD5 `96e8b1885cf4120aaef93154ce809cbd`).
- Split: `formula_seed1` (MSAlign v2 formula split, seed 1). Train 210,825 spectra / 26,087 molecules; validation 9,631 / 1,428; test 10,648 / 1,421.
- Primary population: all 10,648 test spectra. No spectrum is excluded. Every spectrum carries an [M+H]+ or [M+Na]+ adduct, charge +1, and a precursor m/z.
- Identity convention: 2D structure. Molecules are compared as RDKit canonical non-isomeric SMILES (the MSAlign normalisation). Stereoisomers are the same identity. The target is never a duplicate of itself in a pool.
- Group for uncertainty: the target molecule (its 2D SMILES). All spectra of one molecule are resampled together.
- Secondary descriptive population (cheap baselines only): `mces_1` test fold (official MassSpecGym MCES split), 17,556 spectra / 2,997 molecules.

## 3. Candidate pools

Built once per target molecule by `companion/scripts/build_pools.py`, saved with hashes before scoring. All pools for a target are subsets of one manifest.

| Pool | Definition | Role |
|---|---|---|
| `official_raw` | The released 256-candidate mass list exactly as distributed, duplicates included (each counted with its multiplicity) | Reproduction of the published setting |
| `official_dedup` | `official_raw` with repeated 2D structures removed (first occurrence kept) | **Primary** |
| `sub16`, `sub64` | Target plus 15 or 63 decoys drawn without replacement from `official_dedup` decoys, seeded by SHA-256 of the target SMILES | New stress test: smaller pools |
| `expanded1024` | `official_dedup` plus extra decoys from the MassSpecGym 4M molecule set (HF revision `d2e86d0c3bd9`) with RDKit exact mass within 10 ppm of the target's exact mass, excluding molecules whose first InChIKey block or 2D SMILES equals the target's or an existing member's, sampled (seeded as above) until the pool holds 1,024 structures or the window is exhausted | New stress test: larger pools from a declared database snapshot |
| `absent` | `official_dedup` with the target removed | Controlled target-removal stress test |

Artificial target removal is a controlled stress test. It is not a measurement of how often real queries lack their answer in a database.

## 4. Methods (formula-free track only)

Every method receives the same inputs: the peak list (top 100 peaks as released), precursor m/z, adduct (hence charge), collision energy where the released model uses it, and the candidate structures. No method receives the target's molecular formula. No reference-spectrum cosine method is run, because it would require library spectra for every candidate, which this setting does not provide.

| ID | Method | Training | Score |
|---|---|---|---|
| M0 | Random ordering | none | 100 repeated random orderings (seeds 0 to 99); expected value also computed analytically |
| M1 | Precursor mass error | none | minus absolute ppm error between adduct-corrected precursor mass and candidate RDKit monoisotopic mass (masses rounded to 1e-6 Da, ppm to 1e-6) |
| M2 | DeepSets + Fourier features (fingerprint predictor) | released `model_zoo` config, 50 epochs, seed 42, checkpoint by validation loss (released rule) | cosine between predicted and candidate Morgan fingerprint |
| M3 | Emb-Cos (binned spectrum and fingerprint alignment) | released config, 16,000 steps, seed 42, checkpoint by validation R@1 (released rule) | cosine in the learned space |
| M4 | MSAlign alignment, DreaMS + Morgan pair (released code, newly trained) | released `massspecgym_formula` config with the molecule representation set to `morgan_2_4096`, 30,000 steps, seed 42, checkpoint by validation R@1 (released rule) | cosine in the learned space |
| M5 (exploratory) | Late fusion of M4 and M1 | weight w in {0, 0.05, ..., 1.0} for z-scored scores, chosen by validation R@5 on `official_dedup` | (1 - w) z(M4) + w z(M1) |

Hyperparameters are the released defaults; no tuning on any fold beyond the released checkpoint selection on validation and the M5 weight. One training seed per learned method is budgeted. A second seed for M4 may be run only if the first completes with time to spare; if run, both seeds are reported and neither is preferred. Formula-informed methods (MIST, FLARE, MVP, MSAlign+Filter) and the published DreaMS + MolDeBERTa MSAlign appear only as published numbers in a separate table.

## 5. Metrics

- Primary: Recall@5 on `official_dedup`, test fold, spectrum-level average.
- Secondary: Recall@1 and Recall@20; the same on every other pool.
- Ties: primary rule is the **expected value under uniform random tie-breaking**: for a target with b decoys scoring strictly higher and t decoys tied, Recall@k = clip((k - b)/(t + 1), 0, 1). The released strict rule (a tied decoy ranks ahead of the target) is reported alongside, and is the rule used when comparing with published numbers.
- Coverage: the denominator is every test spectrum. A method that fails on a spectrum (exception, non-finite score, missing representation) scores a miss for that spectrum, and the failure count is reported. Pool sizes (minimum, median, count below nominal size) are reported per pool.
- Also reported: mean candidates per pool; per-instrument strata (Orbitrap, QTOF) if the TSV join is unambiguous, descriptive only.

## 6. Uncertainty

- 95% percentile intervals from 2,000 bootstrap resamples of target molecules (seed 20261004), resampling all spectra of a chosen molecule together.
- Paired contrasts use the same resampled molecules for both methods.
- Pre-declared primary contrasts (Recall@5, `official_dedup`, test): C1 M4 minus M1; C2 M4 minus M3; C3 M2 minus M1. Everything else is descriptive. With one split seed and one training seed, intervals reflect molecule sampling only, not split or training variation; the paper's split-seed SDs are quoted for context.

## 7. Abstention (decline to nominate)

- Confidence: the top-1 score in the pool (cosine for M2 to M4; minus the smallest |ppm| for M1). Margin (top-1 minus top-2) is a secondary exploratory confidence.
- Calibration set: validation fold, each spectrum evaluated twice: with `official_dedup` (target present) and with `absent`.
- Two thresholds fitted on validation only and then frozen: tau_cov90, the threshold that keeps 90% of target-present validation queries; tau_fn10, the lowest threshold at which at most 10% of target-absent validation queries are nominated.
- Test report for each threshold: coverage of target-present queries; Recall@5 among nominated target-present queries; false-nomination rate among target-absent queries; with molecule-grouped intervals. Full risk-coverage curves on test are descriptive.
- No claim is made about the natural rate of absent targets. A mixed example (for instance 50% absent) is labelled as illustrative arithmetic.

## 8. Reproduction check

For M2 to M4, the released evaluation (strict ties, `official_raw`) on test is compared with the v2 paper's formula-split mean and SD (M2: DeepSet 4.7 ± 0.6 / 13.0 ± 1.3 / 27.5 ± 2.0; M3: Emb-Cos 42.7 ± 3.0 / 65.2 ± 2.8 / 80.4 ± 1.6; M4: DreaMS-Fingerprint 38.6 ± 2.8 / 60.4 ± 2.1 / 77.6 ± 0.8 for R@1/5/20). A value inside mean ± 2 SD is "consistent"; outside is "not reproduced at this seed". The scoring harness must reproduce the trainer's own validation R@1 for the selected checkpoint to 0.1 percentage points before any test scoring.

## 9. Resources

Report wall time, peak resident memory and device for: candidate fingerprint cache, each training run, pool construction, scoring per method and pool, and own-input CLI runs. Receipts are written by the run itself into an immutable run directory `runs/<ID>-<name>-<UTC timestamp>/`. A re-run creates a new directory; a cached result is never relabelled as a fresh timing.

## 10. Own-input recipe

The companion CLI validates metadata (adduct in a declared table, charge consistent, precursor m/z positive), computes the neutral mass, filters a user candidate file to a declared ppm window, removes duplicate 2D structures, and writes a ranked CSV with scores, ppm errors, tie flags and provenance. It refuses to rank when metadata are missing or inconsistent, and reports "no candidate within window" rather than ranking an empty pool. The demonstration uses real MassSpecGym spectra chosen by a fixed rule (first test-fold spectrum of each of three declared kinds: an [M+H]+ easy case, an [M+Na]+ case, and one target-absent case built by removing the target), selected before any of their scores are viewed.

## 11. What will not be claimed

No identification probability, no calibrated probability from cosine scores, no claim about natural target absence, no claim beyond MassSpecGym formula split seed 1 and its declared pools, no claim about the published MolDeBERTa MSAlign beyond quoting the paper, no "novelty" unless supported by a literature search.

## 12. Amendments

(none)
