"""Recover MassSpecGym identifier and instrument type for processed rows.

The MSAlign Zenodo metadata is reordered relative to MassSpecGym.tsv and drops
the instrument column. A processed row is matched to a TSV record when the 2D
structure, adduct and precursor m/z (within 1e-3) agree and the ten strongest
peaks agree to 0.01 m/z. The identifier is kept only for a unique match; the instrument type is kept
when every matching record agrees. Several matches mean near-duplicate records
(same structure, adduct, precursor and ten strongest peaks).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msms_shortlist.chem import canonical_2d  # noqa: E402


def key10(mz, it):
    return frozenset(np.rint(np.asarray(mz, np.float64)[np.argsort(it)[::-1][:10]] * 100).astype(int))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--folds", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    t0 = time.time()
    meta = pd.read_csv(args.data / "metadata.csv")
    folds = pd.read_csv(args.data / "splits" / f"{args.split}.csv")["fold"].to_numpy()
    spectra = np.load(args.data / "spectra.npy", mmap_mode="r")
    rows = np.flatnonzero(np.isin(folds, args.folds))
    wanted = set(meta.loc[rows, "smiles"])
    tsv = pd.read_csv(args.tsv, sep="\t", usecols=["identifier", "smiles", "precursor_mz", "adduct",
                                                     "mzs", "intensities", "instrument_type"])
    tsv["s2"] = tsv["smiles"].map({s: canonical_2d(s) for s in tsv["smiles"].unique()})
    tsv = tsv[tsv["s2"].isin(wanted)]
    index = {}
    for r in tsv.itertuples():
        mz = np.array(r.mzs.split(","), float)
        it = np.array(r.intensities.split(","), float)
        index.setdefault((r.s2, r.adduct), []).append((r.precursor_mz, key10(mz, it), r.identifier, r.instrument_type))
    out = []
    for row in rows:
        m = meta.loc[row]
        sp = np.asarray(spectra[row])
        sp = sp[sp[:, 1] > 0]
        k = key10(sp[:, 0], sp[:, 1])
        hits = [h for h in index.get((m["smiles"], m["adduct"]), [])
                if abs(h[0] - m["precursor_mz"]) < 1e-3 and h[1] == k]
        out.append({"row": int(row), "fold": folds[row], "n_matches": len(hits),
                    "identifier": hits[0][2] if len(hits) == 1 else None,
                    "instrument_type": (hits[0][3] if hits and len({h[3] for h in hits}) == 1 else None),
                    "n_distinct_identifiers_same_top10": len({h[2] for h in hits})})
    df = pd.DataFrame(out)
    df.to_csv(args.out, index=False)
    print(df["n_matches"].value_counts().to_dict(), df["instrument_type"].value_counts(dropna=False).to_dict(),
          f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
