"""Exploratory late fusion M5 (protocol section 4): (1 - w) z(model) + w z(mass).

z-scores are computed independently over each evaluated pool. The absent
pool excludes the target before normalization. Version 2 artifacts retain
`scores` for official_dedup compatibility and store each pool in `pool_scores`.
The weight is chosen on validation Recall@5 (expected-tie
rule, `official_dedup`) from w in {0, 0.05, ..., 1}; the chosen w is then
applied once to test.

    python fuse_scores.py --pools pools.h5 --model-val a.h5 --mass-val b.h5 \
        --model-test c.h5 --mass-test d.h5 --out-dir run/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def load(path):
    with h5py.File(path, "r") as h:
        return {k: h[k][:] for k in ("rows", "target_slot", "score_offsets", "scores")}, dict(h.attrs)


POOL_FLAGS = {"official_dedup": 1, "sub16": 2, "sub64": 4, "expanded1024": 8}
POOL_NAMES = ("official_raw", *POOL_FLAGS, "absent")
NORMALIZATION = "per_pool_v2"


def pool_mask(flags, multiplicity, pool):
    if pool == "official_raw":
        return multiplicity > 0
    mask = (flags & POOL_FLAGS.get(pool, 1)) > 0
    if pool == "absent":
        mask[0] = False
    return mask


def fused(pools, model, mass, w, pool="official_dedup"):
    if pool not in POOL_NAMES:
        raise ValueError(f"unknown pool: {pool}")
    offsets, flags = pools["offsets"][:], pools["flags"][:]
    multiplicity = pools["official_multiplicity"][:]
    for key in ("rows", "target_slot", "score_offsets"):
        if not np.array_equal(model[key], mass[key]):
            raise ValueError(f"model/mass {key} mismatch")
    if len(model["scores"]) != len(mass["scores"]):
        raise ValueError("model/mass score lengths differ")
    out = np.full(len(model["scores"]), np.nan, dtype=np.float32)
    for i, j in enumerate(model["target_slot"]):
        a, b = model["score_offsets"][i:i + 2]
        lo, hi = offsets[j:j + 2]
        if b - a != hi - lo:
            raise ValueError("score length does not match pool manifest")
        fl, mu = flags[lo:hi], multiplicity[lo:hi]
        mask = pool_mask(fl, mu, pool)
        if not mask.any() or (pool != "absent" and not mask[0]):
            continue  # unavailable pool variant
        weights = mu[mask] if pool == "official_raw" else np.ones(mask.sum())
        zs = []
        for scores in (model["scores"], mass["scores"]):
            values = scores[a:b][mask].astype(np.float64)
            if not np.isfinite(values).all():
                break  # invalid component marks this pool/spectrum as failed
            mean = np.average(values, weights=weights)
            sd = np.sqrt(np.average((values - mean) ** 2, weights=weights))
            zs.append((values - mean) / (sd if sd > 0 else 1.0))
        if len(zs) == 2:
            out[a:b][mask] = (1 - w) * zs[0] + w * zs[1]
    return out


def recall5_dedup(pools, data, scores):
    offsets, flags = pools["offsets"][:], pools["flags"][:]
    vals = []
    for i, j in enumerate(data["target_slot"]):
        a, b = data["score_offsets"][i], data["score_offsets"][i + 1]
        s = scores[a:b][(flags[offsets[j]:offsets[j + 1]] & 1) > 0]
        if not len(s) or not np.isfinite(s).all():
            vals.append(0.0)
            continue
        bb, tt = (s[1:] > s[0]).sum(), (s[1:] == s[0]).sum()
        vals.append(np.clip((5 - bb) / (tt + 1), 0, 1))
    return float(np.mean(vals))


def write(path, data, scores, attrs, pool_scores=None):
    if path.exists():
        raise SystemExit(f"{path} exists")
    with h5py.File(path, "w") as h:
        for k in ("rows", "target_slot", "score_offsets"):
            h.create_dataset(k, data=data[k])
        h.create_dataset("scores", data=scores, compression="lzf")
        if pool_scores is not None:
            group = h.create_group("pool_scores")
            for name in POOL_NAMES:
                group.create_dataset(name, data=pool_scores[name], compression="lzf")
            h.attrs["fusion_normalization"] = NORMALIZATION
            h.attrs["fusion_schema_version"] = 2
        for k, v in attrs.items():
            h.attrs[k] = v


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("pools", "model-val", "mass-val", "model-test", "mass-test", "out-dir"):
        ap.add_argument(f"--{name}", type=Path, required=True)
    args = ap.parse_args()
    pools = h5py.File(args.pools, "r")
    mv, _ = load(args.model_val)
    sv, _ = load(args.mass_val)
    grid = [round(x, 2) for x in np.arange(0, 1.0001, 0.05)]
    curve = {w: recall5_dedup(pools, mv, fused(pools, mv, sv, w)) for w in grid}
    best = max(grid, key=lambda w: (curve[w], -w))  # ties -> smaller mass weight
    args.out_dir.mkdir(parents=True, exist_ok=True)
    val_scores = {name: fused(pools, mv, sv, best, name) for name in POOL_NAMES}
    write(args.out_dir / "scores-val.h5", mv, val_scores["official_dedup"],
          {"method": "fusion", "fold": "val", "w_mass": best}, val_scores)
    mt, _ = load(args.model_test)
    st, _ = load(args.mass_test)
    test_scores = {name: fused(pools, mt, st, best, name) for name in POOL_NAMES}
    write(args.out_dir / "scores-test.h5", mt, test_scores["official_dedup"],
          {"method": "fusion", "fold": "test", "w_mass": best}, test_scores)
    (args.out_dir / "fusion-weight.json").write_text(json.dumps(
        {"chosen_w_mass": best, "validation_recall5_by_w": curve,
         "fusion_normalization": NORMALIZATION, "fusion_schema_version": 2}, indent=2))
    print(best, curve[best])


if __name__ == "__main__":
    main()
