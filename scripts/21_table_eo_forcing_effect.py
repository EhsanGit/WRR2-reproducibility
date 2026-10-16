"""Table 5 (tab:eo_forcing_effect_all_basins): gauge-level response to EO precipitation
forcing (exp30 vs exp10): paired median ΔKGE and the shares of gauges that are better,
the same (|ΔKGE| <= 0.10) or worse. The statistics are those printed in the scatter
panels of Figs. 4, A2 and A3; the full-precision values are kept in extra columns.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/tables/eo_forcing_effect_all_basins.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from wrr2.data import load_performance, paired_delta
from wrr2.paths import TABLE_DIR
from wrr2.plots import scatter_stats
from wrr2.regions import BASINS, BASIN_MODELS
from wrr2.style import model_label

perf = load_performance()
rows = []
for basin in BASINS:
    for model in BASIN_MODELS[basin]:
        d = paired_delta(perf, baseline='exp10', experiments=['exp30'], region=basin, model=model)
        if d.empty:
            print(f'{model} {basin}: no paired gauges for exp30 vs exp10')
            rows.append({'basin': basin, 'model': model_label(model)})
            continue
        s = scatter_stats(d['kge_base'].to_numpy(), d['kge_cur'].to_numpy(), band=0.10)
        rows.append({'basin': basin, 'model': model_label(model),
                     'median_dkge': f"{s['median_dkge']:+.2f}",
                     'pct_better': f"{s['pct_better']:.0f}",
                     'pct_same': f"{s['pct_same']:.0f}",
                     'pct_worse': f"{s['pct_worse']:.0f}",
                     'n_gauges': s['n'], 'median_dkge_full': s['median_dkge'],
                     'pearson_r': s['pearson_r'], 'wilcoxon_p': s['wilcoxon_p']})
table = pd.DataFrame(rows)
table['n_gauges'] = table['n_gauges'].astype('Int64')
table.to_csv(TABLE_DIR / 'eo_forcing_effect_all_basins.csv', index=False)
with pd.option_context('display.width', 200, 'display.max_columns', 20):
    print(table.drop(columns=['median_dkge_full']).to_string(index=False))
print('Saved output/tables/eo_forcing_effect_all_basins.csv')
