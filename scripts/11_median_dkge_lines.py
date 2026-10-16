"""Fig. 3 (fig:med_delta_kge_vs_exp10): basin-median ΔKGE relative to the exp10 baseline
for each model across the experiments at ~1 km. The medians are also written to a table.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/figures/{Po,Rhine,Tugela}_lines_dkge_vs_exp10_1km.png/.pdf
         output/tables/median_dkge_vs_exp10.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from wrr2.data import load_performance
from wrr2.paths import TABLE_DIR
from wrr2.plots import median_kge_lines
from wrr2.regions import BASINS
from wrr2.style import savefig

perf = load_performance()
rows = []
for basin in BASINS:
    fig, med = median_kge_lines(perf, basin, delta=True, baseline='exp10')
    savefig(fig, f'{basin}_lines_dkge_vs_exp10_1km')
    rows.append(med.drop(columns='xpos').assign(region=basin))
table = pd.concat(rows).rename(columns={'kge': 'median_dkge'})[['region', 'model', 'experiment', 'median_dkge']]
table.round(3).to_csv(TABLE_DIR / 'median_dkge_vs_exp10.csv', index=False)
print('Saved output/tables/median_dkge_vs_exp10.csv')
