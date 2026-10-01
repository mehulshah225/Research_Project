"""Figure 3 of the paper: circuit-level comparison on the seven largest
completed instances (PyZX optimization of both realizations > 10 minutes).

Reads results/comparisons/comparison_extended_timeout.csv. Panel (c) reports
qubit counts with the decomposition workspace reused: export_qasm.py allocates
fresh workspace for every decomposed gate, so its circuits are much wider than
necessary; with reuse a circuit needs n + 3 qubits plus the workspace of its
widest gate. The counts are obtained by running export_qasm.py itself.
Usage: python make_fig3.py [fig3.png]
"""
import os, sys, importlib.util
import pandas as pd
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Wong colourblind-safe palette, as used in Figs 1-2
BLUE = '#0072B2'
VERM = '#D55E00'
GREY = '#999999'
SKY = '#56B4E9'
ORANGE = '#E69F00'

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 7,
    'axes.labelsize': 7,
    'axes.titlesize': 7,
    'xtick.labelsize': 6,
    'ytick.labelsize': 6,
    'legend.fontsize': 6,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6,
    'lines.linewidth': 0.9,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

MM = 1 / 25.4


def reuse_qubits(path, ex, cap):
    rows = ex.load(path)
    n = next(int(l.split()[1]) for l in open(path) if l.startswith('.i '))
    ex.build(rows, n, decompose=True)
    em = cap['e']
    return n + 3 + getattr(em, '_peak', 0)


def load_big7():
    spec = importlib.util.spec_from_file_location('ex', 'export_qasm.py')
    ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
    cap = {}; om = ex.Emitter.mcx; oi = ex.Emitter.__init__
    def mcx(self, c, t):
        k = len(list(c)); self._peak = max(getattr(self, '_peak', 0), max(0, k - 2))
        return om(self, c, t)
    def init(self, *a, **k):
        oi(self, *a, **k); cap['e'] = self
    ex.Emitter.mcx = mcx; ex.Emitter.__init__ = init
    E = os.listdir('results/esop'); F = os.listdir('results/final_parser')
    d = pd.read_csv('results/comparisons/comparison_extended_timeout.csv')
    d = d[d.baseline_pyzx.notna() & d.factorized_pyzx.notna()]   # both completed
    rows = []
    for _, x in d.iterrows():
        fn = x.function
        qb = reuse_qubits('results/esop/' + [a for a in E if a.split('.')[0] == fn][0], ex, cap)
        qf = reuse_qubits('results/final_parser/' + [a for a in F if a.split('.')[0] == fn][0], ex, cap)
        rows.append((fn, x.decomposed_baseline, x.baseline_pyzx, x.decomposed_factorized,
                     x.factorized_pyzx, qb, qf, x.baseline_pyzx_seconds, x.factorized_pyzx_seconds))
    order = ['shor_modexp_2_mod21_bit0', 'shor_modexp_2_mod21_bit1', 'max46_d_100', 'life_d_100',
             'ryy6_198', 'majority9', 'shor_modexp_5_mod33_bit0']
    rows.sort(key=lambda r: order.index(r[0]) if r[0] in order else len(order))
    return rows


BIG7 = load_big7()
def panel_label(ax, letter, dx=-0.34, dy=1.08):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=8,
            fontweight='bold', va='top', ha='left')


def figure3(path):
    fig, axes = plt.subplots(1, 4, figsize=(180 * MM, 48 * MM))

    # ---- a: slopegraph across the four stages
    ax = axes[0]
    xs = [0, 1]
    for row in BIG7:
        _, A, B, C, D = row[0], row[1], row[2], row[3], row[4]
        ax.plot(xs, [A, B], color=GREY, marker='o', ms=2, alpha=0.85)
        ax.plot([2, 3], [C, D], color=BLUE, marker='o', ms=2, alpha=0.9)
    ax.set_yscale('log')
    ax.set_yticks([2000, 3000, 5000, 8000])
    ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(['A', 'B', 'C', 'D'])
    ax.set_ylabel('T-count')
    ax.set_xlabel('synthesis stage')
    ax.plot([], [], color=GREY, marker='o', ms=2, label='conventional')
    ax.plot([], [], color=BLUE, marker='o', ms=2, label='factorized')
    ax.legend(frameon=False, loc='lower left')
    panel_label(ax, 'a')

    # ---- b: ratio of optimized to unoptimized
    ax = axes[1]
    ba = [r[2] / r[1] for r in BIG7]
    dc = [r[4] / r[3] for r in BIG7]
    x1 = np.full(len(ba), 0.0) + np.linspace(-0.13, 0.13, len(ba))
    x2 = np.full(len(dc), 1.0) + np.linspace(-0.13, 0.13, len(dc))
    ax.scatter(x1, ba, s=9, color=GREY, zorder=3, label='conventional (B/A)')
    ax.scatter(x2, dc, s=9, color=BLUE, zorder=3, label='factorized (D/C)')
    ax.axhline(4 / 7, color=VERM, lw=0.7, ls='--', zorder=2)
    ax.text(1.42, 4 / 7, '4/7', color=VERM, fontsize=6, va='center')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['B/A', 'D/C'])
    ax.set_ylabel('optimized / unoptimized')
    ax.set_xlim(-0.4, 1.6)
    ax.set_ylim(0.48, 0.64)
    panel_label(ax, 'b')

    # ---- c: qubit counts with decomposition workspace reused
    ax = axes[2]
    qb = [r[5] for r in BIG7]
    qf = [r[6] for r in BIG7]
    lim = [15, 35]
    ax.plot(lim, lim, color=GREY, lw=0.7, ls='--', zorder=1)
    ax.scatter(qb, qf, s=11, color=BLUE, zorder=3)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel('conventional qubits')
    ax.set_ylabel('factorized qubits')
    ax.set_xticks([15, 20, 25, 30, 35])
    ax.set_yticks([15, 20, 25, 30, 35])
    panel_label(ax, 'c')

    # ---- d: observed vs predicted speed-up
    ax = axes[3]
    pred = [(r[1] / r[3]) ** 2.34 for r in BIG7]
    obs = [r[7] / r[8] for r in BIG7]
    lim = [1.0, 10.0]
    ax.plot(lim, lim, color=GREY, lw=0.7, ls='--', zorder=1)
    ax.scatter(pred, obs, s=11, color=BLUE, zorder=3)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel('predicted speed-up')
    ax.set_ylabel('observed speed-up')
    for t in ([1, 2, 5, 10]):
        pass
    ax.set_xticks([1, 2, 5, 10])
    ax.set_yticks([1, 2, 5, 10])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    panel_label(ax, 'd')

    fig.tight_layout(pad=0.6, w_pad=1.6)
    fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('wrote', path)



if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'fig3.png'
    figure3(out)
    for r in BIG7:
        print(f"  {r[0]:26s} qubits (workspace reused) {r[5]} -> {r[6]}")
