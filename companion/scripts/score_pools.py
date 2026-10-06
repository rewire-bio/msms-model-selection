"""Score every spectrum of a fold against its frozen pool manifest.

Writes one HDF5 file holding, for each spectrum, the score of every structure in
its target's manifest (target first). All pool variants of protocol section 3
are subsets of the manifest, so metrics for every pool are computed later from
these saved scores without re-running any model.

Run from the MSAlign source checkout (so `models` and `model_zoo` import)::

    python score_pools.py --method msalign --checkpoint run/model.ckpt \
        --pools pools.h5 --data data/massspecgym --split formula_seed1 \
        --fold test --out run/scores-test.h5

Methods: mass, msalign, deepsets, embcos. Random ordering needs no scores.
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import yaml

sys.path.insert(0, str(Path.cwd()))
COMPANION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMPANION))


def adduct_shift(adduct: str) -> float:
    from models.MSAlign_fusion.data import adduct_mass  # released offsets
    return adduct_mass(adduct)


class Mass:
    name = "mass"

    def __init__(self, meta):
        shifts = {a: adduct_shift(a) for a in meta["adduct"].dropna().unique()}
        self.est = meta["precursor_mz"].to_numpy(float) - meta["adduct"].map(shifts).to_numpy(float)

    def score(self, rows, fps, masses):
        masses = np.round(masses, 6)
        ppm = 1e6 * np.abs(self.est[rows][:, None] - masses[None, :]) / masses[None, :]
        return -np.round(ppm, 6)


class MSAlignScorer:
    name = "msalign"

    def __init__(self, checkpoint, meta, data, device):
        from models.MSAlign.encoders import normalize_adduct
        from models.MSAlign_fusion.scorer import load_msalign_checkpoint
        params = {"labelled_dataset_name": "massspecgym",
                  "candidate_map_name": "official_candidates_by_mass", "split_method": "x"}
        self.model, self.config, _ = load_msalign_checkpoint(checkpoint, params, device)
        self.device = torch.device(device)
        dims = self.model.hparams["input_dimensions"]
        vocab = list(dims["adduct_vocabulary"])  # stored by the released datamodule
        assert len(vocab) == int(dims["unknown_adduct_index"]), dims
        lookup = {v: i for i, v in enumerate(vocab)}
        self.adduct = np.array([lookup.get(normalize_adduct(a), int(dims["unknown_adduct_index"]))
                                for a in meta["adduct"]], dtype=np.int64)
        self.energy = pd.to_numeric(meta["collision_energy"], errors="coerce").to_numpy(np.float32)
        rep = self.config["representations"]
        assert rep["molecule"] == "morgan_2_4096" and rep["spectrum"] == "dreams", rep
        self.spectra = np.load(data / "spectra_embeddings" / "dreams.npy", mmap_mode="r")

    @torch.inference_mode()
    def score(self, rows, fps, masses):
        from msms_shortlist.chem import unpack
        spec = torch.from_numpy(np.asarray(self.spectra[rows], dtype=np.float32)).to(self.device)
        md = {"collision_energy": torch.from_numpy(self.energy[rows]).to(self.device),
              "adduct": torch.from_numpy(self.adduct[rows]).to(self.device)}
        s = F.normalize(self.model.encode_spectrum(spec, md), dim=-1)
        mol = torch.from_numpy(unpack(fps).astype(np.float32)).to(self.device)
        m = F.normalize(self.model.encode_molecule(mol), dim=-1)
        return (s @ m.T).float().cpu().numpy()


class DeepSetsScorer:
    name = "deepsets"

    def __init__(self, checkpoint, meta, data, device):
        from model_zoo.DeepSets.model import DeepSet
        cfg = yaml.safe_load(Path("model_zoo/DeepSets/configs/default.yaml").read_text())
        self.model = DeepSet(cfg)
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
        self.model.load_state_dict(state, strict=True)
        self.device = torch.device(device)
        self.model.eval().to(self.device)
        self.opts = {k: cfg["spectrum"][k] for k in ("n_peaks", "mz_min", "mz_max", "precursor_intensity")}
        self.spectra = np.load(data / "spectra.npy", mmap_mode="r")
        self.prec = pd.to_numeric(meta["precursor_mz"], errors="coerce").to_numpy(np.float32)

    @torch.inference_mode()
    def score(self, rows, fps, masses):
        from model_zoo.DeepSets.datamodule import tokenize_peaks
        from msms_shortlist.chem import unpack
        tok = np.stack([tokenize_peaks(self.spectra[r], self.prec[r], **self.opts) for r in rows])
        pred = self.model(torch.from_numpy(tok).to(self.device))
        cand = torch.from_numpy(unpack(fps).astype(np.float32)).to(self.device)
        return (F.normalize(pred, dim=-1) @ F.normalize(cand, dim=-1).T).float().cpu().numpy()


class EmbCosScorer:
    name = "embcos"

    def __init__(self, checkpoint, meta, data, device):
        from model_zoo.EmbCos.model import EmbCos
        from transforms.spectra_transforms import BIN_Transform
        cfg = yaml.safe_load(Path("model_zoo/EmbCos/configs/default.yaml").read_text())
        self.model = EmbCos(cfg)
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)["state_dict"]
        self.model.load_state_dict(state, strict=True)
        self.device = torch.device(device)
        self.model.eval().to(self.device)
        self.bins = BIN_Transform(max_mz=cfg["max_mz"], bin_width=cfg["bin_width"])
        self.spectra = np.load(data / "spectra.npy", mmap_mode="r")

    @torch.inference_mode()
    def score(self, rows, fps, masses):
        from msms_shortlist.chem import unpack
        ms = torch.from_numpy(np.stack([self.bins(np.asarray(self.spectra[r])) for r in rows])
                              .astype(np.float32)).to(self.device)
        cand = torch.from_numpy(unpack(fps).astype(np.float32)).to(self.device)
        return (self.model.encode_ms(ms) @ self.model.encode_mol(cand).T).float().cpu().numpy()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--method", required=True, choices=("mass", "msalign", "deepsets", "embcos"))
    ap.add_argument("--checkpoint", type=Path)
    ap.add_argument("--pools", type=Path, required=True)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--fold", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--limit-targets", type=int, help="smoke runs only")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; score files are immutable")
    torch.set_num_threads(4)
    t0 = time.time()

    meta = pd.read_csv(args.data / "metadata.csv")
    folds = pd.read_csv(args.data / "splits" / f"{args.split}.csv")["fold"].to_numpy()
    if args.method == "mass":
        scorer = Mass(meta)
    else:
        cls = {"msalign": MSAlignScorer, "deepsets": DeepSetsScorer, "embcos": EmbCosScorer}[args.method]
        scorer = cls(args.checkpoint, meta, args.data, args.device)
    t_load = time.time() - t0

    pools = h5py.File(args.pools, "r")
    offsets = pools["offsets"][:]
    target_ids = pools["target_ids"][:]
    fps_all, mass_all = pools["fingerprints"], pools["mass"][:]
    fold_rows = np.flatnonzero(folds == args.fold)
    row_target = meta["unique_smiles_idx"].to_numpy()
    by_target = pd.Series(fold_rows).groupby(row_target[fold_rows]).apply(list).to_dict()
    order = [j for j, t in enumerate(target_ids) if t in by_target]
    if args.limit_targets:
        order = order[: args.limit_targets]

    out_rows, out_target_slot, score_chunks, score_offsets = [], [], [], [0]
    failures = []
    t_score = time.time()
    for j in order:
        rows = np.array(by_target[target_ids[j]])
        lo, hi = offsets[j], offsets[j + 1]
        try:
            s = scorer.score(rows, fps_all[lo:hi], mass_all[lo:hi])
            if not np.all(np.isfinite(s)):
                raise ValueError("non-finite score")
        except Exception as exc:  # recorded, counted as a miss downstream
            failures.append({"target_slot": int(j), "rows": rows.tolist(), "error": repr(exc)})
            continue
        for r, srow in zip(rows, s):
            out_rows.append(int(r))
            out_target_slot.append(int(j))
            score_chunks.append(srow.astype(np.float32))
            score_offsets.append(score_offsets[-1] + len(srow))
    t_score = time.time() - t_score

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.out, "w") as h:
        h.create_dataset("rows", data=np.array(out_rows, dtype=np.int64))
        h.create_dataset("target_slot", data=np.array(out_target_slot, dtype=np.int64))
        h.create_dataset("score_offsets", data=np.array(score_offsets, dtype=np.int64))
        h.create_dataset("scores", data=np.concatenate(score_chunks) if score_chunks else np.zeros(0, np.float32),
                         compression="lzf")
        h.attrs["method"] = args.method
        h.attrs["checkpoint"] = str(args.checkpoint)
        h.attrs["pools"] = str(args.pools)
        h.attrs["fold"] = args.fold
        h.attrs["split"] = args.split
    receipt = {
        "method": args.method, "checkpoint": str(args.checkpoint), "pools": str(args.pools),
        "split": args.split, "fold": args.fold, "device": args.device,
        "n_spectra_in_fold": int(len(fold_rows)), "n_spectra_scored": len(out_rows),
        "n_failures_targets": len(failures), "failures": failures[:50],
        "seconds_load": t_load, "seconds_scoring": t_score, "seconds_total": time.time() - t0,
        "peak_rss_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "torch": torch.__version__, "python": platform.python_version(),
        "limit_targets": args.limit_targets,
    }
    args.out.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps({k: receipt[k] for k in ("n_spectra_scored", "n_failures_targets", "seconds_total")}))


if __name__ == "__main__":
    main()
