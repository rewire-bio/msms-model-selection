# msms-shortlist: formula-free MS/MS candidate shortlisting

Companion code for the rewire.it article on choosing a formula-free retrieval method for a five-structure shortlist. It has two parts:

1. **Own-input CLI** (`msms_shortlist/`): ranks your candidate structures for your spectra, with metadata checks, a ppm window, duplicate removal, tie flags, an optional decline threshold and a provenance file.
2. **Benchmark scripts** (`scripts/`): the pipeline used for the article's measurements on MassSpecGym (formula split seed 1), with subsequent review fixes. The results archive preserves the historical version.

The output is a shortlist for confirmation with standards or orthogonal evidence. It is not an identification, the scores are not probabilities, and identity is 2D (stereoisomers are not distinguished).

## Install (pinned)

Python 3.11 and [uv](https://docs.astral.sh/uv/):

```bash
uv sync            # uses uv.lock: torch 2.2.1, rdkit 2023.9.6, numpy 1.25.0, pandas 2.2.1
```

## Rank your own spectra

Spectra: an MGF file with `PEPMASS`, `CHARGE` and `ADDUCT` in every block (`COLLISION_ENERGY` optional). Candidates: a CSV with `id` and `smiles` columns, frozen before you look at any scores.

```bash
# Mass-error ranking only (no model files needed)
uv run msms-shortlist --spectra examples/mh.mgf --candidates examples/mh-candidates.csv \
    --out out/mh-mass.csv

# Trained DreaMS + Morgan alignment model
uv run msms-shortlist --spectra examples/mh.mgf --candidates examples/mh-candidates.csv \
    --model models/dreams_morgan_formula_seed1_fp16.pt \
    --dreams weights/DreaMS_embedding_model_torchscript.pt \
    --thresholds models/thresholds.json --out out/mh-model.csv
```

Supported adducts: `[M+H]+`, `[M+Na]+`, `[M+NH4]+`, `[M+K]+`, `[M-H]-`. The trained model saw only `[M+H]+` and `[M+Na]+`; other adducts run with a warning. A spectrum is refused, not ranked, when the precursor m/z, adduct or charge is missing or inconsistent. If no candidate lies inside the ppm window (default 10 ppm), the output says so instead of ranking an empty pool.

### Input handling after the code review

The revised CLI implements issues #5–#7; validation is recorded in [the review report](../docs/review-fixes.md). Archived notebook outputs remain unchanged. `COLLISION_ENERGY=nan`, used by `examples/mna.mgf`, remains the missing-energy sentinel; infinite energy is refused.

- **Refusals are per spectrum.** An unreadable or unsupported `CHARGE` (for example `unknown`) or `COLLISION_ENERGY` (for example `35 eV`) refuses that spectrum and records the reason. The remaining spectra in the batch are still ranked, and the CSV and provenance file are still written. Previously such a value raised an exception and the whole batch produced no output.
- **Peaks must be usable.** Peaks with non-finite m/z, non-finite intensity or non-positive intensity are discarded. The spectrum is refused only if no usable peaks remain. Previously an all-zero spectrum was divided by zero and passed to the model as NaN.
- **Scores must be finite.** If any ranking score for a spectrum is NaN or infinite, the spectrum is refused. It is not sorted, compared with the threshold or nominated. Previously a NaN top score failed the `score < tau` test and was reported as `nominate shortlist`.
- **Isotope labels are kept; stereochemistry is removed.** For your own candidates, the CLI removes stereochemistry for 2D identity but keeps isotope labels. Deduplication and exact mass therefore use the labelled composition: `[13CH3]CO` and `CCO` stay separate, with masses 47.045 and 46.042 Da. Previously RDKit's `isomericSmiles=False` dropped isotope labels as well, so a labelled candidate was silently merged with its unlabelled form and could fall outside its own precursor window. The model was trained on MassSpecGym structures and has not been evaluated on isotope-labelled candidates. Treat model scores for them as untested.

### Difference from the historical benchmark normalisation

The historical normalisation used `isomericSmiles=False`, which removed isotope labels along with stereochemistry. The CLI and benchmark scripts share the corrected `canonical_2d` helper: future pool generation preserves isotope labels too. Previously generated pools and archived results are unchanged. The review did not establish whether affected labelled molecules occurred in the historical benchmark. Regeneration with corrected code must record this normalization change.

The DreaMS TorchScript file (468 MB, MIT) comes from Hugging Face `roman-bushuiev/DreaMS` at revision `c81a62766b10`, SHA-256 `df69866990b194b27d5497e440f87f6ceca568ee512e7c22cb1f278721376f0c`. It reproduces the released MassSpecGym DreaMS embeddings (minimum cosine 0.9999999 on 64 spectra; run V01). Put it at `weights/DreaMS_embedding_model_torchscript.pt`:

```bash
mkdir -p weights
curl -fL -o weights/DreaMS_embedding_model_torchscript.pt \
  https://huggingface.co/roman-bushuiev/DreaMS/resolve/c81a62766b10dd1d39fcda3edec5ef88623e5f6b/DreaMS_embedding_model_torchscript.pt
```

### Get the trained model

The trained DreaMS + Morgan bundle (`msms-shortlist-dreams-morgan-model.tar.gz`, 45,138,751 bytes, SHA-256 `646bbe4fbb14bda60e3544d4a963c9319b6564663c9b0752cd5e92b879eeffc9`) is published as three byte-for-byte parts, because the hosting limit is 25 MiB per file: `.part01` and `.part02` (20,971,520 bytes each) and `.part03` (3,195,711 bytes). Download the three parts into the companion's root directory (the one containing `pyproject.toml`) and run the script from there, either a downloaded copy of `reassemble-model.sh` or the one in `scripts/`:

```bash
sh scripts/reassemble-model.sh   # checks each part, joins 01+02+03, checks the original SHA-256, extracts
mkdir -p models
cp msms-shortlist-model/dreams_morgan_formula_seed1_fp16.pt msms-shortlist-model/thresholds.json models/
```

Setting `BASE_URL` to the directory the parts are served from makes the script download them first. Without the script: `cat` the parts in order (`part01 part02 part03`) into `msms-shortlist-dreams-morgan-model.tar.gz`, compare `shasum -a 256` (or `sha256sum`) with the value above, then `tar -xzf`. The script refuses to join if any part's SHA-256 differs from the values built into it, which are the same as those in `msms-shortlist-dreams-morgan-model.parts.sha256`. The archive was created on macOS and carries a few extended-attribute records; GNU tar may print warnings about unknown extended header keywords, which do not affect the extracted files.

## Reproduce the benchmark

The unchanged, manifest-tracked `REPRODUCE.md` preserves the historical command list, data hashes and run receipts. Where `REPRODUCE.md` says `protocol.md`, it means the historical study protocol, not the repository-root index page. The frozen original is at `../protocol/historical/protocol-frozen-original.md` (SHA-256 `aa2b30b5…31b6`), and the version with amendment A1 is at `../protocol/historical/protocol-with-amendments.md`. These commands document the historical run. They have not been re-executed, and no independent reproduction has been approved.

The exploratory fusion script (`scripts/fuse_scores.py`) as archived standardises scores over the target-present `official_dedup` pool and reuses them for `absent`. Fusion's archived target-absent confidences therefore depend on the removed target (issue #9). The archived abstention analysis also mishandles missing or failed spectra (issue #8); the archived runs reported none. The corrected implementation standardises within each actual candidate pool and handles missing spectra explicitly. Fresh calibration and evaluation are required before reporting corrected fusion results. See `../docs/review-fixes.md`.

### Fusion artifact compatibility

New fusion files use schema version 2 and `fusion_normalization=per_pool_v2`. The `pool_scores` group stores scores standardised within each evaluated pool; the top-level `scores` dataset contains the `official_dedup` scores. `rank_stats.py` validates this schema and uses the matching scores for each pool.

Historical fusion score files lack per-pool normalization. `rank_stats.py` rejects them by default; use `--allow-legacy-fusion` explicitly to recover the historical deletion-after-standardisation calculation. Its output is labelled `legacy_post_scoring_deletion` and retains the target-removal limitation described above. Stored historical score and rank files remain unchanged.

## Licences

Code: MIT. `msms_shortlist/towers.py` adapts inference code from MSAlign (MIT, Copyright (c) 2026 KrzakalaPaul). Data and weights keep their own licences: MassSpecGym (MIT), the MSAlign Zenodo bundle (CC BY 4.0), DreaMS weights (MIT). No source weights or data are bundled in this archive.
