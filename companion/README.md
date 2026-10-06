# msms-shortlist: formula-free MS/MS candidate shortlisting

Companion code for the rewire.it article on choosing a formula-free retrieval method for a five-structure shortlist. It has two parts:

1. **Own-input CLI** (`msms_shortlist/`): ranks your candidate structures for your spectra, with metadata checks, a ppm window, duplicate removal, tie flags, an optional decline threshold and a provenance file.
2. **Benchmark scripts** (`scripts/`): the exact pipeline used for the article's measurements on MassSpecGym (formula split seed 1), run against the MSAlign release.

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

See `REPRODUCE.md` for the full command list, data hashes and run receipts.

## Licences

Code: MIT. `msms_shortlist/towers.py` adapts inference code from MSAlign (MIT, Copyright (c) 2026 KrzakalaPaul). Data and weights keep their own licences: MassSpecGym (MIT), the MSAlign Zenodo bundle (CC BY 4.0), DreaMS weights (MIT). No source weights or data are bundled in this archive.
