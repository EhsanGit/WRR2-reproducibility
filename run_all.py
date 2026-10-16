"""Run every figure and table script in scripts/ in order.

Inputs:  data/ (see download_data.py)
Outputs: output/figures/ and output/tables/

Author: Ehsan Modiri - UFZ
Date: 2026-10-16
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
failed = []
for script in sorted((ROOT / 'scripts').glob('*.py')):
    print(f'=== {script.name}')
    if subprocess.run([sys.executable, str(script)], cwd=ROOT).returncode != 0:
        failed.append(script.name)
print('\nAll scripts finished.' if not failed else f'\nFailed: {", ".join(failed)}')
sys.exit(1 if failed else 0)
