# data/kge/

Gauge-level daily streamflow skill for every model, experiment and basin used in
the manuscript, at the ~1 km grid of each model. One row per gauge, model,
experiment and basin.

Built by `build_data.py` from the per-simulation `performance.csv` files of the
4DHydro WP5 benchmarking (tier2_benchmarking). Only the daily scores and the
columns needed by the scripts are kept. Gauge coordinates and observed discharge
are not included; the station identifiers are those of the 4DHydro gauge
selection.

## File

`streamflow_kge_gauges_1km.csv`

| Column | Description |
|---|---|
| `model` | `clm`, `jules`, `mhm`, `pcrglobwb` or `tetis` |
| `experiment` | `exp10`, `exp20`, `exp21`, `exp30`–`exp34`, `exp41`, `exp42`, `exp44` (see Table 2 of the manuscript). exp20 and exp21 are kept apart here; the scripts merge them into `exp2` (exp21 where available, exp20 otherwise) |
| `region` | basin: `Po`, `Rhine` or `Tugela` |
| `resolution` | model grid: `0p01667deg` (CLM), `0p015625deg` (JULES, mHM), `30sec` (PCR-GLOBWB, TETIS) |
| `station` | gauge identifier, the same across models and experiments within a basin |
| `kge` | Kling–Gupta efficiency of daily discharge (Gupta et al., 2009) [-] |
| `kge_r` | Pearson correlation between simulated and observed daily discharge [-] |
| `kge_alpha` | ratio of simulated to observed standard deviation [-] |
| `kge_beta` | ratio of simulated to observed mean [-] |

Missing values (empty cells) mark gauges for which the score could not be computed,
for example when the overlap with observations is shorter than two years. They are
dropped when gauges are paired between experiments.

Simulations: 2007–2020 (daily). Observations: GRDC and national agencies, collected
by the 4DHydro project.
