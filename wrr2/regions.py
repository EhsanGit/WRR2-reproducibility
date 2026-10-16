"""Study basins, the models run in each of them, and the experiment design.

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import re

BASINS = ['Po', 'Rhine', 'Tugela']

# Models shown in the figures of each basin (CLM and JULES were not run in the
# Tugela, TETIS was not run in the Rhine).
BASIN_MODELS = {
    'Po': ['clm', 'jules', 'mhm', 'pcrglobwb', 'tetis'],
    'Rhine': ['clm', 'jules', 'mhm', 'pcrglobwb'],
    'Tugela': ['mhm', 'pcrglobwb', 'tetis'],
}

# Models with joint EO+Q calibration (exp41/42/44), used for the exp44 figures.
JOINT_MODELS = {
    'Po': ['clm', 'mhm', 'tetis'],
    'Rhine': ['clm', 'mhm'],
    'Tugela': ['mhm', 'tetis'],
}

# Experiment order used on every axis. exp20 and exp21 are merged into exp2.
EXP_ORDER = ['exp10', 'exp2', 'exp30', 'exp31', 'exp32', 'exp33', 'exp34',
             'exp41', 'exp42', 'exp44']

EXP_META = {
    'exp10': {'family': '1x', 'label': 'Baseline (EMO/CHIRPS)', 'eo': False, 'cal': '–'},
    'exp2': {'family': '2x', 'label': 'Q-cal (best available)', 'eo': False, 'cal': 'Q'},
    'exp30': {'family': '3x', 'label': 'EO-P only', 'eo': True, 'cal': '–'},
    'exp31': {'family': '3x', 'label': 'EO-P + SM', 'eo': True, 'cal': 'SM'},
    'exp32': {'family': '3x', 'label': 'EO-P + ET', 'eo': True, 'cal': 'ET'},
    'exp33': {'family': '3x', 'label': 'EO-P + SCA', 'eo': True, 'cal': 'SCA'},
    'exp34': {'family': '3x', 'label': 'EO-P + SM+ET', 'eo': True, 'cal': 'SM+ET'},
    'exp41': {'family': '4x', 'label': 'EO-P + SM+Q', 'eo': True, 'cal': 'SM+Q'},
    'exp42': {'family': '4x', 'label': 'EO-P + ET+Q', 'eo': True, 'cal': 'ET+Q'},
    'exp44': {'family': '4x', 'label': 'EO-P + SM+ET+Q', 'eo': True, 'cal': 'SM+ET+Q'},
}

# Short descriptions printed inside the box-plot panels.
EXP_DESCRIPTION = {
    'exp10': 'non-EO-P',
    'exp2': 'non-EO-P + Q',
    'exp30': 'EO-P',
    'exp31': 'EO-P + SM',
    'exp32': 'EO-P + ET',
    'exp33': 'EO-P + SCA',
    'exp34': 'EO-P + SM + ET',
    'exp41': 'EO-P + SM + Q',
    'exp42': 'EO-P + ET + Q',
    'exp44': 'EO-P + SM + ET + Q',
}


def sort_experiments(exps):
    """Experiments sorted in the manuscript order; unknown names go last."""
    order = {e: i for i, e in enumerate(EXP_ORDER)}
    return sorted(exps, key=lambda x: order.get(x, 10_000))


def experiment_family(experiment):
    """Experiment family (1x baseline, 2x Q calibration, 3x EO-P/EO-only, 4x EO+Q)."""
    if experiment == 'exp2':
        return '2x'
    m = re.search(r'(\d+)$', experiment or '')
    if not m:
        return ''
    n = int(m.group(1))
    if n < 20:
        return '1x'
    if n < 30:
        return '2x'
    if n < 40:
        return '3x'
    return '4x'
