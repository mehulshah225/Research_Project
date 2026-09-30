"""Figure 2 of the paper: resource reductions across the 64 Boolean functions.

Reads results.xlsx (produced by run_all.py) and writes fig2.png.
Usage:  python make_fig2.py [results.xlsx] [fig2.png]
"""
import re
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = sys.argv[1] if len(sys.argv) > 1 else "results.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "fig2.png"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": 8.5,
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "xtick.major.size": 3, "ytick.major.size": 3,
})
BLUE, GREY, VERM = "#0072B2", "#999999", "#D55E00"
NOTE, SHADE = "#555555", "#F2F2F2"

def group(name):
    if name.startswith("f_100"):
        return "random"
    if (name.startswith("shor_modexp") or re.match(r"adder[0-9]", name)
            or name in ("majority7", "majority9", "majority11")):
        return "oracle"
    return "structured"

mas = pd.read_excel(SRC, "Maslov Cost")
tco = pd.read_excel(SRC, "T-Count")
res = pd.read_excel(SRC, "Resources")
d = (mas.merge(tco[["Function", "ESOP T", "Final T"]], on="Function")
        .merge(res[["Function", "ESOP Max Controls", "Final Max Controls"]], on="Function"))
d["g"] = d.Function.map(group)
HL = "con1f1_100"                                   # the worked example of Fig. 1

rng = np.random.default_rng(7)                      # fixed seed: reproducible jitter
d["jx"] = np.exp(rng.uniform(-0.06, 0.06, len(d)))  # small multiplicative jitter

fig, ax = plt.subplots(2, 2, figsize=(7.2, 4.9))
plt.subplots_adjust(wspace=0.32, hspace=0.42)
STYLE = {  # structured, random, oracle
    "structured": dict(c=BLUE, s=11, zorder=3, lw=0),
    "random":     dict(c=GREY, s=11, zorder=3, lw=0),
    "oracle":     dict(c=VERM, s=30, zorder=4, edgecolors="#6b2a00", linewidths=0.6),
}
LABEL = {"structured": "structured benchmarks", "random": "random 100-variable",
         "oracle": "algorithm oracles"}

def base(a, lo, hi):
    a.plot([lo, hi], [lo, hi], ls=(0, (4, 3)), c="#888888", lw=0.9, zorder=2)
    a.fill_between([lo, hi], [lo, lo], [lo, hi], color=SHADE, zorder=0, lw=0)
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlim(lo, hi); a.set_ylim(lo, hi)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)

def highlight(a, x, y, dx, dy):
    a.scatter([x], [y], s=150, facecolors="none", edgecolors="black", lw=1.0, zorder=6)
    a.annotate("con1f1", xy=(x, y), xytext=(x * dx, y * dy), fontweight="bold",
               fontsize=8.5, ha="left", va="center",
               arrowprops=dict(arrowstyle="-", lw=1.0, color="black", shrinkA=0, shrinkB=7))

def title(a, letter, text):
    a.text(-0.13, 1.07, letter, transform=a.transAxes, fontweight="bold", fontsize=10.5)
    a.text(-0.06, 1.07, text, transform=a.transAxes, fontweight="bold", fontsize=10.5)

# (a) quantum cost
a = ax[0, 0]; base(a, 1, 1e8)
for g in ("structured", "random", "oracle"):
    s = d[d.g == g]
    a.scatter(s["ESOP Cost"], s["Final Cost"], label=LABEL[g], **STYLE[g])
h = d[d.Function == HL].iloc[0]
highlight(a, h["ESOP Cost"], h["Final Cost"], 3.5, 0.03)
a.set_xticks([1, 1e2, 1e4, 1e6, 1e8]); a.set_yticks([1, 1e2, 1e4, 1e6, 1e8]); a.minorticks_off()
a.set_xlabel("Conventional quantum cost", labelpad=1)
a.set_ylabel("Factorized\nquantum cost")
n_up = int((d["Final Cost"] > d["ESOP Cost"]).sum())
a.text(0.05, 0.93, f"$n$ = {len(d)}; " + ("no function\nincreased in cost" if n_up == 0
       else f"{n_up} increased"), transform=a.transAxes, va="top", color=NOTE)
a.legend(loc="lower right", frameon=False, handletextpad=0.1, borderaxespad=0.0,
         bbox_to_anchor=(1.04, 0.0), fontsize=7.5, labelspacing=0.35)
title(a, "a", "Quantum cost")

# (b) T-count (functions with non-zero conventional T-count)
a = ax[0, 1]; base(a, 1, 1e6)
t = d[d["ESOP T"].fillna(0) > 0]
for g in ("structured", "random", "oracle"):
    s = t[t.g == g]
    a.scatter(s["ESOP T"], s["Final T"], **STYLE[g])
h = t[t.Function == HL].iloc[0]
highlight(a, h["ESOP T"], h["Final T"], 3.2, 0.02)
a.set_xticks([1, 1e2, 1e4, 1e6]); a.set_yticks([1, 1e2, 1e4, 1e6]); a.minorticks_off()
a.set_xlabel("Conventional T-count", labelpad=1); a.set_ylabel("Factorized\nT-count")
a.text(0.05, 0.93, f"$n$ = {len(t)}; {len(d) - len(t)} affine functions\nomitted (zero T-count in both)",
       transform=a.transAxes, va="top", color=NOTE)
title(a, "b", "T-count")

# (c) quantum-cost reduction against input count
a = ax[1, 0]
for g in ("structured", "oracle", "random"):
    s = d[d.g == g]
    a.scatter(s.Inputs * s.jx, s["Final Cost Saving (%)"], c=STYLE[g]["c"], s=11, lw=0, zorder=3)
med = d["Final Cost Saving (%)"].median()
a.axhline(med, ls=(0, (4, 3)), c="#888888", lw=0.9, zorder=2)
a.text(0.99, med + 2.5, f"median {med:.1f}%", transform=a.get_yaxis_transform(),
       ha="right", va="bottom", color=NOTE)
a.set_xscale("log"); a.set_xlim(2.4, 140); a.set_ylim(0, 100)
a.set_xticks([3, 10, 30, 100]); a.set_xticklabels(["3", "10", "30", "100"])
a.minorticks_off(); a.set_yticks([0, 25, 50, 75, 100])
a.set_xlabel("Input variables", labelpad=1); a.set_ylabel("Quantum-cost\nreduction (%)")
for s in ("top", "right"):
    a.spines[s].set_visible(False)
title(a, "c", "Scalability")

# (d) widest gate (controls); equal jitter on both axes keeps each point's
#     position relative to the equality line
a = ax[1, 1]; base(a, 1, 100)
for g in ("structured", "random", "oracle"):
    s = d[d.g == g]
    a.scatter(s["ESOP Max Controls"] * s.jx, s["Final Max Controls"] * s.jx, **STYLE[g])
h = d[d.Function == HL].iloc[0]
highlight(a, h["ESOP Max Controls"] * h.jx, h["Final Max Controls"] * h.jx, 1.45, 0.42)
a.set_xticks([1, 3, 10, 30, 100]); a.set_xticklabels(["1", "3", "10", "30", "100"])
a.set_yticks([1, 3, 10, 30, 100]); a.set_yticklabels(["1", "3", "10", "30", "100"])
a.minorticks_off()
fell = int((d["Final Max Controls"] < d["ESOP Max Controls"]).sum())
rose = int((d["Final Max Controls"] > d["ESOP Max Controls"]).sum())
a.text(0.05, 0.93, f"largest gate fell for {fell} of {len(d)},\nrose for " +
       ("none" if rose == 0 else str(rose)), transform=a.transAxes, va="top", color=NOTE)
gates = res.set_index("Function")
grew = int((gates["Final Gates"] > gates["ESOP Gates"]).sum())
a.text(0.98, 0.07, f"gate count rose\nfor {grew} of {len(d)}", transform=a.transAxes,
       ha="right", va="bottom", color=NOTE)
a.set_xlabel("Conventional maximum gate size (controls)", labelpad=1)
a.set_ylabel("Factorized maximum\ngate size")
title(a, "d", "Gate arity")

fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"wrote {OUT}: median quantum-cost reduction {med:.1f}%, "
      f"{n_up} increases, gate fell {fell}/rose {rose}, gate count rose {grew}")
