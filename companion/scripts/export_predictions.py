"""Export readable test-fold predictions: the five best structures per spectrum and method.

One CSV per method with, for every test spectrum on the deduplicated official
pool: processed row, MassSpecGym identifier (when uniquely recovered), adduct,
precursor m/z, annotated 2D SMILES, rank statistics, the five top-ranked 2D
SMILES with scores, and whether the annotated structure is among them under
random tie-breaking (expected value).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--instrument", type=Path, required=True)
    ap.add_argument("--scores", nargs="+", required=True, help="method=scores-test.h5")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    P = h5py.File(args.pools, "r")
    offsets, flags = P["offsets"][:], P["flags"][:]
    smiles = P["smiles"]
    meta = pd.read_csv(args.data / "metadata.csv")
    inst = pd.read_csv(args.instrument).set_index("row")
    for item in args.scores:
        name, path = item.split("=", 1)
        S = h5py.File(path, "r")
        rows, slots, soff, scores = S["rows"][:], S["target_slot"][:], S["score_offsets"][:], S["scores"][:]
        recs = []
        for i, (row, j) in enumerate(zip(rows, slots)):
            lo, hi = offsets[j], offsets[j + 1]
            sc = scores[soff[i]:soff[i + 1]]
            keep = np.flatnonzero((flags[lo:hi] & 1) > 0)
            s = sc[keep]
            order = keep[np.argsort(-s, kind="stable")[:5]]
            b, t = (s[1:] > s[0]).sum(), (s[1:] == s[0]).sum()
            rec = {"row": int(row), "massspecgym_identifier": inst["identifier"].get(int(row)),
                   "instrument_type": inst["instrument_type"].get(int(row)),
                   "adduct": meta.at[int(row), "adduct"], "precursor_mz": meta.at[int(row), "precursor_mz"],
                   "annotated_smiles_2d": smiles[lo].decode(), "pool_size": int(len(keep)),
                   "n_scoring_above": int(b), "n_tied": int(t), "target_score": float(s[0]),
                   "in_top5_expected": float(np.clip((5 - b) / (t + 1), 0, 1))}
            for k, idx in enumerate(order, 1):
                rec[f"top{k}_smiles_2d"] = smiles[lo + idx].decode()
                rec[f"top{k}_score"] = float(sc[idx])
            recs.append(rec)
        pd.DataFrame(recs).to_csv(args.out / f"predictions-test-{name}.csv.gz", index=False)
        print(name, len(recs))


if __name__ == "__main__":
    main()
