"""Loading the gauge-level KGE table and the paired contrasts used by all scripts.

The functions follow the benchmarking code used for the manuscript
(tier2_benchmarking, src/visualisation/eo_plot_discharge.py) without changes
to the computations.

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import numpy as np
import pandas as pd

from wrr2.paths import data_file
from wrr2.regions import EXP_ORDER

KGE_FILE = ('kge', 'streamflow_kge_gauges_1km.csv')
RES_GROUP = '≈1km'
AGGREGATION = 'daily'


def merge_exp20_exp21_to_exp2(df):
    """Report exp20 (Q calibration) and exp21 (transfer to ~1 km) jointly as exp2.

    exp21 is used where it exists; exp20 rows are kept only for gauges without
    a matching exp21 row (same model, basin, resolution and station)."""
    df = df.copy()
    keys = ['model', 'region', 'resolution', 'station']
    keys21 = df.loc[df['experiment'].eq('exp21'), keys].drop_duplicates()
    keys21['_has21'] = True
    exp20 = df[df['experiment'].eq('exp20')].merge(keys21, on=keys, how='left')
    exp20_kept = exp20.loc[exp20['_has21'].isna(), df.columns]
    others = df[~df['experiment'].eq('exp20')]
    out = pd.concat([others, exp20_kept], ignore_index=True)
    out['experiment'] = out['experiment'].replace({'exp20': 'exp2', 'exp21': 'exp2'})
    return out


def load_performance():
    """Daily KGE and its components per gauge, model, experiment and basin at ~1 km,
    with exp20/exp21 merged into exp2 and experiments as an ordered categorical."""
    perf = pd.read_csv(data_file(*KGE_FILE), dtype={'station': str})
    perf = merge_exp20_exp21_to_exp2(perf)
    perf = perf[perf['experiment'].isin(EXP_ORDER)].copy()
    present = [e for e in EXP_ORDER if e in set(perf['experiment'].astype(str))]
    perf['experiment'] = pd.Categorical(perf['experiment'], categories=present, ordered=True)
    perf['res_group'] = RES_GROUP
    perf['aggregation'] = AGGREGATION
    return perf.reset_index(drop=True)


def closeness_to_one(x):
    """Map a ratio to (0, 1] with exp(-|ln x|); 1 when the ratio is 1."""
    x = np.where(np.isfinite(x) & (x > 0), x, np.nan)
    return np.exp(-np.abs(np.log(x)))


def paired_delta(perf, baseline='exp10', experiments=None, region=None, model=None):
    """Paired ΔKGE per gauge (experiment minus baseline) for each experiment.

    Gauges are paired on model, basin, resolution and station; gauges missing
    in either experiment are dropped."""
    df = perf.copy()
    if region:
        df = df[df['region'] == region]
    if model:
        df = df[df['model'] == model]
    if experiments is None:
        experiments = [e for e in EXP_ORDER if e in set(df['experiment']) and e != baseline]
    idx = ['model', 'region', 'resolution', 'station']
    base = df[df['experiment'] == baseline].set_index(idx)['kge'].rename('kge_base')
    out = []
    for e in experiments:
        cur = df[df['experiment'] == e].set_index(idx)['kge'].rename('kge_cur')
        pair = pd.concat([base, cur], axis=1, join='inner').dropna()
        if pair.empty:
            continue
        pair['experiment'] = e
        pair['delta_kge'] = pair['kge_cur'] - pair['kge_base']
        out.append(pair.reset_index())
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=['experiment', 'delta_kge'])


def pvalue_stars(p):
    """Significance code of a p value: ***, **, * or ns."""
    if not np.isfinite(p):
        return ''
    return '***' if p < 1e-3 else ('**' if p < 1e-2 else ('*' if p < 5e-2 else 'ns'))

