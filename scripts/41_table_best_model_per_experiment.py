"""Table 7 (tab:exp_winner): model with the highest median KGE at ~1 km for each
experiment and basin.

The manuscript table lists every experiment except exp33, which was run by two models
only (CLM and mHM, Po and Rhine); exp33 is kept in the output with a flag. As for
Table 6, the manuscript table was compiled from the basin medians of Fig. A1.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/tables/best_model_per_experiment.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from wrr2.data import load_performance
from wrr2.paths import TABLE_DIR
from wrr2.regions import BASINS, EXP_ORDER
from wrr2.style import model_label

perf = load_performance()
med = (perf.groupby(['region', 'model', 'experiment'], observed=True)['kge'].median()
       .rename('median_kge').reset_index())
med['experiment'] = med['experiment'].astype(str)

rows = []
for exp in EXP_ORDER:
    for basin in BASINS:
        sub = med[(med['region'] == basin) & (med['experiment'] == exp)]
        if sub.empty:
            continue
        best = sub.loc[sub['median_kge'].idxmax()]
        rows.append({'experiment': exp, 'basin': basin, 'best_model': model_label(best['model']),
                     'median_kge': f"{best['median_kge']:.2f}", 'median_kge_full': best['median_kge'],
                     'n_models': len(sub), 'in_manuscript_table': exp != 'exp33'})
table = pd.DataFrame(rows)
table.to_csv(TABLE_DIR / 'best_model_per_experiment.csv', index=False)
print(table.drop(columns=['median_kge_full']).to_string(index=False))
print('Saved output/tables/best_model_per_experiment.csv')
