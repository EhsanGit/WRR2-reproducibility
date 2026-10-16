"""Repository-relative locations of the input data and generated outputs.

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
FIG_DIR = ROOT / 'output' / 'figures'
TABLE_DIR = ROOT / 'output' / 'tables'

FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def data_file(*parts):
    """Path to an input file under data/, with a clear error if it has not been downloaded."""
    path = DATA_DIR.joinpath(*parts)
    if not path.exists():
        raise FileNotFoundError(
            f'{path} not found. Run `python download_data.py` first to fetch the input data.')
    return path
