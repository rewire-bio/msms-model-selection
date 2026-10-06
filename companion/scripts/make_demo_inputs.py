"""Write the real-spectrum demonstration inputs (protocol section 10).

Fixed selection rule, applied before any score of these spectra is viewed:
the first formula_seed1 test-fold spectrum (metadata order) with adduct [M+H]+,
and the first with [M+Na]+. Each gets an MGF block and a candidate CSV holding
its deduplicated official mass-candidate pool. A third, target-absent case
reuses the [M+H]+ spectrum with the true structure removed from its candidate
file. Peaks are the released top-100 peaks; the MassSpecGym identifier is
recovered from the MassSpecGym TSV by matching structure, adduct, precursor
m/z and peaks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msms_shortlist.chem import canonical_2d  # noqa: E402


def find_identifier(tsv: pd.DataFrame, smiles2d: str, adduct: str, prec: float, peaks: np.ndarray):
    cand = tsv[(tsv["adduct"] == adduct) & np.isclose(tsv["precursor_mz"], prec, atol=1e-3)]
    cand = cand[cand["smiles"] == smiles2d]
    valid = peaks[peaks[:, 1] > 0]
    top = set(np.rint(valid[np.argsort(valid[:, 1])[::-1][:10], 0].astype(np.float64) * 100).astype(int))
    hits = []
    for _, r in cand.iterrows():
        mz = np.array(r["mzs"].split(","), float)
        it = np.array(r["intensities"].split(","), float)
        best = set(np.rint(mz[np.argsort(it)[::-1][:10]] * 100).astype(int))
        if best == top:  # ten strongest peaks agree to 0.01 m/z
            hits.append(r)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    meta = pd.read_csv(args.data / "metadata.csv")
    folds = pd.read_csv(args.data / "splits/formula_seed1.csv")["fold"].to_numpy()
    spectra = np.load(args.data / "spectra.npy", mmap_mode="r")
    cmap = json.loads((args.data / "candidates/official_candidates_by_mass/map.json").read_text())
    tsv = pd.read_csv(args.tsv, sep="\t")
    tsv["smiles"] = tsv["smiles"].map({x: canonical_2d(x) for x in tsv["smiles"].unique()})
    test = meta[folds == "test"]
    chosen = {"mh": test[test.adduct == "[M+H]+"].index[0], "mna": test[test.adduct == "[M+Na]+"].index[0]}
    record = {}
    for key, row in chosen.items():
        m = meta.loc[row]
        peaks = np.asarray(spectra[row])
        hits = find_identifier(tsv, m["smiles"], m["adduct"], m["precursor_mz"], peaks)
        ident = hits[0]["identifier"] if len(hits) == 1 else None
        instrument = hits[0]["instrument_type"] if len(hits) == 1 else None
        title = ident or f"massspecgym_row_{row}"
        lines = ["BEGIN IONS", f"TITLE={title}", f"PEPMASS={m['precursor_mz']}", "CHARGE=1+",
                 f"ADDUCT={m['adduct']}", f"COLLISION_ENERGY={m['collision_energy']}"]
        lines += [f"{mz:.5f} {it:.6f}" for mz, it in peaks if it > 0]
        lines.append("END IONS")
        (args.out / f"{key}.mgf").write_text("\n".join(lines) + "\n")
        pool = list(dict.fromkeys(cmap[m["smiles"]]))
        ids = [f"cand{i:03d}" for i in range(len(pool))]
        # shuffle row order so the true structure is not visibly first in the file
        order = np.random.default_rng(7).permutation(len(pool))
        frame = pd.DataFrame({"id": np.array(ids)[order], "smiles": np.array(pool)[order]})
        frame.to_csv(args.out / f"{key}-candidates.csv", index=False)
        record[key] = {"metadata_row": int(row), "massspecgym_identifier": ident,
                       "identifier_matches": len(hits), "instrument_type": instrument,
                       "adduct": m["adduct"], "precursor_mz": float(m["precursor_mz"]),
                       "collision_energy": m["collision_energy"], "n_candidates": len(pool),
                       "true_structure_id": ids[0], "true_smiles_2d": m["smiles"]}
        if key == "mh":
            absent = frame[frame["id"] != ids[0]]
            absent.to_csv(args.out / "mh-candidates-target-removed.csv", index=False)
            record["absent"] = {"based_on": "mh", "n_candidates": int(len(absent)),
                                "note": "true structure removed: a controlled stress test, not natural absence"}
    (args.out / "demo-inputs.json").write_text(json.dumps(record, indent=2, default=str))
    print(json.dumps(record, indent=2, default=str))


if __name__ == "__main__":
    main()
