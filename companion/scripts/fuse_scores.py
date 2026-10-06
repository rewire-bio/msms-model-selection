"""Exploratory late fusion M5 (protocol section 4): (1 - w) z(model) + w z(mass).

z-scores are computed per spectrum over the members of its `official_dedup`
pool and applied to every manifest entry, so the fused ranking is defined for
all pool variants. The weight is chosen on validation Recall@5 (expected-tie
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


def fused(pools, model, mass, w):
    offsets, flags = pools["offsets"][:], pools["flags"][:]
    assert np.array_equal(model["rows"], mass["rows"])
    out = np.empty_like(model["scores"])
    for i, j in enumerate(model["target_slot"]):
        a, b = model["score_offsets"][i], model["score_offsets"][i + 1]
        d = (flags[offsets[j]:offsets[j + 1]] & 1) > 0
        zs = []
        for s in (model["scores"][a:b].astype(np.float64), mass["scores"][a:b].astype(np.float64)):
            mu, sd = s[d].mean(), s[d].std()
            zs.append((s - mu) / (sd if sd > 0 else 1.0))
        out[a:b] = ((1 - w) * zs[0] + w * zs[1]).astype(np.float32)
    return out


def recall5_dedup(pools, data, scores):
    offsets, flags = pools["offsets"][:], pools["flags"][:]
    vals = []
    for i, j in enumerate(data["target_slot"]):
        a, b = data["score_offsets"][i], data["score_offsets"][i + 1]
        s = scores[a:b][(flags[offsets[j]:offsets[j + 1]] & 1) > 0]
        bb, tt = (s[1:] > s[0]).sum(), (s[1:] == s[0]).sum()
        vals.append(np.clip((5 - bb) / (tt + 1), 0, 1))
    return float(np.mean(vals))


def write(path, data, scores, attrs):
    if path.exists():
        raise SystemExit(f"{path} exists")
    with h5py.File(path, "w") as h:
        for k in ("rows", "target_slot", "score_offsets"):
            h.create_dataset(k, data=data[k])
        h.create_dataset("scores", data=scores, compression="lzf")
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
    write(args.out_dir / "scores-val.h5", mv, fused(pools, mv, sv, best),
          {"method": "fusion", "fold": "val", "w_mass": best})
    mt, _ = load(args.model_test)
    st, _ = load(args.mass_test)
    write(args.out_dir / "scores-test.h5", mt, fused(pools, mt, st, best),
          {"method": "fusion", "fold": "test", "w_mass": best})
    (args.out_dir / "fusion-weight.json").write_text(json.dumps(
        {"chosen_w_mass": best, "validation_recall5_by_w": curve}, indent=2))
    print(best, curve[best])


if __name__ == "__main__":
    main()
