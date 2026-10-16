# WRR2: reproducing the figures and tables

This repository contains the code to reproduce the figures and tables of

> Modiri, E., Rakovec, O., Shrestha, P. K., García-García, A., Avila, L., Blackford, K., Cooper, E., Cortes-Torres, N., Di Paolo, F., Droppers, B., Filippucci, P., Fischer, M., Güiza-Villa, N., Orság, M., Stradiotti, P., Wiggins, M., Brocca, L., Clark, D., Dall'Amico, M., Dorigo, W., Frances, F., Kollet, S., Peng, J., Wanders, N., and Samaniego, L.: *Assessing the Added Value of Earth Observations for Multi-Model Kilometre-Scale Hydrological Modelling Across Contrasting Basins*, Water Resources Research (submitted, 2025WR042446).

The study runs up to five hydrological and land-surface models (CLM, JULES, mHM, PCR-GLOBWB and TETIS) at about 1 km in the Po, Rhine and Tugela basins. It compares a baseline with conventional precipitation (EMO-1, CHIRPS in the Tugela), discharge calibration, EO precipitation (HYPER-P), calibration against EO soil moisture, evapotranspiration and snow cover, and joint calibration against EO data and discharge. Skill is the daily Kling–Gupta efficiency (KGE) and its components at each gauge.

The scripts start from the gauge-level KGE scores of all model–experiment–basin combinations. These are archived separately on Zenodo (doi: to be added). The model simulations are listed in the 4DHydro Open Science Catalogue (https://4dhydro.eu/catalog/).

## Quick start

```bash
git clone https://github.com/EhsanGit/WRR2-reproducibility.git
cd WRR2-reproducibility
conda env create -f environment.yml
conda activate wrr2
python download_data.py      # about 2 MB into data/
python run_all.py            # all figures and tables into output/
```

Each script can also be run on its own, for example `python scripts/20_scatter_exp30_vs_exp10.py`. Figures are written to `output/figures/` (PNG at 300 dpi and PDF) under the same file names as in the manuscript. Tables are written to `output/tables/` as CSV files. A full `run_all.py` takes less than a minute.

## Contents

```
wrr2/                shared helpers: paths, basins and experiments, plotting style, data loading
scripts/             one script per figure or table (list below)
build_data.py        builds the input table from the benchmarking output (run once, on EVE)
download_data.py     fetches the input data from Zenodo into data/
run_all.py           runs every script in order
environment.yml      conda environment
```

### Figures and tables

| Script | Manuscript item | Output |
|---|---|---|
| `01_table_availability.py` | Check of Table 3: model–experiment availability | `model_experiment_availability.csv` |
| `10_kge_boxplots_by_experiment.py` | Fig. 2: KGE across models and experiments | `{Po,Rhine,Tugela}_multi_model_performance_overlay_1km` |
| `11_median_dkge_lines.py` | Fig. 3: median ΔKGE relative to exp10 | `{basin}_lines_dkge_vs_exp10_1km`, `median_dkge_vs_exp10.csv` |
| `12_median_kge_lines.py` | Fig. A1: median KGE | `{basin}_lines_kge_1km`, `median_kge.csv` |
| `20_scatter_exp30_vs_exp10.py` | Figs. 4, A2, A3: exp30 vs exp10 per gauge | `{model}_{basin}_scatter_exp30_vs_exp10_1km` |
| `21_table_eo_forcing_effect.py` | Table 5: EO precipitation forcing response | `eo_forcing_effect_all_basins.csv` |
| `22_scatter_exp44_vs_exp30.py` | Figs. 6, A4, A5: exp44 vs exp30 per gauge | `{model}_{basin}_scatter_exp44_vs_exp30_1km`, `scatter_exp44_vs_exp30.csv` |
| `30_delta_kge_overlay.py` | Fig. 5: ΔKGE relative to exp10 and share of gauges improved | `{basin}_multi_model_delta_overlay_1km_`, `winrate_vs_exp10.csv` |
| `40_table_best_configuration.py` | Table 6: best configuration per basin | `best_configuration_by_basin.csv` |
| `41_table_best_model_per_experiment.py` | Table 7: best model per experiment and basin | `best_model_per_experiment.csv` |
| `50_component_attribution.py` | Figs. 7, B1, B2: ΔKGE against Δr, Δα\*, Δβ\* | `{basin}_{model}_scatter_dkge_vs_exp10_1km`, `component_attribution_exp44_vs_exp10.csv` |
| `51_radar_components.py` | Fig. 8: radar charts of r, α\*, β\* | `{basin}_radar_norm_1km`, `median_kge_components.csv` |

Not produced by code in this repository:

- Fig. 1 (study regions) is a map adapted from Droppers et al. (2024), made with GIS software.
- Tables 1, 2, 4 and C1 describe the data sets, the experiments, the objective-function weights and the calibration set-up. They contain no results.
- Table 3 (availability matrix) was written by hand from the study design; `01_table_availability.py` lists what the data contain so the two can be compared.
- There was no table script in the benchmarking code: Tables 5–7 were filled in from the figure statistics and basin medians. The table scripts here compute the same quantities from the data.

The figure scripts follow the benchmarking code used for the manuscript (`src/visualisation/eo_plot_discharge.py` in the 4DHydro tier2_benchmarking repository), with the same computations and styling. The jitter of the gauge dots in Figs. 2 and 5 is random, so the dots move slightly between runs.

## Input data

`download_data.py` places the Zenodo file under `data/kge/`. `data/README_kge.md` describes the columns.

| Folder | Content |
|---|---|
| `kge/` | daily KGE, r, α and β per gauge for every model, experiment and basin at ~1 km |

KGE follows Gupta et al. (2009) and compares daily simulated discharge with observations at each gauge, with at least two years of overlap. Contrasts between experiments use paired gauges only. exp20 (discharge calibration) and exp21 (its transfer to ~1 km) are reported together as exp2.

`build_data.py` documents how the table was made from the per-simulation `performance.csv` files of the benchmarking. It only needs to be run again if the benchmarking is redone.

## Citation

If you use this code, please cite the article and this repository (doi: to be added); see `CITATION.cff`.

## Licence

Code: MIT (see `LICENSE`). Data on Zenodo: CC BY 4.0.
