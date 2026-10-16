"""Fig. 2 (fig:model_performance_regions): distribution of daily KGE across gauges for
every model and experiment at ~1 km, one panel per basin.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{Po,Rhine,Tugela}_multi_model_performance_overlay_1km.png/.pdf

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import seaborn as sns

from wrr2.data import load_performance, RES_GROUP
from wrr2.regions import BASINS, BASIN_MODELS, sort_experiments
from wrr2.style import (model_color, model_label, draw_family_boundaries, tighten_category_edges,
                        add_experiment_labels, savefig)

THRESHOLD = -0.41  # KGE of the mean-flow benchmark


def plot_basin(perf, region, models):
    df = perf[perf['region'] == region].copy()
    models = [m for m in models if m in df['model'].unique()]
    df = df[df['model'].isin(models)]
    order = sort_experiments(df['experiment'].unique().tolist())
    colors = {m: model_color(m) for m in models}

    fig, ax = plt.subplots(1, 1, figsize=(14, 5))
    sns.boxplot(data=df, x='experiment', y='kge', hue='model', hue_order=models,
                order=order, showfliers=False, ax=ax,
                palette=[colors[m] for m in models], dodge=True, legend=False)
    sns.stripplot(data=df, x='experiment', y='kge', hue='model', hue_order=models,
                  order=order, ax=ax, dodge=True, size=2.5, alpha=0.25,
                  palette=[colors[m] for m in models], legend=False)
    ax.axhline(THRESHOLD, ls='--', c='gray', alpha=0.7, zorder=2.5)
    for t in ax.get_xticklabels():
        t.set_rotation(45)
        t.set_ha('right')
    ax.set_ylabel('KGE')
    ax.set_ylim(-1, 1)
    ax.set_title(f'KGE Performance across models – {region} ({RES_GROUP})')
    draw_family_boundaries(ax, order, zorder=4)
    add_experiment_labels(ax, order)

    handles = [mpatches.Patch(facecolor=colors[m], label=model_label(m)) for m in models]
    leg = ax.legend(handles=handles, ncol=2, frameon=False, loc='lower right', bbox_to_anchor=(1.00, 0.02))
    ax.add_artist(leg)
    tighten_category_edges([ax], n_cats=len(order), pad=0.5)
    fig.subplots_adjust(bottom=0.20)
    return fig


perf = load_performance()
for basin in BASINS:
    savefig(plot_basin(perf, basin, BASIN_MODELS[basin]), f'{basin}_multi_model_performance_overlay_1km')
