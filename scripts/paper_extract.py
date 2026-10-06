#!/usr/bin/env python3
"""Format archived historical results into LaTeX tables for the imported-evidence paper.

Formatting and extraction only; nothing is recomputed. Values are read from members of the archived
`downloads/msms-shortlist-results.tar.gz` (read in memory, never extracted). The archive digest is
checked against `evidence/import-manifest.json` and every member used against the member digests in
`evidence/migration-audit.json`. Values that the original article printed are cross-checked numerically
at the printed precision (ARTICLE below); any disagreement stops the build. Standard library only.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import evidence_integrity

ROOT = Path(__file__).resolve().parents[1]
TARPATH = "downloads/msms-shortlist-results.tar.gz"
PREFIX = "msms-shortlist-results/"
GEN = ROOT / "paper/generated"
METHODS = ["random", "mass", "deepsets", "embcos", "msalign", "fusion"]
NAMES = {"random": "Random ordering (expectation)", "mass": "Precursor mass error", "deepsets": "DeepSets fingerprint predictor",
         "embcos": "Emb-Cos", "msalign": "DreaMS + Morgan alignment", "fusion": "Alignment + mass fusion (exploratory)"}
SHORT = {"random": "Random", "mass": "Mass error", "deepsets": "DeepSets", "embcos": "Emb-Cos",
         "msalign": "DreaMS + Morgan", "fusion": "Fusion (expl.)"}
POOLS = {"sub16": "16", "sub64": "64", "official_dedup": "official, dedup.", "official_raw": "official, raw",
         "expanded1024": "expanded"}

# Article values (percent unless stated), checked at printed precision.
ARTICLE = {
    "main": {  # official_dedup, expected: R@1, R@5, R@20 with CIs
        "mass": [("3.7", "2.9", "4.5"), ("13.3", "11.2", "15.6"), ("32.0", "28.4", "35.5")],
        "deepsets": [("13.4", "10.6", "16.5"), ("31.3", "27.2", "35.5"), ("53.9", "49.4", "57.9")],
        "embcos": [("36.1", "31.6", "40.9"), ("63.2", "58.4", "67.5"), ("82.4", "79.5", "85.1")],
        "msalign": [("33.2", "28.3", "38.4"), ("61.4", "56.2", "66.3"), ("83.9", "80.8", "86.8")],
        "fusion": [("35.2", "30.4", "40.2"), ("64.8", "59.6", "69.9"), ("86.2", "83.0", "89.0")],
    },
    "random": ("0.4", "2.1", "8.5"),
    "repro": {"msalign": ("32.6", "56.8", "76.7"), "embcos": ("35.4", "59.3", "76.8"), "deepsets": ("13.1", "27.9", "46.9")},
    "contrasts": {"C1": ("48.0", "42.2", "53.6"), "C2": ("-1.85", "-5.19", "1.35"), "C3": ("18.0", "13.4", "22.5")},
    "pool_r5": {("msalign", "sub16"): "94.5", ("msalign", "sub64"): "81.4", ("msalign", "expanded1024"): "41.3",
                ("embcos", "sub16"): "93.8", ("embcos", "expanded1024"): "45.9", ("fusion", "expanded1024"): "43.9",
                ("random", "sub16"): "31.2", ("random", "expanded1024"): "1.3"},
    "pool_r1": {("msalign", "sub16"): "69.2", ("msalign", "expanded1024"): "19.1"},
    "rules": {("mass", "official_raw", "strict", 5): "6.3", ("mass", "official_raw", "strict", 1): "0.8",
              ("msalign", "official_raw", "strict", 5): "56.8"},
    "abst": {("msalign", "top1", "tau_fn10"): ("21.3", "16.2", "26.6", "68.4", "13.2", "9.0", "18.0"),
             ("msalign", "top1", "tau_cov90"): ("90.8", None, None, "64.3", "86.6", None, None),
             ("embcos", "top1", "tau_fn10"): ("25.5", "22.0", "29.1", "83.7", "15.7", "12.5", "19.1"),
             ("embcos", "top1", "tau_cov90"): ("90.8", None, None, "66.6", "85.6", None, None),
             ("deepsets", "top1", "tau_fn10"): ("18.4", None, None, "52.8", "15.1", None, None),
             ("fusion", "top1", "tau_fn10"): ("21.8", None, None, "86.8", "10.2", None, None),
             ("mass", "top1", "tau_fn10"): ("12.2", None, None, "22.1", "12.1", None, None),
             ("msalign", "margin", "tau_fn10"): ("13.8", None, None, None, "9.6", None, None),
             ("embcos", "margin", "tau_fn10"): ("18.4", None, None, None, "9.8", None, None)},
    "strata": {("mass", "<0.01 ppm"): "31.6", ("mass", "0.01-10 ppm"): "9.2", ("mass", ">10 ppm"): "0.1",
               ("msalign", "<0.01 ppm"): "54.3", ("msalign", "0.01-10 ppm"): "61.8", ("msalign", ">10 ppm"): "78.5",
               ("embcos", "<0.01 ppm"): "59.0", ("embcos", "0.01-10 ppm"): "63.7", ("embcos", ">10 ppm"): "71.2",
               ("fusion", "<0.01 ppm"): "62.7", ("fusion", "0.01-10 ppm"): "64.2", ("fusion", ">10 ppm"): "77.4",
               ("msalign", "Orbitrap"): "57.2", ("msalign", "QTOF"): "71.2"},
    "threshold": "0.599", "fusion_w": "0.55", "train_hours": "7.75", "pool_median": "252", "exp_median": "449",
}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def close(value: float, printed: str) -> bool:
    s = printed.replace("−", "-")
    digits = len(s.split(".")[1]) if "." in s else 0
    return abs(value - float(s)) <= 0.5 * 10 ** (-digits) + 1e-9


def f1(x: float) -> str:
    return f"{x:.1f}"


def sg(x: float, nd: int = 1) -> str:
    s = f"{x:+.{nd}f}"
    return "$" + s + "$"


def main(corrected: bool = False) -> None:
    try:
        evidence_integrity.verify_or_fail("paper_extract")
    except evidence_integrity.IntegrityError as exc:
        sys.exit(str(exc))
    GEN.mkdir(parents=True, exist_ok=True)
    manifest = {f["path"]: f["sha256"] for f in json.loads((ROOT / "evidence/import-manifest.json").read_text())["files"]}
    audit = json.loads((ROOT / "evidence/migration-audit.json").read_text())
    members = {m["path"]: m["sha256"] for a in audit["archives"] if a["path"] == TARPATH for m in a["members"]}
    raw = (ROOT / TARPATH).read_bytes()
    if sha256(raw) != manifest[TARPATH]:
        sys.exit("results archive digest mismatch")
    tf = tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")
    used: dict[str, str] = {}

    def read(name: str) -> bytes:
        data = tf.extractfile(PREFIX + name).read()
        if sha256(data) != members[PREFIX + name]:
            sys.exit(f"member digest mismatch: {name}")
        used[PREFIX + name] = members[PREFIX + name]
        return data

    def rows(name: str) -> list[dict]:
        return list(csv.DictReader(io.StringIO(read(name).decode())))

    correction = None
    if corrected:
        import corrected_evidence
        correction, corrected_run = corrected_evidence.load()
        historical_rows = rows
        def rows(name):
            if name in {"analysis/metrics.csv", "analysis/contrasts.csv", "analysis/abstention.csv"}:
                return list(csv.DictReader((corrected_run / name).open()))
            return historical_rows(name)

    MET = rows("analysis/metrics.csv")
    CON = rows("analysis/contrasts.csv")
    ABS = rows("analysis/abstention.csv")
    PS = rows("analysis/pool-sizes.csv")
    STR = rows("analysis/strata-post-hoc.csv")
    RR = json.loads(read("analysis/random-repeats.json"))
    M1 = rows("analysis-mces1/metrics.csv")
    PS1 = rows("analysis-mces1/pool-sizes.csv")
    T01 = json.loads(read("receipts/T01-msalign-dreams-morgan-formula1-20261004T220904Z/train-receipt.json"))
    T02 = json.loads(read("receipts/T02-embcos-formula1-20261005T055415Z/released-result.json"))
    T03 = json.loads(read("receipts/T03-deepsets-formula1-20261005T085424Z/released-result.json"))
    A02 = json.loads(read("receipts/A02-precursor-error-audit-20261004T224918Z/summary.json"))
    V01 = json.loads(read("receipts/V01-dreams-torchscript-equivalence-20261004T221550Z/result.json"))
    X02 = read("receipts/X02-cli-demo-20261005T060708Z/consistency-check.txt").decode()
    FW = json.loads((ROOT / "companion/results/fusion-weight.json").read_text())
    if corrected:
        FW = json.loads((corrected_run / "fusion-weight.json").read_text())
    mism: list[str] = []

    def check(label, value, printed):
        # Historical values are checked in the mandatory first pass. The second
        # pass renders independently digest-verified corrected outputs; comparing
        # corrected fusion to the superseded article would reject the correction.
        if corrected or printed is None:
            return
        if value is None or not close(float(value), printed):
            mism.append(f"{label}: archive {value!r} vs article {printed!r}")

    def m(pool, rule, method, k):
        for r in MET:
            if (r["pool"], r["rule"], r["method"], r["k"]) == (pool, rule, method, str(k)):
                return r
        raise KeyError((pool, rule, method, k))

    # ---- Table: reproduction (official_raw, strict)
    released = {"embcos": T02["metrics"]["test"], "deepsets": T03["metrics"]["test"]}
    lines = []
    band = {"msalign": "33.0--44.2 / 56.2--64.6 / 76.0--79.2", "embcos": "36.7--48.7 / 59.6--70.8 / 77.2--83.6",
            "deepsets": "3.5--5.9 / 10.4--15.6 / 23.5--31.5"}
    verdict = {"msalign": "R@1 just below; R@5, R@20 inside", "embcos": "all three below", "deepsets": "all three far above"}
    label = {"msalign": "DreaMS + Morgan pair, MSAlign code (step 3,296 of 30,000)", "embcos": "Emb-Cos, model\\_zoo (epoch 3)",
             "deepsets": "DeepSets + Fourier, model\\_zoo (epoch 3)"}
    for meth in ("msalign", "embcos", "deepsets"):
        vals = [float(m("official_raw", "strict", meth, k)["estimate"]) for k in (1, 5, 20)]
        for v, w, k in zip(vals, ARTICLE["repro"][meth], (1, 5, 20)):
            check(f"repro {meth} R@{k}", v, w)
        if meth in released:
            rel = released[meth]
            for v, k in zip(vals, (1, 5, 20)):
                if abs(v - 100 * rel[f"R@{k} (test)"]) > 0.01:
                    mism.append(f"harness vs released evaluation {meth} R@{k}")
        lines.append(f"{label[meth]} & {vals[0]:.1f} & {vals[1]:.1f} & {vals[2]:.1f} & {band[meth]} & {verdict[meth]} \\\\")
    (GEN / "tab_repro.tex").write_text("\n".join(lines) + "\n")

    # ---- Table: main new measurement (official_dedup, expected)
    lines = []
    rnd = [RR["official_dedup"][f"R@{k}"]["mean"] * 100 for k in (1, 5, 20)]
    for v, w in zip(rnd, ARTICLE["random"]):
        check("random dedup", v, w)
    lines.append(f"{NAMES['random']} & {rnd[0]:.1f} & {rnd[1]:.1f} & {rnd[2]:.1f} \\\\")
    for meth in ("mass", "deepsets", "embcos", "msalign", "fusion"):
        cells = []
        for k, w in zip((1, 5, 20), ARTICLE["main"][meth]):
            r = m("official_dedup", "expected", meth, k)
            e, lo, hi = float(r["estimate"]), float(r["ci_low"]), float(r["ci_high"])
            check(f"main {meth} R@{k}", e, w[0]); check(f"main {meth} R@{k} lo", lo, w[1]); check(f"main {meth} R@{k} hi", hi, w[2])
            if r["n_missing_or_failed"] != "0" or r["n_spectra"] != "10648" or r["n_molecules"] != "1421":
                mism.append(f"population/failures {meth}")
            cells.append(f"{e:.1f} [{lo:.1f}, {hi:.1f}]")
        lines.append(f"{NAMES[meth]} & " + " & ".join(cells) + " \\\\")
    (GEN / "tab_main.tex").write_text("\n".join(lines) + "\n")

    # ---- Primary contrasts
    desc = {"C1": "C1: DreaMS + Morgan minus mass error", "C2": "C2: DreaMS + Morgan minus Emb-Cos", "C3": "C3: DeepSets minus mass error"}
    lines = []
    for r in CON:
        if r["primary"] == "True":
            w = ARTICLE["contrasts"][r["contrast"]]
            e, lo, hi = float(r["estimate"]), float(r["ci_low"]), float(r["ci_high"])
            nd = 2 if r["contrast"] == "C2" else 1
            check(r["contrast"], e, w[0]); check(r["contrast"] + " lo", lo, w[1]); check(r["contrast"] + " hi", hi, w[2])
            lines.append(f"{desc[r['contrast']]} & {sg(e, nd)} [{sg(lo, nd)}, {sg(hi, nd)}] \\\\")
    (GEN / "tab_contrasts.tex").write_text("\n".join(lines) + "\n")

    # Appendix: all contrasts (longtable body)
    lines = []
    for r in CON:
        e, lo, hi = float(r["estimate"]), float(r["ci_low"]), float(r["ci_high"])
        lines.append(f"{r['contrast']} & {POOLS[r['pool']]} & {r['rule']} & {r['k']} & {'yes' if r['primary'] == 'True' else ''} & "
                     f"{sg(e, 2)} [{sg(lo, 2)}, {sg(hi, 2)}] \\\\")
    (GEN / "tab_contrasts_all.tex").write_text("\n".join(lines) + "\n")
    # The expanded-pool C2 value quoted in the article
    c2x = next(r for r in CON if r["contrast"] == "C2" and r["pool"] == "expanded1024" and r["rule"] == "expected" and r["k"] == "5")
    check("C2 expanded", float(c2x["estimate"]), "-4.56"); check("C2 expanded lo", float(c2x["ci_low"]), "-7.95")
    check("C2 expanded hi", float(c2x["ci_high"]), "-1.19")

    # ---- Pool-size stress (R@5 and R@1, expected)
    med = {r["pool"]: float(r["50%"]) for r in PS}
    check("dedup median", med["official_dedup"], ARTICLE["pool_median"]); check("expanded median", med["expanded1024"], ARTICLE["exp_median"])
    order = ["sub16", "sub64", "official_dedup", "expanded1024"]
    lines = []
    for k in (5, 1):
        for meth in METHODS:
            cells = []
            for pool in order:
                if meth == "random":
                    v = RR[pool][f"R@{k}"]["mean"] * 100
                else:
                    v = float(m(pool, "expected", meth, k)["estimate"])
                key = (meth, pool)
                if k == 5 and key in ARTICLE["pool_r5"]:
                    check(f"pool R@5 {key}", v, ARTICLE["pool_r5"][key])
                if k == 1 and key in ARTICLE["pool_r1"]:
                    check(f"pool R@1 {key}", v, ARTICLE["pool_r1"][key])
                cells.append(f"{v:.1f}")
            lines.append(f"R@{k} & {SHORT[meth]} & " + " & ".join(cells) + " \\\\")
        if k == 5:
            lines.append("\\midrule")
    (GEN / "tab_pools.tex").write_text("\n".join(lines) + "\n")
    lines = [f"{POOLS.get(r['pool'], r['pool'].replace('_', ' '))} & {float(r['count']):,.0f} & {float(r['mean']):.1f} & "
             f"{float(r['min']):.0f} & {float(r['25%']):.0f} & {float(r['50%']):.0f} & {float(r['75%']):.0f} & {float(r['max']):.0f} \\\\"
             for r in PS]
    (GEN / "tab_poolsizes.tex").write_text("\n".join(lines) + "\n")
    hdr = " & ".join(f"{med[p]:.0f}" for p in order)
    (GEN / "pool_medians.tex").write_text(hdr + "\n")

    # ---- Tie and duplicate rules (R@1 and R@5)
    lines = []
    for meth in ("mass", "deepsets", "embcos", "msalign", "fusion"):
        cells = []
        for pool, rule in (("official_raw", "strict"), ("official_dedup", "strict"), ("official_raw", "expected"), ("official_dedup", "expected")):
            v5 = float(m(pool, rule, meth, 5)["estimate"]); v1 = float(m(pool, rule, meth, 1)["estimate"])
            for k, v in ((5, v5), (1, v1)):
                key = (meth, pool, rule, k)
                if key in ARTICLE["rules"]:
                    check(f"rules {key}", v, ARTICLE["rules"][key])
            cells.append(f"{v5:.1f} / {v1:.1f}")
        lines.append(f"{SHORT[meth]} & " + " & ".join(cells) + " \\\\")
    (GEN / "tab_rules.tex").write_text("\n".join(lines) + "\n")

    # ---- Abstention
    def a(meth, conf, tau):
        return next(r for r in ABS if (r["method"], r["confidence"], r["threshold"]) == (meth, conf, tau))

    main_rows = [("msalign", "top1", "tau_fn10"), ("msalign", "top1", "tau_cov90"), ("embcos", "top1", "tau_fn10"),
                 ("embcos", "top1", "tau_cov90"), ("deepsets", "top1", "tau_fn10"), ("fusion", "top1", "tau_fn10"),
                 ("mass", "top1", "tau_fn10")]
    rule_txt = {"tau_fn10": "at most 10\\% false", "tau_cov90": "keep 90\\% covered"}
    lines, all_lines = [], []
    for meth, conf, tau in [(mm, c, t) for mm in ("msalign", "embcos", "deepsets", "fusion", "mass") for c in ("top1", "margin")
                            for t in ("tau_fn10", "tau_cov90")]:
        r = a(meth, conf, tau)
        cov = [100 * float(r[x]) for x in ("coverage_present_estimate", "coverage_present_ci_low", "coverage_present_ci_high")]
        rec = [100 * float(r[x]) for x in ("recall5_among_nominated_estimate", "recall5_among_nominated_ci_low", "recall5_among_nominated_ci_high")]
        fal = [100 * float(r[x]) for x in ("false_nomination_absent_estimate", "false_nomination_absent_ci_low", "false_nomination_absent_ci_high")]
        w = ARTICLE["abst"].get((meth, conf, tau))
        if w:
            check(f"abst cov {meth}{conf}{tau}", cov[0], w[0]); check("lo", cov[1], w[1]); check("hi", cov[2], w[2])
            check(f"abst rec {meth}{conf}{tau}", rec[0], w[3]); check(f"abst false {meth}{conf}{tau}", fal[0], w[4])
            check("flo", fal[1], w[5]); check("fhi", fal[2], w[6])
        all_lines.append(f"{SHORT[meth]} & {conf} & {rule_txt[tau]} & {float(r['tau']):.4f} & {100 * float(r['val_false_nomination_absent']):.1f} & "
                         f"\\ci{{{cov[0]:.1f}}}{{{cov[1]:.1f}}}{{{cov[2]:.1f}}} & \\ci{{{rec[0]:.1f}}}{{{rec[1]:.1f}}}{{{rec[2]:.1f}}} & "
                         f"\\ci{{{fal[0]:.1f}}}{{{fal[1]:.1f}}}{{{fal[2]:.1f}}} \\\\")
    for meth, conf, tau in main_rows:
        r = a(meth, conf, tau)
        cov = [100 * float(r[x]) for x in ("coverage_present_estimate", "coverage_present_ci_low", "coverage_present_ci_high")]
        rec = 100 * float(r["recall5_among_nominated_estimate"])
        fal = [100 * float(r[x]) for x in ("false_nomination_absent_estimate", "false_nomination_absent_ci_low", "false_nomination_absent_ci_high")]
        lines.append(f"{SHORT[meth]} & {rule_txt[tau]} & \\ci{{{cov[0]:.1f}\\%}}{{{cov[1]:.1f}}}{{{cov[2]:.1f}}} & {rec:.1f}\\% & "
                     f"\\ci{{{fal[0]:.1f}\\%}}{{{fal[1]:.1f}}}{{{fal[2]:.1f}}} \\\\")
    (GEN / "tab_abstention.tex").write_text("\n".join(lines) + "\n")
    (GEN / "tab_abstention_all.tex").write_text("\n".join(all_lines) + "\n")
    check("threshold", float(a("msalign", "top1", "tau_fn10")["tau"]), ARTICLE["threshold"])

    # ---- Strata
    lines_p, lines_i = [], []
    lev = {"<0.01 ppm": "Within 0.01 ppm (recomputed-looking)", "0.01-10 ppm": "0.01--10 ppm", ">10 ppm": "Beyond 10 ppm"}
    st = {(r["method"], r["stratum"], r["level"]): r for r in STR}
    for level in ("<0.01 ppm", "0.01-10 ppm", ">10 ppm"):
        base = st[("mass", "precursor_precision", level)]
        cells = []
        for meth in ("mass", "deepsets", "msalign", "embcos", "fusion"):
            r = st[(meth, "precursor_precision", level)]
            v = float(r["recall5_estimate"])
            if (meth, level) in ARTICLE["strata"]:
                check(f"strata {meth} {level}", v, ARTICLE["strata"][(meth, level)])
            cells.append(f"\\ci{{{v:.1f}}}{{{float(r['recall5_ci_low']):.1f}}}{{{float(r['recall5_ci_high']):.1f}}}")
        lines_p.append(f"{lev[level]} & {int(base['n_spectra']):,} / {int(base['n_molecules']):,} & " + " & ".join(cells) + " \\\\")
    for level in ("Orbitrap", "QTOF", "unmapped"):
        base = st[("mass", "instrument", level)]
        cells = []
        for meth in ("mass", "deepsets", "msalign", "embcos", "fusion"):
            r = st[(meth, "instrument", level)]
            v = float(r["recall5_estimate"])
            if (meth, level) in ARTICLE["strata"]:
                check(f"strata {meth} {level}", v, ARTICLE["strata"][(meth, level)])
            cells.append(f"\\ci{{{v:.1f}}}{{{float(r['recall5_ci_low']):.1f}}}{{{float(r['recall5_ci_high']):.1f}}}")
        lines_i.append(f"{level} & {int(base['n_spectra']):,} / {int(base['n_molecules']):,} & " + " & ".join(cells) + " \\\\")
    (GEN / "tab_strata_precursor.tex").write_text("\n".join(lines_p) + "\n")
    (GEN / "tab_strata_instrument.tex").write_text("\n".join(lines_i) + "\n")

    # ---- Fusion weight grid
    grid = FW["validation_recall5_by_w"]
    check("fusion w", FW["chosen_w_mass"], ARTICLE["fusion_w"])
    ws = list(grid)
    half = (len(ws) + 1) // 2
    lines = []
    for i in range(half):
        left = f"{float(ws[i]):.2f} & {100 * grid[ws[i]]:.2f}"
        right = f"{float(ws[i + half]):.2f} & {100 * grid[ws[i + half]]:.2f}" if i + half < len(ws) else " & "
        lines.append(f"{left} & {right} \\\\")
    (GEN / "tab_fusion.tex").write_text("\n".join(lines) + "\n")

    # ---- MCES-1 secondary descriptive population (cheap baselines only)
    lines = []
    for r in M1:
        if r["k"] == "5" or r["k"] == "1" or r["k"] == "20":
            lines.append(f"{POOLS.get(r['pool'], r['pool'])} & {r['rule']} & {SHORT[r['method']]} & {r['k']} & "
                         f"{float(r['estimate']):.1f} [{float(r['ci_low']):.1f}, {float(r['ci_high']):.1f}] \\\\")
    (GEN / "tab_mces1.tex").write_text("\n".join(lines) + "\n")
    n1 = {r["n_spectra"] for r in M1}; mol1 = {r["n_molecules"] for r in M1}

    # ---- Precursor audit
    lines = []
    for fold in ("train", "val"):
        s = A02[fold]
        lines.append(f"{'training' if fold == 'train' else 'validation'} & {s['n']:,} & {100 * s['frac_abs_ppm_lt_0.01']:.1f} & "
                     f"{100 * s['frac_abs_ppm_lt_0.1']:.1f} & {100 * s['frac_abs_ppm_lt_1']:.1f} & {100 * s['frac_abs_ppm_lt_5']:.1f} & "
                     f"{100 * s['frac_abs_ppm_lt_10']:.1f} & {s['median_abs_ppm']:.3f} \\\\")
    (GEN / "tab_precursor.tex").write_text("\n".join(lines) + "\n")
    check("train within 0.01", 100 * A02["train"]["frac_abs_ppm_lt_0.01"], "19.0")

    # ---- Macros
    hours = T01["wall_seconds"] / 3600
    check("train hours", hours, ARTICLE["train_hours"])
    mac = {"FusionExpandedRecall": f"{float(m('expanded1024', 'expected', 'fusion', 5)['estimate']):.1f}", "DedupMedian": f"{med['official_dedup']:.0f}", "ExpandedMedian": f"{med['expanded1024']:.0f}",
           "TrainHours": f"{hours:.2f}", "DeepSetsHours": f"{T03['elapsed_seconds'] / 3600:.2f}",
           "Threshold": f"{float(a('msalign', 'top1', 'tau_fn10')['tau']):.4f}", "FusionW": f"{FW['chosen_w_mass']:.2f}",
           "VCosMin": f"{V01['cosine_min']:.8f}", "VSpectra": str(V01["n"]),
           "MCESSpectra": f"{int(next(iter(n1))):,}", "MCESMolecules": f"{int(next(iter(mol1))):,}",
           "TrainPrecursorWithin": f"{100 * A02['train']['frac_abs_ppm_lt_0.01']:.1f}",
           "MCESDedupMedian": f"{float(next(r for r in PS1 if r['pool'] == 'official_dedup')['50%']):.0f}",
           "MCESSubMin": f"{float(next(r for r in PS1 if r['pool'] == 'sub64')['min']):.0f}"}
    (GEN / "cli_consistency.txt").write_text(X02)
    (GEN / "macros.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in mac.items()))

    receipt = {"schema_version": 1, "kind": "formatting/extraction only; no recomputation",
               "archive": TARPATH, "archive_sha256": manifest[TARPATH], "members_read_in_memory": used,
               "also_read": {"companion/results/fusion-weight.json": sha256((ROOT / "companion/results/fusion-weight.json").read_bytes())},
               "cross_check_against_article_values": "Tables 3-7, pool-size, tie-rule and abstention values, contrasts (incl. expanded-pool C2), threshold, fusion weight, training time; numeric at printed precision",
               "cross_check_mismatches": mism, "generated": sorted(p.name for p in GEN.glob("*.tex"))}
    if corrected:
        receipt["kind"] = "corrected cached-score tables plus unchanged historical supplementary evidence"
        receipt["corrected_evidence"] = correction
        receipt["historical_validation"] = json.loads((GEN / "historical-extraction-receipt.json").read_text())
        receipt["cross_check_against_article_values"] = "Historical first pass only; corrected tables bound to execution hashes and invariance report"
    (GEN / "extraction-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if mism:
        print("\n".join(mism))
        sys.exit("generated tables disagree with the article's reported values")
    print(f"extracted {len(used)} archive members; {len(receipt['generated'])} generated files; 0 mismatches")


if __name__ == "__main__":
    import corrected_evidence
    corrected_evidence.load()  # fail before overwriting any generated output
    main()
    (GEN / "historical-extraction-receipt.json").write_text((GEN / "extraction-receipt.json").read_text())
    main(corrected=True)
