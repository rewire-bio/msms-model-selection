"""Post hoc descriptive strata (not pre-declared): Recall@5 on the deduplicated
official pools by instrument type and by precursor-precision class.

Precision classes use the mass baseline's own target score, i.e. the absolute
ppm error between the recorded precursor's implied neutral mass and the
annotated structure: < 0.01 ppm (almost certainly recomputed from the
annotation), 0.01-10 ppm, > 10 ppm (outside a 10 ppm window around the
measurement).

    python strata.py --ranks mass=... msalign=... --mass mass-ranks-test.csv.gz \
        --instrument instrument-map.csv --out strata.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msms_shortlist.metrics import grouped_bootstrap, recall_expected, summarise  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranks", nargs="+", required=True)
    ap.add_argument("--mass", type=Path, required=True)
    ap.add_argument("--instrument", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    mass = pd.read_csv(args.mass).query("pool == 'official_dedup'").set_index("row")
    ppm = -mass["target_score"]
    prec = pd.cut(ppm, [-1, 0.01, 10, np.inf], labels=["<0.01 ppm", "0.01-10 ppm", ">10 ppm"])
    inst = pd.read_csv(args.instrument).set_index("row")["instrument_type"].reindex(mass.index).fillna("unmapped")
    groups = mass["target_id"]
    out = []
    for item in args.ranks:
        name, path = item.split("=", 1)
        r = pd.read_csv(path).query("pool == 'official_dedup'").set_index("row").reindex(mass.index)
        hit = recall_expected(r["b"].to_numpy(), r["t"].to_numpy(), 5)
        for kind, labels in (("instrument", inst), ("precursor_precision", prec.astype(str))):
            for level in sorted(labels.unique()):
                mask = (labels == level).to_numpy()
                boots = grouped_bootstrap({"v": hit[mask]}, groups.to_numpy()[mask], 2000, 20261004)
                s = summarise(hit[mask].mean(), boots["v"])
                out.append({"method": name, "stratum": kind, "level": level, "n_spectra": int(mask.sum()),
                            "n_molecules": int(groups[mask].nunique()),
                            **{f"recall5_{k}": 100 * v for k, v in s.items()}})
    df = pd.DataFrame(out)
    df.to_csv(args.out, index=False)
    print(df.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
