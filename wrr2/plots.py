"""Plot functions used by more than one figure script.

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.stats import wilcoxon

from wrr2.data import paired_delta, pvalue_stars, RES_GROUP, AGGREGATION
from wrr2.regions import sort_experiments, experiment_family
from wrr2.style import model_color, model_label


def median_kge_lines(perf, region, delta=False, baseline='exp10', figsize=(12, 4)):
    """Basin-median KGE (or ΔKGE against `baseline`) per model across experiments."""
    df = perf[perf['region'] == region].copy()
    present = df['experiment'].dropna().astype(str).unique().tolist()
    exps = sort_experiments(present)
    df = df[df['experiment'].isin(exps)].copy()

    if delta:
        base_tab = (df[df['experiment'] == baseline][['model', 'station', 'kge']]
                    .rename(columns={'kge': 'kge_base'}))
        df = df.merge(base_tab, on=['model', 'station'], how='left')
        df['kge'] = df['kge'] - df['kge_base']

    med = df.groupby(['model', 'experiment'], observed=True)['kge'].median().reset_index()
    med['experiment'] = med['experiment'].astype(str)
    pos = {e: i for i, e in enumerate(exps)}
    med['xpos'] = med['experiment'].map(pos)
    med = med.sort_values(['model', 'xpos'])

    fig, ax = plt.subplots(figsize=figsize)
    for m, sub in med.groupby('model', observed=True):
        sub = sub.dropna(subset=['xpos'])
        ax.plot(sub['xpos'], sub['kge'], marker='o', lw=2, label=model_label(m), color=model_color(m))

    ax.set_xticks(range(len(exps)))
    ax.set_xticklabels(exps, rotation=45, ha='right')
    for i in range(len(exps) - 1):
        if experiment_family(exps[i]) != experiment_family(exps[i + 1]):
            ax.axvline(i + 0.5, ls='--', color='gray', alpha=0.35)
    ax.set_ylim(-1, 1)
    ax.axhline(0 if delta else -0.41, ls='--', c='gray', alpha=0.7)
    ax.set_ylabel('Median ΔKGE' if delta else 'Median KGE')
    ax.legend(ncol=3, frameon=False)
    ax.set_title(f"{region} ({RES_GROUP}) – {'ΔKGE vs ' + baseline if delta else 'KGE'}")
    fig.tight_layout()
    return fig, med


def scatter_stats(x, y, band=0.10):
    """Statistics printed in the 1:1 scatter panels: N, median ΔKGE, Pearson r,
    Wilcoxon p and the shares of better/same/worse gauges using the ±band tolerance."""
    mask = np.isfinite(x) & np.isfinite(y)
    xx, yy = x[mask], y[mask]
    n = int(mask.sum())
    diff = yy - xx
    med = float(np.nanmedian(diff)) if n else np.nan
    r = float(np.corrcoef(xx, yy)[0, 1]) if n > 1 else np.nan
    p = np.nan
    if n >= 10:
        try:
            _, p = wilcoxon(diff, zero_method='wilcox', alternative='two-sided')
        except Exception:
            p = np.nan
    better = (diff > band).sum()
    same = (np.abs(diff) <= band).sum()
    worse = (diff < -band).sum()
    nn = n if n else 1
    return {'n': n, 'median_dkge': med, 'pearson_r': r, 'wilcoxon_p': p, 'stars': pvalue_stars(p),
            'pct_better': 100.0 * better / nn, 'pct_same': 100.0 * same / nn,
            'pct_worse': 100.0 * worse / nn}


def baseline_scatter(perf, baseline, experiment, region, model, gridsize=35, band=0.10,
                     band_color='grey', band_alpha=0.15):
    """Gauge-wise 1:1 hexbin of KGE in `experiment` against KGE in `baseline`.
    Returns (figure, statistics) or (None, None) when no gauges are paired."""
    d = paired_delta(perf, baseline=baseline, experiments=[experiment], region=region, model=model)
    if d.empty:
        return None, None
    d = d[d['experiment'] == experiment]
    x = d['kge_base'].to_numpy()
    y = d['kge_cur'].to_numpy()

    # number of colour levels per basin (capped by the largest hexagon count)
    region_color_map = {'Po': 7, 'Rhine': 15, 'Tugela': 3}

    fig, ax = plt.subplots(figsize=(6, 6))
    lim = (-1, 1)
    hb = ax.hexbin(x, y, gridsize=gridsize, mincnt=1, extent=(*lim, *lim))
    counts = hb.get_array()
    maxc = int(np.nanmax(counts)) if counts.size else 1
    n_colors = max(1, min(maxc, region_color_map.get(region, maxc)))
    cmap = plt.get_cmap('viridis', n_colors)
    bounds = np.arange(0.5, maxc + 1.5, 1)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    hb.set_cmap(cmap)
    hb.set_norm(norm)
    cax = make_axes_locatable(ax).append_axes('right', size='5%', pad=0.1)
    cb = fig.colorbar(hb, cax=cax, ticks=np.arange(1, n_colors + 1))
    cb.set_label('# gauges')

    ax.plot(lim, lim, 'k--', lw=1)
    xs = np.linspace(lim[0], lim[1], 200)
    ax.plot(xs, xs + band, ls=':', c='gray', lw=1)
    ax.plot(xs, xs - band, ls=':', c='gray', lw=1)
    ax.fill_between(xs, xs - band, xs + band, color=band_color, alpha=band_alpha, zorder=0)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel(f'KGE {baseline}')
    ax.set_ylabel(f'KGE {experiment}')

    s = scatter_stats(x, y, band=band)
    ax.set_title(f'{model_label(model)} – {region} ({RES_GROUP}, {AGGREGATION})')
    ax.text(0.02, 0.98,
            f"N={s['n']}\nmed ΔKGE={s['median_dkge']:.2f}\nr={s['pearson_r']:.2f}\np={s['wilcoxon_p']:.2g} {s['stars']}",
            transform=ax.transAxes, va='top', ha='left',
            bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'))
    ax.text(0.98, 0.02,
            f"↑ better: {s['pct_better']:.0f}%\n≈ same (±{band:.2f}): {s['pct_same']:.0f}%\n↓ worse: {s['pct_worse']:.0f}%",
            transform=ax.transAxes, va='bottom', ha='right',
            bbox=dict(facecolor='white', alpha=0.85, edgecolor='none'), zorder=5)
    return fig, s
