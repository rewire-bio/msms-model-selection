# Reproducing the article's measurements

Everything below ran on an Apple M4 (10 cores, 16 GB RAM, macOS) without CUDA. Wall times are from the run receipts. The protocol (`protocol.md`, SHA-256 `aa2b30b5fe8b06e95a0793ef05c5d3ffc769fbc8e954a626fc71ae0b700531b6` for the frozen original) was fixed before any test-fold score existed.

## 1. Sources and hashes

| Item | Where | Check |
|---|---|---|
| MSAlign code | `git clone https://github.com/KrzakalaPaul/MSAlign-NeurIPS2026 && git checkout c2ef425b68749052a17b9cdd5f5f11709322654e` | MIT |
| Processed MassSpecGym, splits, candidates, DreaMS embeddings | Zenodo 10.5281/zenodo.22830464, `massspecgym.zip` (1,078,913,065 B) | MD5 `96e8b1885cf4120aaef93154ce809cbd`, CC BY 4.0 |
| MassSpecGym 4M molecule set (larger pools) | HF dataset `roman-bushuiev/MassSpecGym` @ `d2e86d0c3bd905a6d578c0dd6053ed2bd41f9c2a`, `data/molecules/candidate_pools/MassSpecGym_retrieval_molecules_4M.tsv` | SHA-256 `1f8ca23530d594836a29f7b07daff3698b558135604d957d3c5d82b58ff95e5f`, MIT |
| MassSpecGym TSV (identifiers, instrument type) | same revision, `data/MassSpecGym.tsv` | SHA-256 `0c9cc50450def3f0d4fe2dc09dea1105fc15e635db8c6656bc3e3be37a3bcd95` |
| DreaMS TorchScript (own-input only) | HF `roman-bushuiev/DreaMS` @ `c81a62766b10dd1d39fcda3edec5ef88623e5f6b` | SHA-256 `df69866990b194b27d5497e440f87f6ceca568ee512e7c22cb1f278721376f0c`, MIT |

Unzip `massspecgym.zip` (the `annotated_peaks.json` member is not needed) and link `massspecgym/` into the MSAlign checkout as `data/massspecgym`. Create the MSAlign environment with `uv sync --frozen` in the checkout (torch 2.2.1, lightning 2.6.1, rdkit 2023.09.6).

## 2. One storage patch

`patches/msalign-c2ef425-lzf-fingerprint-cache.diff` adds `compression="lzf"` to the candidate fingerprint HDF5 dataset (3.8 GB becomes 987 MB). Values read back are identical.

## 3. Commands (run from the MSAlign checkout)

```bash
S=/path/to/companion/scripts
# candidate Morgan fingerprints (239 s, 4 workers)
python precompute_representations.py massspecgym --candidate-map official_candidates_by_mass \
    --representations fingerprint --workers 4

# training (one at a time; released configurations)
python $S/train_msalign_variant.py --config massspecgym_formula --split formula_seed1 \
    --spectrum dreams --molecule morgan_2_4096 --max-steps 30000 --seed 42 --workers 3 \
    --out runs/T01/dreams_morgan_formula_seed1.ckpt                       # 7.75 h on MPS
python -m model_zoo.train embcos   --dataset massspecgym --candidate-map official_candidates_by_mass \
    --split formula_seed1 --workers 3 --no-logger --result-path runs/T02/released-result.json
python -m model_zoo.train deepsets --dataset massspecgym --candidate-map official_candidates_by_mass \
    --split formula_seed1 --workers 3 --no-logger --result-path runs/T03/released-result.json

# frozen pools (347 s)
python $S/build_pools.py --data data/massspecgym --pool4m MassSpecGym_retrieval_molecules_4M.tsv \
    --split formula_seed1 --folds val test --out runs/P01/pools.h5

# scores and rank statistics, per method and fold
python $S/score_pools.py --method msalign --checkpoint runs/T01/dreams_morgan_formula_seed1.ckpt \
    --pools runs/P01/pools.h5 --data data/massspecgym --split formula_seed1 --fold test --out runs/SC03/scores-test.h5
python $S/rank_stats.py --pools runs/P01/pools.h5 --scores runs/SC03/scores-test.h5 --out runs/SC03/ranks-test.csv.gz
#   (same for --method mass | embcos | deepsets, and --fold val)
python $S/fuse_scores.py --pools runs/P01/pools.h5 --model-val ... --mass-val ... --model-test ... --mass-test ... --out-dir runs/SC06

# metrics, grouped bootstrap, contrasts, decline thresholds
python $S/analyse.py --test mass=... msalign=... embcos=... deepsets=... fusion=... \
    --val mass=... msalign=... embcos=... deepsets=... fusion=... \
    --data data/massspecgym --split formula_seed1 --fold test --out runs/AN02/analysis
python $S/make_charts.py --analysis runs/AN02/analysis --precursor runs/A02/precursor-ppm-error.csv.gz --out charts/
```

The released `model_zoo` scripts evaluate their own test fold at the end of training (strict ties, duplicates kept). Those numbers are kept in `released-result.json` and compared with the harness, not substituted for it.

## 4. Checks that must pass

- Harness reproduces the trainer's validation metrics for the selected checkpoint (H02 smoke; SC03 full: 0.3763 / 0.6217 / 0.7863).
- Pool fingerprints equal the released candidate cache (P00: 7,192 of 7,192).
- DreaMS TorchScript equals the released embeddings (V01: minimum cosine 0.9999999).
- CLI scores equal harness scores for the demo spectrum (X02: maximum absolute difference 2.2e-4 with the fp16 bundle).
