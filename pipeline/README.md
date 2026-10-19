# Benchmarking pipeline

The scripts in `src/` produce the gauge-level scores (`performance.csv`) from which `build_data.py` builds the data used by the figure and table scripts of this repository. They are the 4DHydro WP5 benchmarking workflow, also kept at codebase.helmholtz.cloud/4dhydro/wp5/benchmarking. They run on the full model simulations, which are archived by each modelling group (see the Data Availability Statement of the article), not on the Zenodo data of this repository. Paths below are relative to this `pipeline/` folder.

## Folders and environment variables

All steps read and write under one root folder and one save name, set by two environment variables:

| Variable | Default (used for the WRR study) | Meaning |
|---|---|---|
| `T2B_TIER2_DIRECTORY` | `/data/4dhydro/data/processed/tier2/` | root folder with `simulations/` (input) and the outputs |
| `T2B_DESIRED_NAME` | `eo_alternative` | save name: outputs go to `saves_<name>/` and `simulations_mya_<name>/` |

The gauge records are read from `/data/4dhydro/data/processed/tier1/observations/q/` (`meta.parquet` with all gauges, and one folder per provider). The patterns file of step 6 is written to `resource/` in this repository. The same steps can be run into a separate tree, for example:

```bash
export T2B_TIER2_DIRECTORY=/data/4dhydro/data/processed/eo_forcings/
export T2B_DESIRED_NAME=eo_forcings
```

## Order of the steps

Run the steps from `src/preprocessing` (step 8 from `src/benchmarking`). `--experiment` takes a comma-separated list. Without options each script keeps its defaults (given in its header). Existing outputs are kept unless stated.

| Step | Script | Command (example for exp35, mHM) | Output |
|---|---|---|---|
| 1 | `model_checkup/mask_uparea_checking.py` | `python model_checkup/mask_uparea_checking.py --model mhm --experiment exp35` (dry run), then add `--apply` | missing mask/uparea files copied from an earlier experiment |
| 2 | `preprocess_common_period_mask.py` | `python preprocess_common_period_mask.py --experiment exp35` (`--overwrite` to rewrite) | common period and mask of all models of the experiment |
| 3 | `preprocess_observed_metadata.py` | `python preprocess_observed_metadata.py --experiment exp35` (`--overwrite`, or `all`) | gauges inside the basin, the period and the mask |
| 4 | `preprocess_observed_data.py` | `python preprocess_observed_data.py --experiment exp35` | observed daily discharge per gauge, cut to the period |
| 5 | `preprocess_average_discharge_simulations.py` | `python preprocess_average_discharge_simulations.py --model mhm --experiment exp35` | long-term mean simulated discharge |
| 6 | `preprocess_simulated_metadata.py` | `python preprocess_simulated_metadata.py --model mhm --experiment exp35 --patterns-file simulation_patterns_eo_exp35.parquet` | gauge-to-cell matching (gauge correction) and the patterns file |
| 7 | `preprocess_simulated_data.py` | `python preprocess_simulated_data.py --experiment exp35 --patterns-file simulation_patterns_eo_exp35.parquet` | simulated daily discharge at the corrected cells |
| 8 | `../benchmarking/benchmark_performance.py` | `python benchmark_performance.py --model mhm --experiment exp35 --patterns-file simulation_patterns_eo_exp35.parquet` (`--region`, `--overwrite`) | `performance.csv` |

Notes:

- The patterns file is never overwritten, so give each new run its own `--patterns-file` name and pass the same name to steps 7 and 8.
- In step 6, experiments given with `--experiment` are added to the allowed experiments (`ALLOWED`) of the `--model` models (default mhm).
- Gauge correction (step 6): the nearest cell is taken first. If the gauge has an upstream area, the cells within 0.25° whose simulated upstream area is within 10% of it are candidates; otherwise all cells within 0.25° are. Among them the cell whose mean discharge is closest to the observed mean is used.
- Scores (step 8): daily and monthly means, at least two years of overlap; normalised mean error, normalised RMSE, NSE, and KGE, KGE′ and non-parametric KGE with their components (`hydroeval`).
- The common period and mask (step 2) are the overlap of all models of an experiment, so they depend on which models are present in `simulations/`.
- On EVE, scipy needs a newer libstdc++ than the system one: `export LD_LIBRARY_PATH=<conda env>/lib:$LD_LIBRARY_PATH`.
- The SLURM scripts in `src/download/` contain the EVE paths used at the time; adapt `--chdir`, the log folder and the `/work` paths before use.

## Layout of the save tree

```
<T2B_TIER2_DIRECTORY>/
├── simulations/<model>/<experiment>/                    input files (download step), e.g.
│       mhm_emo_q_po_0p015625deg_daily_exp10_19900101_19901231.nc, mhm_emo_mask_po_0p015625deg.nc
├── simulations_mya_<name>/<model>/<experiment>/*.nc     step 5: mean of annual means
└── saves_<name>/
    ├── common/<experiment>/<variable>/<region>/
    │       period.csv, mask.nc                          step 2
    ├── observations/<experiment>/q/<region>/
    │       meta.parquet                                 step 3: selected gauges
    │       data/discharge_<gauge>.parquet               step 4
    ├── simulations/<model>/q/<experiment>/<region>/<resolution>/
    │       meta.parquet                                 step 6: gauges with simulated_* and corrected_simulated_* lat, lon, area, average
    │       data/discharge_<gauge>.parquet               step 7
    └── performance/<model>/q/<experiment>/<region>/<resolution>/
            performance.csv                              step 8: one row per gauge and aggregation (daily, monthly)
```

The WRR study used the defaults, i.e. `/data/4dhydro/data/processed/tier2/saves_eo_alternative/`.

File names follow `{model}_{forcing}_{variable}_{region}_{resolution}_{step}_{experiment}_{start}_{end}.nc`, and `{model}_{forcing}_{mask|uparea}_{region}_{resolution}.nc` for static files (parsed by `src/utils/simulation_patterns.py`). The forcing token is `emo` (Po, Rhine) or `chirps` (Tugela) for exp10, exp20 and exp21, and `mergedera5gpmsm2a` for the EO-forced experiments exp30–exp34, exp41, exp42 and exp44. Coordinates are named `lat` and `lon`; `latitude`/`longitude` are renamed in the code.

## Downloading the partner files (`src/download/`)

The partner simulations are published on different platforms (OPeNDAP/THREDDS catalogues, Zenodo, institutional web folders, the mHM S3 bucket). These steps are repeated whenever partners deliver new data:

1. **Update `base_url`** in `extract_urls.py`. It is a nested dictionary model → experiment → catchment → URL (`None` = no data). Entries that are commented out were downloaded in earlier rounds.

   ```python
   base_url = {
       "CLM": {
           "Exp10": {"Po": ["<url>"], "Rhine": ["<url>"], "Tugela": None},
           ...
       },
       ...
   }
   ```

   Models: CLM, GEOframe, JULES, PCR-GLOBWB, TETIS, wflow_sbm (mHM URLs are built in `mhm_urls_logic`). Experiments: exp10, exp20, exp21, exp30–exp44. Catchments: Po, Rhine, Tugela (and Europe).
2. **Extract the URLs:** `python extract_urls.py` writes one list per model and experiment (e.g. `clm_exp10.txt`). Pages that need a browser are read with headless Chromium (selenium); Zenodo records through the Zenodo API.
3. **Filter the lists:** `python url_revision.py` keeps only the files of the experiment of each list (plus mask and uparea files), because some partner folders hold several experiments.
4. **Download** in parallel with SLURM (one array task per list, files that exist are skipped):

   ```bash
   cd src/download/
   sbatch -p download wget_download.sh
   ```

   Files go to `/work/modiri/4dhydro/<model>/<experiment>/`; logs to `logs/Tier2_download-<job>-<task>.out/.err`.
5. **Check the downloads by eye:** number of files per experiment and catchment, naming convention, no broken or incomplete files. Examples of manual fixes that were needed:

   ```bash
   # GEOframe exp10: rename files to the naming convention
   cd /work/modiri/4dhydro/geoframe/exp10
   for file in *.nc; do
       new_file=$(echo "$file" | sed -e 's/EXP1/exp10/' -e 's/0.5_arcmin/30sec/')
       new_file=$(echo "$new_file" | sed 's/\(daily\)/\1_/' | sed 's/\(daily_.*\)_exp10/\1_exp10/')
       mv "$file" "$new_file"
   done

   # wflow_sbm and TETIS: copy the uparea/mask files into exp21
   cp -v *_uparea_*_30sec.nc ../exp21
   cp -v *_mask_*_30sec.nc ../exp21
   ```

   `pcr_deliniation_files.py` copies the PCR-GLOBWB mask and uparea files, delivered once in a `delineation/` folder, into each exp3x folder.
6. **Copy to the data tree:** `sbatch -p download copy_simulations.sh` copies the checked folders from `/work` to `/data/4dhydro/data/processed/tier2/simulations/` (rsync).

The largest downloaded files can be listed with `find /gpfs1/work/modiri/4dhydro -type f -name "*.nc" -exec du -h {} + | sort -hr | head -n 1`.
