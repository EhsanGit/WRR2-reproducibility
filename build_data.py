"""Collect the gauge-level KGE scores needed by the figure and table scripts into
one tidy table, ready to be archived on Zenodo.

Run once on the EVE cluster, where the benchmarking output is stored. The script
only reads from the benchmarking tree and writes to --out (never into the source).
It stops with an error if any of the required performance.csv files is missing,
unless --allow-missing is given, in which case it writes a partial table to
<out>/partial/ together with the list of missing files.

Inputs:
    <source>/<model>/q/<experiment>/<basin>/<resolution>/performance.csv
    (default source: /data/4dhydro/data/processed/tier2/saves_eo_alternative/performance)
Outputs:
    <out>/kge/streamflow_kge_gauges_1km.csv   daily KGE and components per gauge
    <out>/kge/inputs.txt                      list of the source files used
    <out>/kge.zip                             the table in the layout expected under data/,
                                              for upload to Zenodo (complete tables only)

Usage:
    python build_data.py [--source DIR] [--out DIR] [--allow-missing]

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

SOURCE = '/data/4dhydro/data/processed/tier2/saves_eo_alternative/performance'
OUT = '/work/modiri/4dhydro/wrr2_reproducibility_data'

# Grid used by each model at ~1 km (the "≈1km" group of the manuscript).
RESOLUTION = {
    'clm': '0p01667deg',
    'jules': '0p015625deg',
    'mhm': '0p015625deg',
    'pcrglobwb': '30sec',
    'tetis': '30sec',
}

# Experiments available at ~1 km for each model and basin. exp20 is listed where
# it was run at ~1 km; it is merged with exp21 into exp2 by the figure scripts.
EXPERIMENTS = {
    'clm': {
        'po': ['exp10', 'exp20', 'exp21', 'exp30', 'exp31', 'exp32', 'exp33', 'exp34', 'exp41', 'exp42', 'exp44'],
        'rhine': ['exp10', 'exp20', 'exp21', 'exp30', 'exp31', 'exp32', 'exp33', 'exp34', 'exp41', 'exp44'],
    },
    'jules': {
        'po': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp34'],
        'rhine': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp34'],
    },
    'mhm': {
        'po': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp33', 'exp34', 'exp41', 'exp42', 'exp44'],
        'rhine': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp34', 'exp41', 'exp42', 'exp44'],
        'tugela': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp34', 'exp41', 'exp42', 'exp44'],
    },
    'pcrglobwb': {
        'po': ['exp10', 'exp20', 'exp30', 'exp31', 'exp32', 'exp34'],
        'rhine': ['exp10', 'exp20', 'exp30', 'exp31', 'exp32', 'exp34'],
        'tugela': ['exp10', 'exp20', 'exp30', 'exp31', 'exp32', 'exp34'],
    },
    'tetis': {
        'po': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp34', 'exp41', 'exp42', 'exp44'],
        'tugela': ['exp10', 'exp21', 'exp30', 'exp31', 'exp32', 'exp34', 'exp41', 'exp42', 'exp44'],
    },
}

COLUMNS = ['station', 'aggregation', 'kge', 'kge_r', 'kge_alpha', 'kge_beta']


def required_files(source):
    for model in sorted(EXPERIMENTS):
        for basin in sorted(EXPERIMENTS[model]):
            for exp in EXPERIMENTS[model][basin]:
                res = RESOLUTION[model]
                yield model, exp, basin, res, Path(source) / model / 'q' / exp / basin / res / 'performance.csv'


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--source', default=SOURCE)
    parser.add_argument('--out', default=OUT)
    parser.add_argument('--allow-missing', action='store_true',
                        help='write a partial table to <out>/partial/ instead of stopping')
    args = parser.parse_args()

    out = Path(args.out).resolve()
    if out.is_relative_to(Path(args.source).resolve()) or str(out).startswith(('/data/4dhydro', '/gpfs1/data/4dhydro')):
        sys.exit('--out must not point into /data/4dhydro')

    files = list(required_files(args.source))
    missing = [f for *_, f in files if not os.path.exists(f)]
    print(f'{len(files)} files required, {len(missing)} missing')
    for f in missing:
        print(f'MISSING {f}')
    if missing and not args.allow_missing:
        sys.exit(f'{len(missing)} required input files are missing; nothing written.')

    out_dir = Path(args.out) / ('partial' if missing else '') / 'kge'
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for model, exp, basin, res, f in files:
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f, usecols=COLUMNS)
        df = df[df['aggregation'] == 'daily'].drop(columns='aggregation')
        df.insert(0, 'model', model)
        df.insert(1, 'experiment', exp)
        df.insert(2, 'region', basin.title())
        df.insert(3, 'resolution', res)
        frames.append(df)
    table = pd.concat(frames, ignore_index=True)
    table.to_csv(out_dir / 'streamflow_kge_gauges_1km.csv', index=False)

    with open(out_dir / 'inputs.txt', 'w') as fh:
        for *_, f in files:
            fh.write(f'{"MISSING " if str(f) in map(str, missing) else ""}{f}\n')
    if missing:
        with open(out_dir / 'MISSING.txt', 'w') as fh:
            fh.write('\n'.join(map(str, missing)) + '\n')
        print(f'PARTIAL table ({len(table)} rows) written to {out_dir}; do not publish it.')
    else:
        import zipfile
        with zipfile.ZipFile(Path(args.out) / 'kge.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(out_dir / 'streamflow_kge_gauges_1km.csv', 'kge/streamflow_kge_gauges_1km.csv')
        print(f'{len(table)} rows written to {out_dir}; upload {Path(args.out) / "kge.zip"} to Zenodo')


if __name__ == '__main__':
    main()
