"""Build the frozen candidate-pool manifest (protocol section 3).

For every target molecule in the requested folds this writes one ordered list
of distinct 2D structures: the target first, then the deduplicated official
decoys, then extra decoys from the MassSpecGym 4M set. Membership flags,
official multiplicities, monoisotopic masses and packed Morgan fingerprints
are stored alongside, so every scorer reads identical pools.

Usage (from anywhere)::

    python build_pools.py --data /path/to/msalign-data/massspecgym \
        --pool4m /path/to/MassSpecGym_retrieval_molecules_4M.tsv \
        --split formula_seed1 --folds val test --out /path/to/run/pools.h5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msms_shortlist.chem import canonical_2d, exact_mass, inchikey_block1, morgan_packed  # noqa: E402

FLAG_DEDUP, FLAG_SUB16, FLAG_SUB64, FLAG_EXP1024 = 1, 2, 4, 8
PPM_WINDOW = 10.0
EXPANDED_SIZE = 1024


def seeded_rng(smiles: str, purpose: str) -> np.random.Generator:
    digest = hashlib.sha256(f"{smiles}|{purpose}".encode()).hexdigest()
    return np.random.default_rng(int(digest[:16], 16))


def _parse_4m(row):
    smiles, ik = row
    canon = canonical_2d(smiles)
    if canon is None:
        return None
    try:
        mass = exact_mass(canon)
    except ValueError:
        return None
    return canon, mass, ik


def load_4m(path: Path, workers: int) -> pd.DataFrame:
    table = pd.read_csv(path, sep="\t")
    rows = list(zip(table["smiles"], table["inchikey"]))
    with mp.Pool(workers) as pool:
        parsed = pool.map(_parse_4m, rows, chunksize=4096)
    kept = [p for p in parsed if p is not None]
    frame = pd.DataFrame(kept, columns=["smiles", "mass", "ik14"])
    frame = frame.drop_duplicates("smiles").sort_values("mass").reset_index(drop=True)
    frame.attrs["n_input"] = len(rows)
    frame.attrs["n_invalid"] = len(rows) - len(kept)
    return frame


def _fp_and_mass(smiles):
    return morgan_packed(smiles), exact_mass(smiles)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--pool4m", type=Path)
    ap.add_argument("--split", required=True)
    ap.add_argument("--folds", nargs="+", default=["val", "test"])
    ap.add_argument("--no-expanded", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    t0 = time.time()
    timings = {}

    meta = pd.read_csv(args.data / "metadata.csv")
    uniq = pd.read_csv(args.data / "unique_smiles.csv")["smiles"].tolist()
    folds = pd.read_csv(args.data / "splits" / f"{args.split}.csv")["fold"].to_numpy()
    cmap = json.loads((args.data / "candidates/official_candidates_by_mass/map.json").read_text())
    target_ids = sorted(set(meta.loc[np.isin(folds, args.folds), "unique_smiles_idx"]))
    print(f"{len(target_ids)} target molecules in folds {args.folds}", flush=True)

    pool4m = None
    if not args.no_expanded:
        t = time.time()
        pool4m = load_4m(args.pool4m, args.workers)
        timings["load_4m_seconds"] = time.time() - t
        masses4m = pool4m["mass"].to_numpy()
        print(f"4M set: {len(pool4m)} distinct valid structures "
              f"({pool4m.attrs['n_invalid']} unparsable) in {timings['load_4m_seconds']:.0f}s", flush=True)

    t = time.time()
    records, all_smiles, offsets = [], [], [0]
    flags_all, mult_all = [], []
    for tid in target_ids:
        target = uniq[tid]
        raw = cmap[target]
        assert raw[0] == target
        mult = Counter(raw)
        dedup = list(dict.fromkeys(raw))
        decoys = dedup[1:]
        flags = [FLAG_DEDUP] * len(dedup)
        for size, flag in ((16, FLAG_SUB16), (64, FLAG_SUB64)):
            flags[0] |= flag
            pick = seeded_rng(target, f"sub{size}").choice(
                len(decoys), size=min(size - 1, len(decoys)), replace=False)
            for i in pick:
                flags[1 + i] |= flag
        extras = []
        n_window = 0
        if pool4m is not None:
            for i in range(len(flags)):
                flags[i] |= FLAG_EXP1024
            m = exact_mass(target)
            tol = m * PPM_WINDOW * 1e-6
            lo, hi = np.searchsorted(masses4m, [m - tol, m + tol], side="left")
            window = pool4m.iloc[lo:hi]
            window = window[np.abs(window["mass"].to_numpy() - m) < tol]
            ik_target = inchikey_block1(target)
            present = set(dedup)
            window = window[(window["ik14"] != ik_target) & ~window["smiles"].isin(present)]
            n_window = len(window)
            need = max(0, EXPANDED_SIZE - len(dedup))
            if need and n_window:
                pick = seeded_rng(target, "expanded1024").choice(
                    n_window, size=min(need, n_window), replace=False)
                extras = window["smiles"].to_numpy()[np.sort(pick)].tolist()
        members = dedup + extras
        flags += [FLAG_EXP1024] * len(extras)
        all_smiles += members
        flags_all += flags
        mult_all += [mult.get(s, 0) for s in members]
        offsets.append(len(all_smiles))
        records.append({"target_id": tid, "target_smiles": target, "n_raw": len(raw),
                        "n_dedup": len(dedup), "n_extra": len(extras),
                        "n_window_4m_eligible": n_window})
    timings["manifest_seconds"] = time.time() - t
    print(f"manifest: {len(all_smiles)} entries in {timings['manifest_seconds']:.0f}s", flush=True)

    t = time.time()
    with mp.Pool(args.workers) as pool:
        out = pool.map(_fp_and_mass, all_smiles, chunksize=2048)
    fps = np.stack([o[0] for o in out])
    masses = np.array([o[1] for o in out])
    timings["fingerprint_mass_seconds"] = time.time() - t

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.out, "w") as h:
        h.create_dataset("smiles", data=np.array(all_smiles, dtype=object),
                         dtype=h5py.string_dtype(), compression="lzf")
        h.create_dataset("offsets", data=np.array(offsets, dtype=np.int64))
        h.create_dataset("target_ids", data=np.array(target_ids, dtype=np.int64))
        h.create_dataset("flags", data=np.array(flags_all, dtype=np.uint8), compression="lzf")
        h.create_dataset("official_multiplicity", data=np.array(mult_all, dtype=np.int16), compression="lzf")
        h.create_dataset("mass", data=masses, compression="lzf")
        h.create_dataset("fingerprints", data=fps, compression="lzf", chunks=(4096, 512))
        h.attrs["split"] = args.split
        h.attrs["folds"] = json.dumps(args.folds)
        h.attrs["flags"] = json.dumps({"official_dedup": FLAG_DEDUP, "sub16": FLAG_SUB16,
                                       "sub64": FLAG_SUB64, "expanded1024": FLAG_EXP1024})
    pd.DataFrame(records).to_csv(args.out.with_suffix(".targets.csv"), index=False)
    timings["total_seconds"] = time.time() - t0
    receipt = {"args": {k: str(v) for k, v in vars(args).items()}, "timings": timings,
               "n_targets": len(target_ids), "n_entries": len(all_smiles),
               "pool4m_rows": None if pool4m is None else int(pool4m.attrs["n_input"]),
               "pool4m_distinct_valid": None if pool4m is None else int(len(pool4m))}
    args.out.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt["timings"]))


if __name__ == "__main__":
    main()
