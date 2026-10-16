"""Check of Table 3 (tab:simulation_combinations): which model–experiment combinations
have gauge-level KGE at ~1 km in each basin, with the number of gauges.

Table 3 in the manuscript is part of the study design and was written by hand; this
script lists what the input data contain so that the two can be compared.

Inputs:  data/kge/streamflow_kge_gauges_1km.csv
Outputs: output/tables/model_experiment_availability.csv

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wrr2.data import load_performance
from wrr2.paths import TABLE_DIR
from wrr2.regions import EXP_ORDER
from wrr2.style import MODEL_ORDER, model_label

perf = load_performance()
counts = (perf.dropna(subset=['kge']).groupby(['model', 'region', 'experiment'], observed=True)
          .size().unstack('experiment').reindex(columns=[e for e in EXP_ORDER if e in set(perf['experiment'])]))
counts = counts.reindex([m for m in MODEL_ORDER if m in counts.index.get_level_values(0)], level=0)
counts = counts.fillna(0).astype(int)
counts.index = counts.index.set_levels([model_label(m) for m in counts.index.levels[0]], level=0)
counts.to_csv(TABLE_DIR / 'model_experiment_availability.csv')
print('Number of gauges with a KGE value (0 = combination not available):')
print(counts.to_string())
print('Saved output/tables/model_experiment_availability.csv')
