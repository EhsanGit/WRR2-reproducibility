"""Figs. 6, A4 and A5 (fig:po_exp44_vs_exp30, fig:rhine_exp44_vs_exp30,
fig:tugela_exp44_vs_exp30): gauge-wise KGE with joint EO+Q calibration (exp44) against
EO precipitation forcing without recalibration (exp30), for the models with exp44.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{model}_{basin}_scatter_exp44_vs_exp30_1km.png/.pdf
         output/tables/scatter_exp44_vs_exp30.csv  (the in-panel statistics)

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from wrr2.data import load_performance
from wrr2.paths import TABLE_DIR
from wrr2.plots import baseline_scatter
from wrr2.regions import BASINS, JOINT_MODELS
from wrr2.style import savefig

perf = load_performance()
rows = []
for basin in BASINS:
    for model in JOINT_MODELS[basin]:
        fig, stats = baseline_scatter(perf, 'exp30', 'exp44', basin, model)
        if fig is None:
            print(f'{model} {basin}: no paired gauges for exp44 vs exp30, skipped')
            continue
        savefig(fig, f'{model}_{basin}_scatter_exp44_vs_exp30_1km')
        rows.append({'basin': basin, 'model': model, **stats})
pd.DataFrame(rows).to_csv(TABLE_DIR / 'scatter_exp44_vs_exp30.csv', index=False)
print('Saved output/tables/scatter_exp44_vs_exp30.csv')
