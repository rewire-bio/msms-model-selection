"""Rank a reader's candidate structures for one or more MS/MS spectra.

    python -m msms_shortlist.cli --spectra query.mgf --candidates candidates.csv \
        --out ranked.csv [--model dreams_morgan.pt --dreams DreaMS_embedding_model_torchscript.pt \
        --thresholds thresholds.json] [--ppm 10] [--shortlist 5]

Spectra: MGF with PEPMASS (precursor m/z), CHARGE and ADDUCT per block; an
optional COLLISION_ENERGY is passed to the model. Candidates: CSV with columns
`id` and `smiles` (any extra columns are carried through as provenance).

Without --model the ranking is by precursor mass error alone. With --model the
ranking is by the trained DreaMS + Morgan alignment model; mass error is still
reported. The output is a shortlist for confirmation, never an identification,
and the score is not a probability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .chem import ADDUCTS, canonical_2d, exact_mass, morgan_packed, neutral_mass, ppm_error, unpack

N_PEAKS = 100
PRECURSOR_INTENSITY = 1.1


def sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_mgf(path: Path) -> list[dict]:
    spectra, cur = [], None
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "BEGIN IONS":
            cur = {"params": {}, "peaks": []}
        elif line == "END IONS":
            spectra.append(cur)
            cur = None
        elif cur is not None:
            if "=" in line and not line[0].isdigit():
                key, value = line.split("=", 1)
                cur["params"][key.strip().upper()] = value.strip()
            else:
                parts = line.split()
                cur["peaks"].append((float(parts[0]), float(parts[1])))
    return spectra


def parse_charge(text: str | None) -> int | None:
    if text is None or text == "":
        return None
    text = text.strip()
    sign = -1 if text.endswith("-") else 1
    return sign * int(text.rstrip("+-"))


def validate(params: dict) -> tuple[dict | None, str | None]:
    """Return (metadata, None) or (None, reason) when the spectrum must not be ranked."""
    try:
        prec = float(params.get("PEPMASS", "").split()[0])
    except (ValueError, IndexError):
        return None, "missing or unreadable PEPMASS (precursor m/z)"
    adduct = params.get("ADDUCT")
    if not adduct:
        return None, "missing ADDUCT; the neutral mass cannot be derived"
    if adduct not in ADDUCTS:
        return None, f"unsupported adduct {adduct}"
    charge = parse_charge(params.get("CHARGE"))
    if charge is None:
        return None, "missing CHARGE"
    try:
        mass = neutral_mass(prec, adduct, charge)
    except ValueError as exc:
        return None, str(exc)
    energy = params.get("COLLISION_ENERGY")
    return {"precursor_mz": prec, "adduct": adduct, "charge": charge, "neutral_mass": mass,
            "collision_energy": float(energy) if energy not in (None, "") else float("nan")}, None


def prepare_candidates(path: Path) -> tuple[pd.DataFrame, dict]:
    table = pd.read_csv(path)
    if not {"id", "smiles"} <= set(table.columns):
        raise SystemExit("candidate file needs columns 'id' and 'smiles'")
    table["smiles_2d"] = [canonical_2d(str(s)) for s in table["smiles"]]
    invalid = table[table["smiles_2d"].isna()]
    table = table.dropna(subset=["smiles_2d"]).copy()
    merged = table.groupby("smiles_2d")["id"].apply(lambda ids: ";".join(map(str, ids)))
    table = table.drop_duplicates("smiles_2d").copy()
    table["merged_ids"] = table["smiles_2d"].map(merged)
    table["exact_mass"] = [exact_mass(s) for s in table["smiles_2d"]]
    report = {"n_input": int(len(table) + len(invalid) + (merged.str.count(";").sum())),
              "n_invalid_smiles": int(len(invalid)),
              "n_duplicate_2d_merged": int(merged.str.count(";").sum()),
              "n_distinct_2d": int(len(table))}
    return table.reset_index(drop=True), report


class AlignmentModel:
    """DreaMS (TorchScript) spectrum embedding + exported DreaMS-Morgan MSAlign towers."""

    def __init__(self, model_path: Path, dreams_path: Path):
        import torch
        self.torch = torch
        self.dreams = torch.jit.load(str(dreams_path), map_location="cpu").eval()
        bundle = torch.load(model_path, map_location="cpu", weights_only=False)
        from .towers import build_model
        self.model = build_model(bundle)
        self.vocab = bundle["input_dimensions"]["adduct_vocabulary"]
        self.unknown = int(bundle["input_dimensions"]["unknown_adduct_index"])

    def embed_spectrum(self, peaks: list[tuple[float, float]], precursor_mz: float):
        arr = np.array(peaks, dtype=np.float64).reshape(-1, 2)
        arr = arr[arr[:, 1] > 0]
        arr = arr[np.argsort(arr[:, 1])[::-1][:N_PEAKS]]          # strongest 100 peaks
        padded = np.zeros((N_PEAKS, 2))
        padded[: len(arr)] = arr
        padded[:, 1] = padded[:, 1] / padded[:, 1].max()           # relative intensity
        x = np.vstack([[precursor_mz, PRECURSOR_INTENSITY], padded]).astype(np.float32)
        with self.torch.inference_mode():
            return self.dreams(self.torch.from_numpy(x)[None])

    def score(self, peaks, meta, smiles: list[str]) -> np.ndarray:
        torch = self.torch
        F = torch.nn.functional
        spec = self.embed_spectrum(peaks, meta["precursor_mz"])
        adduct = self.vocab.index(meta["adduct"]) if meta["adduct"] in self.vocab else self.unknown
        md = {"collision_energy": torch.tensor([meta["collision_energy"]], dtype=torch.float32),
              "adduct": torch.tensor([adduct])}
        fps = torch.from_numpy(unpack(np.stack([morgan_packed(s) for s in smiles])).astype(np.float32))
        with torch.inference_mode():
            s = F.normalize(self.model.encode_spectrum(spec, md), dim=-1)
            m = F.normalize(self.model.encode_molecule(fps), dim=-1)
        return (s @ m.T).numpy()[0]


def rank_one(spectrum, candidates, args, model, thresholds) -> tuple[pd.DataFrame, dict]:
    qid = spectrum["params"].get("TITLE", spectrum["params"].get("SCANS", "query"))
    meta, reason = validate(spectrum["params"])
    summary = {"query_id": qid}
    if meta is None:
        summary.update(decision="refused", reason=reason)
        return pd.DataFrame(), summary
    if len(spectrum["peaks"]) < 1:
        summary.update(decision="refused", reason="empty peak list")
        return pd.DataFrame(), summary
    pool = candidates.copy()
    pool["ppm_error"] = ppm_error(meta["neutral_mass"], pool["exact_mass"].to_numpy())
    pool = pool[np.abs(pool["ppm_error"]) <= args.ppm].copy()
    summary.update(meta, n_candidates_in_window=int(len(pool)))
    if pool.empty:
        summary.update(decision="no candidate within window", reason=f"no structure within {args.ppm} ppm")
        return pd.DataFrame(), summary
    pool["score_mass"] = -np.round(np.abs(pool["ppm_error"].to_numpy()), 6)
    if model is not None:
        pool["score_model"] = model.score(spectrum["peaks"], meta, pool["smiles_2d"].tolist())
        key = "score_model"
        if meta["adduct"] not in model.vocab:
            summary["warning"] = f"model was not trained on {meta['adduct']}"
    else:
        key = "score_mass"
    pool = pool.sort_values(key, ascending=False, kind="stable").reset_index(drop=True)
    pool.insert(0, "rank", np.arange(1, len(pool) + 1))
    s = pool[key].to_numpy()
    pool["tied_with_previous"] = np.r_[False, s[1:] == s[:-1]]
    k = min(args.shortlist, len(pool))
    boundary_tie = len(pool) > k and s[k - 1] == s[k]
    pool["in_shortlist"] = pool["rank"] <= k
    decision = "nominate shortlist"
    if thresholds and key == "score_model" and s[0] < thresholds["tau"]:
        decision = "decline: top score below validation threshold"
    summary.update(decision=decision, ranking_score=key, shortlist_size=k,
                   tie_at_shortlist_boundary=bool(boundary_tie),
                   n_candidates_tied_with_shortlist_boundary=int((s == s[k - 1]).sum()),
                   top_score=float(s[0]))
    pool.insert(0, "query_id", qid)
    pool["decision"] = decision
    return pool, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spectra", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", type=Path)
    ap.add_argument("--dreams", type=Path)
    ap.add_argument("--thresholds", type=Path, help="JSON with key 'tau' fitted on validation")
    ap.add_argument("--ppm", type=float, default=10.0)
    ap.add_argument("--shortlist", type=int, default=5)
    args = ap.parse_args(argv)
    if (args.model is None) != (args.dreams is None):
        ap.error("--model and --dreams must be given together")
    model = AlignmentModel(args.model, args.dreams) if args.model else None
    thresholds = json.loads(args.thresholds.read_text()) if args.thresholds else None
    candidates, cand_report = prepare_candidates(args.candidates)
    tables, summaries = [], []
    for spectrum in read_mgf(args.spectra):
        table, summary = rank_one(spectrum, candidates, args, model, thresholds)
        tables.append(table)
        summaries.append(summary)
    out = pd.concat([t for t in tables if not t.empty], ignore_index=True) if any(
        not t.empty for t in tables) else pd.DataFrame()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    provenance = {
        "tool": "msms_shortlist", "version": __version__,
        "spectra_file": str(args.spectra), "spectra_sha256": sha256(args.spectra),
        "candidates_file": str(args.candidates), "candidates_sha256": sha256(args.candidates),
        "candidate_report": cand_report,
        "model": str(args.model) if args.model else None, "model_sha256": sha256(args.model),
        "dreams": str(args.dreams) if args.dreams else None, "dreams_sha256": sha256(args.dreams),
        "thresholds": thresholds, "ppm_window": args.ppm, "shortlist": args.shortlist,
        "queries": summaries,
        "note": "Shortlist for confirmation; scores are not probabilities; 2D identity (no stereochemistry).",
    }
    args.out.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2, default=float))
    for s in summaries:
        print(f"{s['query_id']}: {s['decision']}" + (f" ({s.get('reason')})" if s.get("reason") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
