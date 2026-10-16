"""Table 6 (tab:winner): best configuration per basin, i.e. the model and experiment
with the highest median KGE at ~1 km, and its gain over the best baseline, defined as
the highest median KGE among exp10 and exp2 across models.

The manuscript table was compiled from these basin medians (the same medians as in
Fig. A1); there was no separate table script in the benchmarking code.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/tables/best_configuration_by_basin.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from wrr2.data import load_performance
from wrr2.paths import TABLE_DIR
from wrr2.regions import BASINS, EXP_META
from wrr2.style import model_label

perf = load_performance()
med = (perf.groupby(['region', 'model', 'experiment'], observed=True)['kge'].median()
       .rename('median_kge').reset_index())
med['experiment'] = med['experiment'].astype(str)

rows = []
for basin in BASINS:
    sub = med[med['region'] == basin]
    best = sub.loc[sub['median_kge'].idxmax()]
    base = sub[sub['experiment'].isin(['exp10', 'exp2'])]
    # on ties the first in model and experiment order is reported (exp10 before exp2)
    base = base.sort_values(['median_kge', 'experiment'], ascending=[False, True])
    best_base = base.iloc[0]
    rows.append({
        'basin': basin,
        'best_model': model_label(best['model']),
        'experiment': f"{best['experiment']}: {EXP_META[best['experiment']]['cal']}",
        'median_kge': f"{best['median_kge']:.2f}",
        'best_baseline': f"{model_label(best_base['model'])} / {best_base['experiment']} ({best_base['median_kge']:.2f})",
        'delta_vs_baseline': f"{best['median_kge'] - best_base['median_kge']:+.2f}",
        'median_kge_full': best['median_kge'],
        'baseline_kge_full': best_base['median_kge'],
    })
table = pd.DataFrame(rows)
table.to_csv(TABLE_DIR / 'best_configuration_by_basin.csv', index=False)
print(table.drop(columns=['median_kge_full', 'baseline_kge_full']).to_string(index=False))
print('Saved output/tables/best_configuration_by_basin.csv')
