"""Fig. 5 (fig:da_benefit): gauge-wise ΔKGE (experiment minus exp10) per model and
experiment at ~1 km (top), and the share of gauges with higher or lower KGE than in
exp10 (bottom, strict sign without tolerance band), one figure per basin.

In the benchmarking code this figure was written as
<basin>_multi_model_performance_overlay_1km.png and then renamed for the manuscript;
here it is saved directly under the manuscript name.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{Po,Rhine,Tugela}_multi_model_delta_overlay_1km_.png/.pdf
         output/tables/winrate_vs_exp10.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import itertools

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

from wrr2.data import load_performance, paired_delta, RES_GROUP
from wrr2.paths import TABLE_DIR
from wrr2.regions import BASINS, BASIN_MODELS, sort_experiments
from wrr2.style import (model_color, model_label, MODEL_LETTER, WINRATE_COLORS_BW_HATCHED as WR,
                        WINRATE_HATCH, HATCH_COLOR, draw_family_boundaries, tighten_category_edges,
                        add_experiment_labels, savefig)

BASELINE = 'exp10'
# exp33 is drawn as an empty slot in the Tugela so that the axes match the other basins
FORCE_EXPERIMENTS = {'Tugela': ['exp33']}


def plot_basin(perf, region, models, force_experiments=None, figsize=(15, 11.0),
               height_ratios=(4.8, 2.4), winrate_legend_y=-0.50, bottom_pad=0.55, ytick_step=25):
    frames = []
    for m in models:
        d = paired_delta(perf, baseline=BASELINE, region=region, model=m)
        if d.empty:
            continue
        frames.append(d.assign(model=m))
    df = pd.concat(frames, ignore_index=True)

    available = df['experiment'].unique().tolist()
    order = sort_experiments(list(set(available + (force_experiments or []))))
    colors = {m: model_color(m) for m in models}

    fig, (ax, axw) = plt.subplots(2, 1, sharex=True, figsize=figsize,
                                  gridspec_kw={'height_ratios': list(height_ratios)})

    # top: ΔKGE distribution per model
    sns.boxplot(data=df, x='experiment', y='delta_kge', hue='model', hue_order=models,
                order=order, showfliers=False, ax=ax,
                palette=[colors[m] for m in models], dodge=True, legend=False)
    sns.stripplot(data=df, x='experiment', y='delta_kge', hue='model', hue_order=models,
                  order=order, ax=ax, dodge=True, size=2.5, alpha=0.25,
                  palette=[colors[m] for m in models], legend=False)
    ax.axhline(0, ls='--', c='gray', alpha=0.7, zorder=2.5)
    for t in ax.get_xticklabels():
        t.set_rotation(45)
        t.set_ha('right')
    ax.set_ylabel('ΔKGE (experiment – baseline)')
    ax.set_ylim(-2, 1)
    ax.set_title(f'ΔKGE vs baseline – {region} ({RES_GROUP})')
    draw_family_boundaries(ax, order, zorder=4)
    add_experiment_labels(ax, order)
    h_models = [mpatches.Patch(facecolor=colors[m], label=model_label(m)) for m in models]
    leg_models = ax.legend(handles=h_models, ncol=2, frameon=False, loc='lower right',
                           bbox_to_anchor=(1.00, 0.02))
    ax.add_artist(leg_models)
    # font of the top-panel tick labels, reused for the model letters
    xticks_top = ax.get_xticklabels()
    if xticks_top:
        tick_fp = xticks_top[0].get_fontproperties()
    else:
        tick_fp = FontProperties(family=mpl.rcParams.get('font.family'),
                                 size=mpl.rcParams.get('font.size'),
                                 weight=mpl.rcParams.get('font.weight', 'normal'))

    # bottom: share of gauges better / same / worse than the baseline (strict sign)
    stats = []
    for (e, m), v in df.groupby(['experiment', 'model'])['delta_kge']:
        n = v.size
        if n == 0:
            continue
        stats.append({'experiment': e, 'model': m,
                      'worse': 100.0 * (v < 0).sum() / n,
                      'same': 100.0 * (v == 0).sum() / n,
                      'better': 100.0 * (v > 0).sum() / n,
                      'n_gauges': n})
    win = pd.DataFrame(stats)
    idx = pd.MultiIndex.from_product([order, models], names=['experiment', 'model'])
    win_full = win.set_index(['experiment', 'model']).reindex(idx).fillna(0.0).reset_index()

    x0 = np.arange(len(order))
    barw = 0.8 / max(len(models), 1)
    for j, m in enumerate(models):
        sub = win_full[win_full['model'] == m].set_index('experiment').reindex(order).reset_index()
        xs = x0 - 0.4 + (j + 0.5) * barw
        b_worse = axw.bar(xs, sub['worse'], width=barw, color=WR['worse'],
                          hatch=WINRATE_HATCH['worse'], edgecolor=HATCH_COLOR)
        b_same = axw.bar(xs, sub['same'], width=barw, bottom=sub['worse'], color=WR['same'],
                         hatch=WINRATE_HATCH['same'], edgecolor=HATCH_COLOR)
        b_better = axw.bar(xs, sub['better'], width=barw, bottom=sub['worse'] + sub['same'],
                           color=WR['better'], hatch=WINRATE_HATCH['better'], edgecolor=HATCH_COLOR)
        for r in itertools.chain.from_iterable((b_worse, b_same, b_better)):
            x, y = r.get_xy()
            axw.add_patch(Rectangle((x, y), r.get_width(), r.get_height(), fill=False,
                                    edgecolor='#333333', linewidth=1.2, zorder=4))
        # model letters above the bars that have data
        for exp, x in zip(order, xs):
            row = sub[sub['experiment'] == exp]
            if (row['worse'].iloc[0] + row['same'].iloc[0] + row['better'].iloc[0]) > 0:
                axw.text(x, 115, MODEL_LETTER.get(m, m[0].upper()), ha='center', va='bottom',
                         color='black', fontproperties=tick_fp, fontweight=None, fontsize=None,
                         clip_on=False, zorder=5)

    axw.set_xticks(x0, order)
    for t in axw.get_xticklabels():
        t.set_rotation(45)
        t.set_ha('right')
    draw_family_boundaries(axw, order, zorder=3)
    axw.set_ylim(0, 112)
    axw.set_ylabel('% gauges')
    axw.set_yticks(np.arange(0, 101, int(ytick_step)))

    wr_handles = [mpatches.Patch(facecolor=WR['worse'], hatch=WINRATE_HATCH['worse'],
                                 edgecolor=HATCH_COLOR, label='worse'),
                  mpatches.Patch(facecolor=WR['better'], hatch=WINRATE_HATCH['better'],
                                 edgecolor=HATCH_COLOR, label='better')]
    if (win_full['same'] > 0).any():
        wr_handles.insert(1, mpatches.Patch(facecolor=WR['same'], hatch=WINRATE_HATCH['same'],
                                            edgecolor=HATCH_COLOR, label='no change'))
    wr_legend = axw.legend(handles=wr_handles, ncol=len(wr_handles), frameon=False,
                           loc='upper center', bbox_to_anchor=(0.5, winrate_legend_y))
    fig.add_artist(wr_legend)

    tighten_category_edges([ax, axw], n_cats=len(order), pad=0.5)
    fig.subplots_adjust(hspace=0.40, bottom=bottom_pad)

    medians = df.groupby(['experiment', 'model'])['delta_kge'].median().rename('median_dkge')
    return fig, win.merge(medians.reset_index(), on=['experiment', 'model'])


perf = load_performance()
tables = []
for basin in BASINS:
    fig, win = plot_basin(perf, basin, BASIN_MODELS[basin], FORCE_EXPERIMENTS.get(basin))
    savefig(fig, f'{basin}_multi_model_delta_overlay_1km_')
    tables.append(win.assign(region=basin))
table = pd.concat(tables, ignore_index=True)
table = table[['region', 'model', 'experiment', 'n_gauges', 'median_dkge', 'better', 'same', 'worse']]
table.round(3).to_csv(TABLE_DIR / 'winrate_vs_exp10.csv', index=False)
print('Saved output/tables/winrate_vs_exp10.csv')
