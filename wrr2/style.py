"""Plotting conventions shared by all figures: model names and colours, win-rate
colours, experiment-family separators and figure saving.

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import matplotlib.pyplot as plt

from wrr2.regions import EXP_DESCRIPTION, experiment_family

MODEL_ORDER = ['clm', 'jules', 'mhm', 'pcrglobwb', 'tetis']
MODEL_LABEL = {'clm': 'CLM', 'jules': 'JULES', 'mhm': 'mHM', 'pcrglobwb': 'PCR-GLOBWB', 'tetis': 'TETIS'}
MODEL_LETTER = {'clm': 'C', 'jules': 'J', 'mhm': 'M', 'pcrglobwb': 'P', 'tetis': 'T'}

# Paul Tol's colour-blind-safe palette, fixed per model across all figures.
MODEL_COLOR = {
    'clm': '#4477AA',
    'jules': '#228833',
    'mhm': '#CCBB44',
    'pcrglobwb': '#66CCEE',
    'tetis': '#AA3377',
}

# Black-and-white win-rate colours used in the ΔKGE overlay figure (hatched "worse").
WINRATE_COLORS_BW_HATCHED = {
    'better': '#2F2F2F',
    'worse': '#FFFFFF',
    'same': '#808080',
}
WINRATE_HATCH = {'worse': '////', 'same': '....', 'better': None}
HATCH_COLOR = '#DDDDDD'


def model_label(m):
    return MODEL_LABEL.get(str(m).strip().lower(), str(m))


def model_color(m):
    return MODEL_COLOR.get(str(m).strip().lower(), '#7f7f7f')


def sort_models(models):
    models = [str(m).strip().lower() for m in models]
    return [m for m in MODEL_ORDER if m in models] + [m for m in sorted(set(models)) if m not in MODEL_ORDER]


def draw_family_boundaries(ax, order, zorder=4, alpha=0.35):
    """Dashed vertical lines between experiment families on a categorical axis."""
    fams = [experiment_family(e) for e in order]
    for i in range(1, len(order)):
        if fams[i] != fams[i - 1]:
            ax.axvline(i - 0.5, ls='--', lw=1.0, color='gray', alpha=alpha, zorder=zorder)


def tighten_category_edges(axes, n_cats, pad=0.5):
    """Reduce the empty space left and right of categorical axes."""
    for ax in (axes if isinstance(axes, (list, tuple)) else [axes]):
        ax.set_xlim(-pad, (n_cats - 1) + pad)


def add_experiment_labels(ax, order):
    """Short experiment descriptions placed just inside the bottom of the panel."""
    ylim = ax.get_ylim()
    label_y = ylim[0] + (ylim[1] - ylim[0]) * 0.02
    for i, exp in enumerate(order):
        ax.text(i, label_y, EXP_DESCRIPTION.get(exp, exp), ha='center', va='bottom', fontsize=7,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8,
                          edgecolor='lightgray', linewidth=0.5),
                rotation=0, weight='normal')


def savefig(fig, name):
    """Save a figure as PNG (300 dpi) and PDF under output/figures/."""
    from wrr2.paths import FIG_DIR
    for ext in ('png', 'pdf'):
        fig.savefig(FIG_DIR / f'{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved output/figures/{name}.png/.pdf')
