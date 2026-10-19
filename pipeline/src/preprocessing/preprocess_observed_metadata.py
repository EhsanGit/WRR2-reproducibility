"""
preprocess_observed_metadata.py  (step 3)

Selects the discharge gauges of each experiment and region: a gauge is kept if it
lies (1) inside the region extent, (2) has at least two years of record inside the
common period and (3) falls inside the common mask of the experiment.

Inputs:  /data/4dhydro/data/processed/tier1/observations/q/meta.parquet (all gauges)
         <save tree>/common/<experiment>/q/<region>/period.csv and mask.nc
Outputs: <save tree>/observations/<experiment>/q/<region>/meta.parquet
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).

Usage (default experiment exp40; "all" processes every experiment):
    python preprocess_observed_metadata.py --experiment exp35,exp36
    python preprocess_observed_metadata.py --experiment exp35 --overwrite

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""

import argparse
import pathlib as pl
import pandas as pd
import glob
import numpy as np
import xarray as xr
import os

# Optional command line options (applied in the "Process metadata" configuration below)
parser = argparse.ArgumentParser(description="Observed discharge metadata preprocessing.")
parser.add_argument("--experiment", default=None, help="Comma-separated experiments, e.g. exp35,exp36, or 'all' (default: exp40)")
parser.add_argument("--overwrite", action="store_true", help="Rewrite existing meta.parquet files")
args, _ = parser.parse_known_args()

# Define directories
tier1_directory = pl.Path("/data/4dhydro/data/processed/tier1/")
tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))
desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")

common_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/common")
observation_directory = pl.Path(f"{tier1_directory}/observations/q")
simulation_directory = pl.Path(f"{tier2_directory}/simulations")
output_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/observations")

# Set minimum period overlap in years
minimum_period_overlap = 2

# Define regional extents
extents = {
    "europe": [-11, 33, 42, 73],
    "rhine": [3, 46, 13, 53],
    "po": [6, 43, 13, 47],
    "tugela": [28, -30, 32, -27],
}

# Simulation patterns recognition
file_paths = glob.glob(f"{simulation_directory}/**/*.nc", recursive=True)
file_paths = sorted(file_paths)

# Filter the file paths that are in experiments directories
filtered_paths = [
    path for path in file_paths if os.path.basename(os.path.dirname(path)).startswith("exp")
]
# Replace filtered_paths with file_paths
file_paths = filtered_paths

simulation_patterns = []
invalid_files = []

# Iterate over all files and classify based on filename components
for file_path in file_paths:
    file_name = file_path.split("/")[-1]
    components = file_name.split('_')

    if len(components) >= 8:
        simulation_patterns.append({
            "model": components[0],
            "meteo": components[1],
            "variable": components[2],
            "region": components[3],
            "resolution": components[4],
            "temp_res": components[5],
            "experiment": components[6],
            "start_date": components[7],
            "end_date": components[8].split('.')[0]
        })
    elif len(components) == 5:
        simulation_patterns.append({
            "model": components[0],
            "meteo": components[1],
            "variable": components[2],
            "region": components[3],
            "resolution": components[4].split('.')[0],
            "temp_res": None,
            "experiment": None,
            "start_date": None,
            "end_date": None
        })
    else:
        invalid_files.append(file_name)

# Convert to DataFrame and sort patterns
if simulation_patterns:
    simulation_patterns = pd.DataFrame(simulation_patterns)
    simulation_patterns = simulation_patterns.sort_values(
        by=["model", "experiment", "variable", "region", "resolution", "start_date"]
    ).reset_index(drop=True)
else:
    print("No valid patterns found in the filenames.")

# Print invalid files
if invalid_files:
    print("\nThe following files did not match the expected pattern:")
    for invalid_file in invalid_files:
        print(invalid_file)

#%% Drop records
# GEOframe exp10 is left out (partner request)
simulation_patterns = simulation_patterns[~((simulation_patterns["model"] == "geoframe") & (simulation_patterns["experiment"] == "exp10"))]

#%% Process metadata
# --- Configuration ---
target_experiment = "exp40" # Set to None if you want to run all
overwrite = False           # Set to False to skip already processed patterns
# ---------------------

# Optional command line overrides (defaults = values above)
if args.experiment:
    target_experiment = None if args.experiment == "all" else [e.strip() for e in args.experiment.split(",") if e.strip()]
overwrite = overwrite or args.overwrite
if isinstance(target_experiment, str):
    target_experiment = [target_experiment]

# Find unique patterns and filter for specific variables
unique_patterns = simulation_patterns.drop_duplicates(
    subset=["model", "meteo", "variable", "region", "resolution", "experiment"]
)
unique_patterns = unique_patterns[unique_patterns["variable"] == "q"]
unique_patterns = unique_patterns.dropna(subset=["experiment"])

# Keep only the selected experiments
if target_experiment:
    unique_patterns = unique_patterns[unique_patterns["experiment"].isin(target_experiment)]

# Select and save gauges based on extent, period, and mask
meta_file = pl.Path(f"{observation_directory}/meta.parquet")
meta = pd.read_parquet(meta_file)

for index, row in unique_patterns.iterrows():
    model = row['model']
    meteo = row['meteo']
    variable = row['variable']
    region = row['region']
    resolution = row['resolution']
    experiment = row['experiment']

    print(f"Pattern: {model}_{meteo}_{variable}_{region}_{resolution}_{experiment}")

    period_file = common_directory / f"{experiment}/{variable}/{region}/period.csv"
    mask_file = common_directory / f"{experiment}/{variable}/{region}/mask.nc"

    extent = extents[region]
    period = pd.read_csv(period_file, parse_dates=["start", "end"])
    mask = xr.open_dataset(mask_file).mask

    region_meta = meta.copy()
    
    meta_lon_sel = np.logical_and(region_meta["lon"] >= extent[0], region_meta["lon"] <= extent[2])
    meta_lat_sel = np.logical_and(region_meta["lat"] >= extent[1], region_meta["lat"] <= extent[3])
    meta_sel = np.logical_and(meta_lon_sel, meta_lat_sel)
    print(f"\t > Removing {np.sum(~meta_sel)} gauges outside of the region extent")
    region_meta = region_meta.loc[meta_sel]

    start_date = period.at[0, "start"]
    end_date = period.at[0, "end"]
    meta_sel = np.logical_and(region_meta["start-year"] <= end_date.year - minimum_period_overlap,
                              region_meta["end-year"] >= start_date.year + minimum_period_overlap)
    print(f"\t > Removing {np.sum(~meta_sel)} gauges outside of the region period")
    region_meta = region_meta.loc[meta_sel]

    resolution = mask["lon"].values[1] - mask["lon"].values[0]

    excludes = []
    for index, row in region_meta.iterrows():
        try:
            include = mask.sel(lon=row["lon"], lat=row["lat"], method="nearest", tolerance=resolution / 2 + 1e-10)
            include = include.values
        except KeyError:
            include = False

        if not include:
            excludes.append(index)

    region_meta = region_meta.drop(excludes, axis=0)
    region_meta = region_meta.sort_values("average", ascending=False)

    print(f"\t > Removing {len(excludes)} gauges outside of the simulation domain")

    if region_meta.index.size == 0:
        continue

    meta_out = pl.Path(f"{output_directory}/{experiment}/{variable}/{region}/meta.parquet")

    # --- Overwrite Logic ---
    if not overwrite and meta_out.exists():
        print(f"Skipping {experiment}_{region}: File already exists.")
        continue

    meta_out.parent.mkdir(parents=True, exist_ok=True)
    region_meta.to_parquet(meta_out)

    print(f"\t - Saved {region_meta.index.size} out of {meta.index.size} gauges")

print("All patterns processed.")
