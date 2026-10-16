"""Fig. 8 (fig:median_normalised_kge): radar charts of the basin-median KGE components
r, α* and β* (α*, β* = exp(-|ln x|) of the median α and β) for each model and experiment.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{Po,Rhine,Tugela}_radar_norm_1km.png/.pdf
         output/tables/median_kge_components.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from wrr2.data import load_performance, closeness_to_one, RES_GROUP, AGGREGATION
from wrr2.paths import TABLE_DIR
from wrr2.regions import BASINS, EXP_ORDER
from wrr2.style import model_color, model_label, sort_models, savefig


def component_table(perf, experiments, region):
    """Median r, α and β per experiment and model, and their normalised forms."""
    df = perf[(perf['region'] == region) & (perf['experiment'].isin(experiments))].copy()
    tab = (df.groupby(['experiment', 'model'], observed=True)
             .agg({'kge_r': 'median', 'kge_alpha': 'median', 'kge_beta': 'median'}).reset_index())
    tab['experiment'] = pd.Categorical(tab['experiment'], categories=experiments, ordered=True)
    tab = tab.sort_values(['experiment', 'model'])
    tab['r'] = tab['kge_r'].clip(0, 1)
    tab['α'] = closeness_to_one(tab['kge_alpha'].to_numpy())
    tab['β'] = closeness_to_one(tab['kge_beta'].to_numpy())
    return tab


def radar(perf, experiments, region, figsize=(18, 8)):
    tab = component_table(perf, experiments, region)
    models = sort_models(tab['model'].unique())
    keys, labels = ['r', 'α', 'β'], ['r', 'α*', 'β*']

    n = len(experiments)
    ncols = min(n, 5)
    nrows = (n + ncols - 1) // ncols
    fig, axs = plt.subplots(nrows, ncols, figsize=figsize, subplot_kw=dict(polar=True))
    axs = np.atleast_1d(axs).ravel()
    angles = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist()
    angles += angles[:1]

    for i, exp in enumerate(experiments):
        ax = axs[i]
        sub = tab[tab['experiment'] == exp]
        ax.plot(angles, [1] * (len(keys) + 1), c='gray', ls='--', lw=1.5, zorder=1)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles[:-1]), labels)
        ax.set_title(exp, y=1.08, x=0.0, loc='left')
        ax.set_ylim(0, 1.0)
        for m in models:
            row = sub[sub['model'] == m]
            if row.empty:
                continue
            vals = row[keys].iloc[0].tolist()
            vals += vals[:1]
            ax.plot(angles, vals, color=model_color(m), lw=2.5, label=model_label(m), zorder=3)
            ax.fill(angles, vals, color=model_color(m), alpha=0.08, zorder=2)
    for j in range(i + 1, len(axs)):
        fig.delaxes(axs[j])

    handles = [mlines.Line2D([], [], color=model_color(m), lw=3, label=model_label(m)) for m in models]
    fig.legend(handles=handles, loc='center right', bbox_to_anchor=(1.02, 0.5), frameon=False, title='Model')
    fig.subplots_adjust(right=0.88)
    fig.suptitle(f'Median KGE components – {region} ({RES_GROUP}, {AGGREGATION}) | mode=normalized', y=1.02)
    fig.tight_layout()
    return fig, tab


perf = load_performance()
# all experiments present in the data are drawn for every basin (empty panel if none)
experiments = [e for e in EXP_ORDER if e in set(perf['experiment'])]
tables = []
for basin in BASINS:
    fig, tab = radar(perf, experiments, basin)
    savefig(fig, f'{basin}_radar_norm_1km')
    tables.append(tab.assign(region=basin))
table = pd.concat(tables).rename(columns={'kge_r': 'median_r', 'kge_alpha': 'median_alpha',
                                          'kge_beta': 'median_beta', 'α': 'alpha_star', 'β': 'beta_star'})
table = table[['region', 'model', 'experiment', 'median_r', 'median_alpha', 'median_beta', 'alpha_star', 'beta_star']]
table.round(3).to_csv(TABLE_DIR / 'median_kge_components.csv', index=False)
print('Saved output/tables/median_kge_components.csv')
