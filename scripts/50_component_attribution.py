"""Figs. 7, B1 and B2 (fig:po_component_attribute_exp44_vs_exp10,
fig:rhine_component_attribute_exp44_vs_exp10, fig:tugela_component_attribute_exp44_vs_exp10):
gauge-wise ΔKGE (exp44 minus exp10) against the change in each KGE component
(Δr, Δα*, Δβ*, with α* and β* = exp(-|ln x|)), with OLS fits.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{basin}_{model}_scatter_dkge_vs_exp10_1km.png/.pdf
         output/tables/component_attribution_exp44_vs_exp10.csv  (the in-panel statistics)

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import linregress

from wrr2.data import load_performance, paired_delta, closeness_to_one, pvalue_stars, RES_GROUP
from wrr2.paths import TABLE_DIR
from wrr2.regions import BASINS, JOINT_MODELS
from wrr2.style import model_color, model_label, savefig

BASELINE = 'exp10'
EXPERIMENT = 'exp44'
XLIMITS = {'Δr': (-0.7, 0.7), 'Δα*': (-0.7, 0.7), 'Δβ*': (-0.7, 0.7)}
# ΔKGE axis range; the Rhine panels were drawn with a wider range to show the CLM losses
YLIMITS = {'Po': (-1.5, 1), 'Rhine': (-2, 1), 'Tugela': (-1.5, 1)}
P_ALPHA = 0.05


def component_scatter(perf, region, model, figsize=(12, 3.8)):
    d = paired_delta(perf, baseline=BASELINE, experiments=[EXPERIMENT], region=region, model=model)
    if d.empty:
        return None, []
    keys = ['model', 'region', 'resolution', 'station']
    comp = ['kge_r', 'kge_alpha', 'kge_beta']
    base = perf[(perf['experiment'] == BASELINE) & (perf['region'] == region)][keys + comp].rename(
        columns={'kge_r': 'r_b', 'kge_alpha': 'a_b', 'kge_beta': 'b_b'})
    exp = perf[(perf['experiment'] == EXPERIMENT) & (perf['region'] == region)][keys + comp].rename(
        columns={'kge_r': 'r_e', 'kge_alpha': 'a_e', 'kge_beta': 'b_e'})
    m = d.merge(base, on=keys, how='inner').merge(exp, on=keys, how='inner')
    if m.empty:
        return None, []

    m['d_r'] = m['r_e'] - m['r_b']
    m['d_a'] = closeness_to_one(m['a_e']) - closeness_to_one(m['a_b'])
    m['d_b'] = closeness_to_one(m['b_e']) - closeness_to_one(m['b_b'])
    labels = ['Δr', 'Δα*', 'Δβ*']
    y = m['delta_kge'].to_numpy()
    comps = [m['d_r'].to_numpy(), m['d_a'].to_numpy(), m['d_b'].to_numpy()]

    fig, axes = plt.subplots(1, 3, figsize=figsize, sharey=True)
    color = model_color(model)
    stats = []
    for ax, x, lab in zip(axes, comps, labels):
        ax.scatter(x, y, s=16, alpha=0.5, color=color)
        mask = np.isfinite(x) & np.isfinite(y)
        n = int(mask.sum())
        if n > 5 and np.nanstd(x[mask]) > 0:
            slope, intercept, r, p, _ = linregress(x[mask], y[mask])
            xs = np.linspace(np.nanmin(x[mask]), np.nanmax(x[mask]), 50)
            ax.plot(xs, intercept + slope * xs, c=color, lw=2, alpha=0.8)
            stars = pvalue_stars(p)
            med = float(np.nanmedian(y[mask]))
            ax.text(0.02, 0.98, f'N={n}\nmed ΔKGE={med:.2f}\nslope={slope:.2f}\nr={r:.2f}\np={p:.2g} {stars}',
                    transform=ax.transAxes, va='top', ha='left',
                    bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'),
                    color='black' if (np.isfinite(p) and p < P_ALPHA) else 'gray')
            stats.append({'basin': region, 'model': model, 'component': lab, 'n': n,
                          'median_dkge': med, 'slope': slope, 'pearson_r': r, 'p': p, 'stars': stars})
        ax.axhline(0, ls='--', c='gray')
        ax.set_xlabel(lab)
        ax.set_xlim(*XLIMITS[lab])
        ax.set_ylim(*YLIMITS[region])
    axes[0].set_ylabel('ΔKGE')
    fig.suptitle(f'{model_label(model)} – {region} – {EXPERIMENT} vs {BASELINE} ({RES_GROUP})')
    fig.tight_layout()
    return fig, stats


perf = load_performance()
rows = []
for basin in BASINS:
    for model in JOINT_MODELS[basin]:
        fig, stats = component_scatter(perf, basin, model)
        if fig is None:
            print(f'{model} {basin}: no paired gauges for {EXPERIMENT} vs {BASELINE}, skipped')
            continue
        savefig(fig, f'{basin}_{model}_scatter_dkge_vs_{BASELINE}_1km')
        rows.extend(stats)
pd.DataFrame(rows).to_csv(TABLE_DIR / 'component_attribution_exp44_vs_exp10.csv', index=False)
print('Saved output/tables/component_attribution_exp44_vs_exp10.csv')
