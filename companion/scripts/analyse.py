"""Protocol sections 5-7: metrics, molecule-grouped intervals, contrasts, abstention.

Inputs are rank-statistic files written by rank_stats.py. Every method must
cover the same spectra; a spectrum missing from a method's file is a failure
and counts as a miss (protocol section 5).

    python analyse.py --test mass=ranks-mass-test.csv.gz msalign=... \
        --val mass=ranks-mass-val.csv.gz msalign=... \
        --fold-rows rows-test.txt --out results/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msms_shortlist.metrics import grouped_bootstrap, recall_expected, recall_strict, summarise  # noqa: E402

KS = (1, 5, 20)
POOLS = ("official_raw", "official_dedup", "sub16", "sub64", "expanded1024")
CONTRASTS = (("C1", "msalign", "mass"), ("C2", "msalign", "embcos"), ("C3", "deepsets", "mass"))
N_BOOT = 2000
SEED = 20261004


def load(spec: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for item in spec:
        name, path = item.split("=", 1)
        out[name] = pd.read_csv(path)
    return out


def random_rows(ref: pd.DataFrame) -> pd.DataFrame:
    """Random ordering: every decoy tied with the target gives the exact expectation."""
    df = ref[["row", "target_id", "pool", "n_pool", "n_pool_weighted"]].copy()
    df["b"] = 0.0
    df["t"] = df["n_pool_weighted"] - 1.0
    return df


def random_repeats(ref: pd.DataFrame, pool: str, n_seeds: int = 100) -> dict:
    sub = ref[ref.pool == pool]
    n = sub["n_pool_weighted"].to_numpy()
    res = {k: [] for k in KS}
    for seed in range(n_seeds):
        rng = np.random.default_rng(seed)
        rank = np.floor(rng.random(len(n)) * n) + 1
        for k in KS:
            res[k].append(float((rank <= k).mean()))
    return {f"R@{k}": {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}
            for k, v in res.items()}


def valid_ranks(sub: pd.DataFrame) -> np.ndarray:
    b, t = sub['b'].to_numpy(dtype=float), sub['t'].to_numpy(dtype=float)
    return np.isfinite(b) & np.isfinite(t) & (b >= 0) & (t >= 0)


def per_spectrum(df: pd.DataFrame, pool: str, rows: np.ndarray, k: int, rule: str) -> np.ndarray:
    sub = df[df.pool == pool].set_index("row").reindex(rows)
    fn = recall_expected if rule == "expected" else recall_strict
    vals = fn(sub["b"].to_numpy(), sub["t"].to_numpy(), k)
    return np.where(valid_ranks(sub) & np.isfinite(vals), vals, 0.0)  # failed spectrum = miss


def metrics_table(methods: dict, rows: np.ndarray, groups: np.ndarray) -> tuple[pd.DataFrame, dict]:
    records, boot_store = [], {}
    available = {pool for pool in POOLS if any((df.pool == pool).any() for df in methods.values())}
    if not available:
        raise ValueError('No candidate-pool rows available; cannot infer evaluation pools')
    for pool in POOLS:
        if pool not in available:
            continue
        for rule in ("expected", "strict"):
            values = {}
            for name, df in methods.items():
                for k in KS:
                    values[(name, k)] = per_spectrum(df, pool, rows, k, rule)
            if not values:
                continue
            keyed = {f"{n}|{k}": v for (n, k), v in values.items()}
            boots = grouped_bootstrap(keyed, groups, N_BOOT, SEED)
            boot_store[(pool, rule)] = (keyed, boots)
            for (name, k), v in values.items():
                s = summarise(v.mean(), boots[f"{name}|{k}"])
                n_missing = int((~valid_ranks(methods[name].query("pool == @pool").set_index("row").reindex(rows))).sum())
                records.append({"pool": pool, "rule": rule, "method": name, "k": k,
                                **{x: 100 * y for x, y in s.items()},
                                "n_spectra": int(len(rows)), "n_missing_or_failed": n_missing,
                                "n_molecules": int(len(np.unique(groups)))})
    return pd.DataFrame(records), boot_store


def contrasts(boot_store) -> pd.DataFrame:
    out = []
    for pool, rule in boot_store:
        keyed, boots = boot_store[(pool, rule)]
        for cid, a, b in CONTRASTS:
            for k in KS:
                ka, kb = f"{a}|{k}", f"{b}|{k}"
                if ka in keyed and kb in keyed:
                    diff = boots[ka] - boots[kb]
                    s = summarise(keyed[ka].mean() - keyed[kb].mean(), diff)
                    out.append({"contrast": cid, "a": a, "b": b, "pool": pool, "rule": rule, "k": k,
                                "primary": cid in {"C1", "C2", "C3"} and pool == "official_dedup"
                                and rule == "expected" and k == 5,
                                **{x: 100 * y for x, y in s.items()}})
    return pd.DataFrame(out)


def abstention(val: dict, test: dict, rows_val, rows_test, groups_test) -> tuple[pd.DataFrame, dict]:
    """Thresholds from validation (protocol section 7), applied once to test."""
    if len(rows_val) == 0 or len(rows_test) == 0:
        raise ValueError("abstention requires nonempty validation and test folds")
    records, curves = [], {}
    for name in test:
        if name not in val or name == "random":
            continue
        thr = {}
        v = val[name]
        fusion_mode = None
        if "fusion_normalization" in v.columns or "fusion_normalization" in test[name].columns:
            modes = []
            for frame in (v, test[name]):
                modes.append(set(frame.get("fusion_normalization", pd.Series(["unspecified"])).dropna())
                             if len(frame) else set())
            combined_modes = modes[0] | modes[1]
            if len(combined_modes) > 1 or "unspecified" in combined_modes:
                raise ValueError(f"{name}: validation/test fusion normalization mismatch or missing provenance")
            fusion_mode = next(iter(combined_modes), "unavailable_no_predictions")
        pv = v[v.pool == "official_dedup"].set_index("row").reindex(rows_val)
        av = v[v.pool == "absent"].set_index("row").reindex(rows_val)
        for frame in (pv, av):
            for column in ("top1", "top2", "b", "t"):
                frame[column] = frame[column].astype(float)
        for conf in ("top1", "margin"):
            cp = pv["top1"] if conf == "top1" else pv["top1"] - pv["top2"]
            ca = av["top1"] if conf == "top1" else av["top1"] - av["top2"]
            cp, ca = cp.to_numpy(), ca.to_numpy()
            # Failed predictions decline; all declared rows remain in denominators.
            cp = np.where(np.isfinite(cp) & valid_ranks(pv), cp, np.nan)
            finite_p, finite_a = cp[np.isfinite(cp)], ca[np.isfinite(ca)]
            # Choose the largest observed threshold reaching 90% of the full fold,
            # or maximum attainable coverage when failures make 90% impossible.
            if len(finite_p) == len(cp):
                tau_cov90 = float(np.quantile(cp, 0.10))  # preserve complete-run method
            elif len(finite_p):
                required = min(int(np.ceil(0.9 * len(cp))), len(finite_p))
                tau_cov90 = float(np.sort(finite_p)[-required])
            else:
                tau_cov90 = float("inf")
            cand = np.unique(np.concatenate([finite_p, finite_a]))
            fnr = np.array([((np.isfinite(ca)) & (ca >= c)).mean() for c in cand])
            ok = cand[fnr <= 0.10]
            # No absent calibration observations cannot justify nominations.
            tau_fn10 = float(ok.min()) if len(ok) and len(finite_a) else float("inf")
            thr[conf] = {"tau_cov90": tau_cov90, "tau_fn10": tau_fn10}
            t = test[name]
            pt = t[t.pool == "official_dedup"].set_index("row").reindex(rows_test)
            at = t[t.pool == "absent"].set_index("row").reindex(rows_test)
            for frame in (pt, at):
                for column in ("top1", "top2", "b", "t"):
                    frame[column] = frame[column].astype(float)
            ctp = (pt["top1"] if conf == "top1" else pt["top1"] - pt["top2"]).to_numpy()
            cta = (at["top1"] if conf == "top1" else at["top1"] - at["top2"]).to_numpy()
            valid_rank = valid_ranks(pt)
            ctp = np.where(valid_rank, ctp, np.nan)
            hit5 = recall_expected(pt["b"].to_numpy(), pt["t"].to_numpy(), 5)
            hit5 = np.where(valid_rank & np.isfinite(hit5), hit5, 0.0)
            for tname, tau in thr[conf].items():
                nom_p = (np.isfinite(ctp) & (ctp >= tau)).astype(float)
                nom_a = (np.isfinite(cta) & (cta >= tau)).astype(float)
                vals = {"coverage_present": nom_p, "false_nomination_absent": nom_a,
                        "hit5_and_nominated": nom_p * hit5}
                boots = grouped_bootstrap(vals, groups_test, N_BOOT, SEED)
                cov = nom_p.mean()
                # A no-nomination estimate/replicate uses zero by convention;
                # recall5_defined distinguishes it from an observed zero recall.
                rec = (nom_p * hit5).sum() / max(nom_p.sum(), 1)
                rec_boot = boots["hit5_and_nominated"] / np.maximum(boots["coverage_present"], 1e-12)
                records.append({"method": name, "confidence": conf, "threshold": tname, "tau": tau,
                                "coverage_present": summarise(cov, boots["coverage_present"]),
                                "recall5_among_nominated": summarise(rec, rec_boot),
                                "false_nomination_absent": summarise(nom_a.mean(), boots["false_nomination_absent"]),
                                **({"fusion_normalization": fusion_mode} if fusion_mode is not None else {}),
                                "n_validation": len(rows_val), "n_test": len(rows_test),
                                "n_valid_calibration_present": len(finite_p),
                                "n_valid_calibration_absent": len(finite_a),
                                "n_nominated_present": int(nom_p.sum()),
                                "recall5_defined": bool(nom_p.sum()),
                                "val_coverage_present": float((np.isfinite(cp) & (cp >= tau)).mean()),
                                "val_false_nomination_absent": float((np.isfinite(ca) & (ca >= tau)).mean())})
            # descriptive risk-coverage curve on test
            finite_test = np.concatenate([ctp[np.isfinite(ctp)], cta[np.isfinite(cta)]])
            grid = (np.unique(np.quantile(finite_test, np.linspace(0, 1, 101)))
                    if len(finite_test) else np.array([]))
            curves[f"{name}|{conf}"] = [
                {"tau": float(c), "coverage_present": float((np.isfinite(ctp) & (ctp >= c)).mean()),
                 "recall5_among_nominated": float(((np.isfinite(ctp) & (ctp >= c)) * hit5).sum() / max((np.isfinite(ctp) & (ctp >= c)).sum(), 1)),
                 "false_nomination_absent": float((np.isfinite(cta) & (cta >= c)).mean())} for c in grid]
    flat = []
    for r in records:
        row = {k: v for k, v in r.items() if not isinstance(v, dict)}
        for k, v in r.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    row[f"{k}_{kk}"] = vv
        flat.append(row)
    return pd.DataFrame(flat), curves


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", nargs="+", required=True)
    ap.add_argument("--val", nargs="+", default=[])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--fold", default="test")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    meta = pd.read_csv(args.data / "metadata.csv")
    folds = pd.read_csv(args.data / "splits" / f"{args.split}.csv")["fold"].to_numpy()
    rows_test = np.flatnonzero(folds == args.fold)
    rows_val = np.flatnonzero(folds == "val")
    groups_test = meta["unique_smiles_idx"].to_numpy()[rows_test]

    test, val = load(args.test), load(args.val)
    ref = next(iter(test.values()))
    test["random"] = random_rows(ref)
    table, boots = metrics_table(test, rows_test, groups_test)
    table.to_csv(args.out / "metrics.csv", index=False)
    contrasts(boots).to_csv(args.out / "contrasts.csv", index=False)
    rnd = {pool: random_repeats(ref, pool) for pool in POOLS if (ref.pool == pool).any()}
    (args.out / "random-repeats.json").write_text(json.dumps(rnd, indent=2))
    sizes = ref.groupby("pool")["n_pool"].describe()
    sizes.to_csv(args.out / "pool-sizes.csv")
    if val:
        ab, curves = abstention(val, test, rows_val, rows_test, groups_test)
        ab.to_csv(args.out / "abstention.csv", index=False)
        (args.out / "risk-coverage-curves.json").write_text(json.dumps(curves))
    print(table.query("pool == 'official_dedup' and rule == 'expected'")
          [["method", "k", "estimate", "ci_low", "ci_high"]].to_string(index=False))


if __name__ == "__main__":
    main()
