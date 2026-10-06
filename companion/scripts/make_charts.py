"""Draw the article charts from saved analysis receipts only (no model is re-run).

    python make_charts.py --analysis runs/AN01-*/analysis --precursor runs/A02-*/precursor-ppm-error.csv.gz \
        --out assets/charts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Fixed categorical order (validated: light surface, adjacent CVD dE >= 9.1).
# Every series is direct-labelled and has its own marker because three slots
# are below 3:1 contrast on the surface.
STYLE = {
    "msalign": ("DreaMS + Morgan alignment", "#2a78d6", "o"),
    "mass": ("Precursor mass error", "#eb6834", "s"),
    "embcos": ("Emb-Cos", "#1baf7a", "D"),
    "deepsets": ("DeepSets fingerprint", "#eda100", "^"),
    "fusion": ("Alignment + mass fusion", "#e87ba4", "v"),
}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#6b6a66", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "lines.linewidth": 2,
})


def val(df, **kw):
    """Single estimate selected by exact column matches (avoids query scoping)."""
    mask = np.ones(len(df), dtype=bool)
    for k, v in kw.items():
        mask &= (df[k] == v).to_numpy()
    return df[mask]["estimate"].iloc[0]


def spread(ys, gap):
    """Shift label y positions apart by at least `gap`, keeping their order."""
    order = np.argsort(ys)
    out = np.array(ys, dtype=float)
    for a, b in zip(order[:-1], order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def present(df, methods):
    return [m for m in methods if m in set(df["method"])]


def footnote(fig, text):
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=9, color=MUTED, wrap=True)


def chart_recall(metrics, out):
    d = metrics.query("pool == 'official_dedup' and rule == 'expected'")
    methods = present(d, ["msalign", "embcos", "fusion", "deepsets", "mass"])
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=True)
    for ax, k in zip(axes, (1, 5, 20)):
        rnd = d.query("method == 'random' and k == @k")["estimate"].iloc[0]
        for y, m in enumerate(methods[::-1]):
            r = d.query("method == @m and k == @k").iloc[0]
            name, color, marker = STYLE[m]
            ax.plot([r.ci_low, r.ci_high], [y, y], color=color, solid_capstyle="round")
            ax.plot(r.estimate, y, marker=marker, color=color, markersize=9, markeredgecolor=SURFACE, markeredgewidth=1.5)
            ax.text(r.ci_high + 1.5, y, f"{r.estimate:.1f}", va="center", fontsize=10, color=INK)
        ax.axvline(rnd, color=MUTED, linestyle="--", linewidth=1.2)
        ax.text(rnd + 1, len(methods) - 0.45, f"random {rnd:.1f}", fontsize=9, color=MUTED)
        ax.set_title(f"Recall@{k}" + ("  (the five-structure budget)" if k == 5 else ""), loc="left", fontsize=12, color=INK)
        ax.set_xlim(0, 100)
    axes[1].set_xlabel("% of test spectra with the true structure in the top k")
    axes[0].set_yticks(range(len(methods)))
    axes[0].set_yticklabels([STYLE[m][0] for m in methods[::-1]])
    fig.suptitle("Formula split (seed 1), 10,648 test spectra, deduplicated official pools", x=0.01, ha="left", fontsize=13, color=INK)
    footnote(fig, "Points: spectrum-level recall, ties broken at random in expectation. Bars: 95% intervals from 2,000 bootstrap "
                  "resamples of the 1,421 test molecules. All learned models newly trained here with released code and settings, one seed.")
    fig.subplots_adjust(left=0.2, right=0.98, top=0.84, bottom=0.22, wspace=0.12)
    fig.savefig(out, dpi=200)
    plt.close(fig)


def chart_pool_size(metrics, sizes, out):
    d = metrics.query("rule == 'expected' and k == 5")
    pools = ["sub16", "sub64", "official_dedup", "expanded1024"]
    x = [float(sizes.loc[p, "50%"]) for p in pools]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    labels = []
    for m in present(d, ["msalign", "embcos", "fusion", "deepsets", "mass", "random"]):
        ys = [val(d, method=m, pool=p) for p in pools]
        if m == "random":
            ax.plot(x, ys, color=MUTED, linestyle="--", linewidth=1.2)
            labels.append((ys[-1], "random", MUTED))
            continue
        name, color, marker = STYLE[m]
        ax.plot(x, ys, color=color, marker=marker, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5)
        labels.append((ys[-1], f"{name} {ys[-1]:.1f}", INK))
    pos = spread([l[0] for l in labels], 4.5)
    for (y0, text, color), y in zip(labels, pos):
        ax.text(x[-1] * 1.08, y, text, va="center", fontsize=10, color=color)
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(v)}\n{lab}" for v, lab in zip(x, ["subsample", "subsample", "official", "official + 4M"])])
    ax.set_xlim(x[0] * 0.8, x[-1] * 3.2)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Recall@5, % of test spectra")
    ax.set_xlabel("Median candidate-pool size (distinct 2D structures)")
    ax.set_title("More candidates, fewer hits in the top five", loc="left", fontsize=13, color=INK)
    footnote(fig, "Smaller pools are seeded random subsets of the official pool. The largest pool adds same-mass (10 ppm) structures from "
                  "the MassSpecGym 4M set, capped at 1,024 (5% of the 2,849 validation and test targets reach the cap). Target always present.")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def chart_ties(metrics, out):
    d = metrics.query("pool == 'official_raw' and k == 5")
    d2 = metrics.query("pool == 'official_dedup' and rule == 'expected' and k == 5")
    methods = present(d, ["msalign", "embcos", "deepsets", "mass"])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    labels = ["Strict ties,\nduplicates kept\n(released rule)", "Random ties,\nduplicates kept", "Random ties,\nduplicates removed\n(this article)"]
    ends, starts = [], []
    for i, m in enumerate(methods):
        vals = [val(d, method=m, rule="strict"), val(d, method=m, rule="expected"), val(d2, method=m)]
        name, color, marker = STYLE[m]
        ax.plot(range(3), vals, color=color, marker=marker, markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5)
        ends.append((vals[-1], f"{name} {vals[-1]:.1f}"))
        starts.append((vals[0], f"{vals[0]:.1f}"))
    for group, xpos, ha in ((ends, 2.08, "left"), (starts, -0.08, "right")):
        for (y0, text), y in zip(group, spread([g[0] for g in group], 3.2)):
            ax.text(xpos, y, text, va="center", ha=ha, fontsize=10, color=INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.5, 3.1)
    ax.set_ylabel("Recall@5, % of test spectra")
    ax.set_title("Scoring conventions move the cheap baseline most", loc="left", fontsize=13, color=INK)
    footnote(fig, "Same scores, three bookkeeping rules. The mass ranking ties every isomer of the target, so the strict rule counts all of "
                  "them ahead of it.")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def chart_abstention(curves, abst, out):
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    for m in ["msalign", "embcos", "fusion", "deepsets", "mass"]:
        key = f"{m}|top1"
        if key not in curves:
            continue
        c = pd.DataFrame(curves[key]).sort_values("false_nomination_absent")
        name, color, marker = STYLE[m]
        ax.plot(100 * c.false_nomination_absent, 100 * c.coverage_present, color=color)
        row = abst.query("method == @m and confidence == 'top1' and threshold == 'tau_fn10'")
        if len(row):
            r = row.iloc[0]
            ax.plot(100 * r.false_nomination_absent_estimate, 100 * r.coverage_present_estimate, marker=marker,
                    color=color, markersize=9, markeredgecolor=SURFACE, markeredgewidth=1.5, linestyle="none",
                    label=f"{name}: {100 * r.coverage_present_estimate:.0f}% covered, "
                          f"{100 * r.false_nomination_absent_estimate:.0f}% false")
    ax.plot([0, 100], [0, 100], color=MUTED, linestyle="--", linewidth=1.2)
    ax.text(70, 64, "no better than chance", rotation=33, fontsize=9, color=MUTED)
    ax.legend(loc="lower right", fontsize=9, frameon=False, title="At the validation-fitted threshold (test)",
              title_fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("% of target-removed test queries still given a shortlist (false nominations)")
    ax.set_ylabel("% of target-present test queries given a shortlist")
    ax.set_title("The top score is only a weak signal that the answer is missing", loc="left", fontsize=13, color=INK)
    footnote(fig, "Curves sweep the top-score threshold on test. Markers: threshold fitted on validation to allow at most 10% false nominations, "
                  "then applied once to test. Targets were removed artificially; this is a stress test, not a natural absence rate.")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def chart_precursor(pre, out):
    a = pre["ppm_error"].abs().clip(lower=1e-4)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bins = np.logspace(-4, 4, 81)
    ax.hist(a, bins=bins, color="#2a78d6", edgecolor=SURFACE, linewidth=0.5)
    ax.set_xscale("log")
    for v, lab in ((0.01, "0.01 ppm"), (10, "10 ppm window")):
        ax.axvline(v, color=MUTED, linestyle="--", linewidth=1.2)
        ax.text(v * 1.15, ax.get_ylim()[1] * 0.92, lab, fontsize=9, color=MUTED)
    lt = 100 * (a < 0.01).mean()
    gt = 100 * (a > 10).mean()
    ax.set_xlabel("|precursor mass error| against the annotated structure, ppm (log scale)")
    ax.set_ylabel("spectra")
    ax.set_title(f"{lt:.0f}% of library precursors sit within 0.01 ppm; {gt:.0f}% are more than 10 ppm off",
                 loc="left", fontsize=12, color=INK)
    footnote(fig, f"MassSpecGym formula split seed 1, training and validation spectra (n = {len(a):,}). Values below 1e-4 ppm are drawn at "
                  "1e-4. Errors this small are unlikely to be instrument measurements; they suggest precursors recomputed from the annotation.")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", type=Path, required=True)
    ap.add_argument("--precursor", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(args.analysis / "metrics.csv")
    sizes = pd.read_csv(args.analysis / "pool-sizes.csv", index_col=0)
    chart_recall(metrics, args.out / "01-recall-by-method.png")
    chart_pool_size(metrics, sizes, args.out / "02-pool-size-stress.png")
    chart_ties(metrics, args.out / "03-tie-and-duplicate-rules.png")
    if (args.analysis / "risk-coverage-curves.json").exists():
        chart_abstention(json.loads((args.analysis / "risk-coverage-curves.json").read_text()),
                         pd.read_csv(args.analysis / "abstention.csv"), args.out / "04-decline-to-nominate.png")
    chart_precursor(pd.read_csv(args.precursor), args.out / "05-precursor-mass-error.png")
    print(sorted(p.name for p in args.out.glob("*.png")))


if __name__ == "__main__":
    main()
