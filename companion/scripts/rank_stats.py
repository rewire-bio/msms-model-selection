"""Turn saved scores into per-spectrum rank statistics for every pool variant.

For each spectrum and pool the output row holds: pool size (distinct structures,
and weighted size for `official_raw`), b and t (decoys scoring above / tied with
the target), the target score, the top-1 and top-2 scores in the pool and the
manifest indices of the five best structures. The `absent` pool is the deduplicated
official pool without the target; for it, only top-1/top-2 scores are defined.

    python rank_stats.py --pools pools.h5 --scores scores-test.h5 --out ranks-test.csv.gz
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

FLAGS = {"official_dedup": 1, "sub16": 2, "sub64": 4, "expanded1024": 8}


def stats(scores, weights):
    """b, t, target score, top-1, top-2 and top-5 manifest positions."""
    target = scores[0]
    dec = scores[1:]
    w = weights[1:]
    b = float(w[dec > target].sum())
    t = float(w[dec == target].sum())
    order = np.argsort(-scores, kind="stable")
    top = scores[order[:2]]
    return b, t, float(target), float(top[0]), float(top[1]) if len(top) > 1 else np.nan, order[:5]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pools", type=Path, required=True)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--allow-legacy-fusion", action="store_true",
                    help="Explicitly reproduce historical post-scoring deletion; not target-absent fusion")
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    t0 = time.time()
    P = h5py.File(args.pools, "r")
    S = h5py.File(args.scores, "r")
    offsets, flags_all = P["offsets"][:], P["flags"][:]
    mult_all = P["official_multiplicity"][:].astype(float)
    target_ids = P["target_ids"][:]
    rows, slots, soff = S["rows"][:], S["target_slot"][:], S["score_offsets"][:]
    scores_all = S["scores"][:]
    is_fusion = S.attrs.get("method") == "fusion"
    normalization = "not_applicable"
    pool_scores = None
    if is_fusion:
        if S.attrs.get("fusion_normalization") == "per_pool_v2" and S.attrs.get("fusion_schema_version") == 2:
            names = ("official_raw", *FLAGS, "absent")
            if "pool_scores" not in S or any(name not in S["pool_scores"] for name in names):
                raise SystemExit("Incomplete per-pool fusion artifact; regenerate fusion scores")
            pool_scores = {name: S["pool_scores"][name][:] for name in names}
            if any(len(values) != len(scores_all) for values in pool_scores.values()):
                raise SystemExit("Invalid per-pool fusion score lengths")
            normalization = "per_pool_v2"
        elif args.allow_legacy_fusion and "fusion_schema_version" not in S.attrs and "pool_scores" not in S:
            normalization = "legacy_post_scoring_deletion"
        else:
            raise SystemExit("Fusion scores lack supported per-pool normalization. Regenerate with fuse_scores.py, "
                             "or use --allow-legacy-fusion only to reproduce historical post-scoring deletion.")
    records = []
    for i, (row, j) in enumerate(zip(rows, slots)):
        sc = scores_all[soff[i]:soff[i + 1]]
        lo, hi = offsets[j], offsets[j + 1]
        assert len(sc) == hi - lo
        fl, mu = flags_all[lo:hi], mult_all[lo:hi]
        variants = {"official_raw": (mu > 0, mu)}
        for name, bit in FLAGS.items():
            m = (fl & bit) > 0
            variants[name] = (m, np.ones(hi - lo))
        for name, (mask, weight) in variants.items():
            if not mask[0]:  # pool variant not built in this manifest
                continue
            idx = np.flatnonzero(mask)
            variant_sc = sc if pool_scores is None else pool_scores[name][soff[i]:soff[i + 1]]
            if not np.isfinite(variant_sc[idx]).all():
                continue  # failure remains a miss when analysis reindexes the fold
            b, t, ts, t1, t2, top5 = stats(variant_sc[idx], weight[idx])
            records.append({"row": int(row), "target_id": int(target_ids[j]), "pool": name,
                            "n_pool": int(len(idx)), "n_pool_weighted": float(weight[idx].sum()),
                            "b": b, "t": t, "target_score": ts, "top1": t1, "top2": t2,
                            "top5": ";".join(str(int(idx[k])) for k in top5)})
        dmask = (fl & FLAGS["official_dedup"]) > 0
        dmask[0] = False
        idx = np.flatnonzero(dmask)
        absent_sc = sc if pool_scores is None else pool_scores["absent"][soff[i]:soff[i + 1]]
        if len(idx) and not np.isfinite(absent_sc[idx]).all():
            continue
        ordered = np.sort(absent_sc[idx])[::-1]
        records.append({"row": int(row), "target_id": int(target_ids[j]), "pool": "absent",
                        "n_pool": int(len(idx)), "n_pool_weighted": float(len(idx)),
                        "b": np.nan, "t": np.nan, "target_score": np.nan,
                        "top1": float(ordered[0]) if len(ordered) else np.nan, "top2": float(ordered[1]) if len(ordered) > 1 else np.nan,
                        "top5": ";".join(str(int(idx[k])) for k in np.argsort(-absent_sc[idx], kind="stable")[:5])})
    df = pd.DataFrame(records, columns=["row", "target_id", "pool", "n_pool", "n_pool_weighted",
                                       "b", "t", "target_score", "top1", "top2", "top5"])
    if is_fusion:
        df["fusion_normalization"] = normalization
    df.attrs = {}
    df.to_csv(args.out, index=False)
    meta = {"method": S.attrs["method"], "fold": S.attrs["fold"], "n_spectra": int(len(rows)),
            "seconds": time.time() - t0, "fusion_normalization": normalization}
    args.out.with_name(args.out.name.replace(".csv.gz", "") + ".receipt.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
