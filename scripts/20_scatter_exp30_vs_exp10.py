"""Figs. 4, A2 and A3 (fig:po_exp30_vs_exp10, fig_rhine_exp30_vs_exp10,
fig:tugela_exp30_vs_exp10): gauge-wise KGE with EO precipitation forcing and no
recalibration (exp30) against the baseline (exp10), one panel per model and basin.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{model}_{basin}_scatter_exp30_vs_exp10_1km.png/.pdf

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrr2.data import load_performance
from wrr2.plots import baseline_scatter
from wrr2.regions import BASINS, BASIN_MODELS
from wrr2.style import savefig

perf = load_performance()
for basin in BASINS:
    for model in BASIN_MODELS[basin]:
        fig, _ = baseline_scatter(perf, 'exp10', 'exp30', basin, model)
        if fig is None:
            print(f'{model} {basin}: no paired gauges for exp30 vs exp10, skipped')
            continue
        savefig(fig, f'{model}_{basin}_scatter_exp30_vs_exp10_1km')
