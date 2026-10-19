"""
preprocess_simulated_metadata.py  (step 6)

Matches each selected gauge to a model cell (gauge correction) for every model,
experiment, region and resolution, and saves the table of simulation files
(simulation patterns) used by steps 7 and 8.

For each gauge the nearest cell is taken first. If the gauge has an upstream area,
the cells within 0.25 degrees whose simulated upstream area is within 10% of it (or
the closest one if none is) are candidates; otherwise all cells within 0.25 degrees
are. Among the candidates the cell whose long-term mean discharge (step 5) is
closest to the observed mean is chosen (corrected_simulated_lat/lon).

Inputs:  <root>/simulations/<model>/<experiment>/*.nc (discharge and uparea files)
         <root>/simulations_mya_$T2B_DESIRED_NAME/<model>/<experiment>/ (step 5)
         <save tree>/observations/<experiment>/q/<region>/meta.parquet (step 3)
Outputs: ../../resource/<patterns file> (not overwritten if it exists)
         <save tree>/simulations/<model>/q/<experiment>/<region>/<res>/meta.parquet
         (gauge table with simulated_* and corrected_simulated_* lat, lon, area, average;
         an existing file is kept)
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).

Usage (defaults: experiment exp40, all models in ALLOWED, simulation_patterns_eo_exp40.parquet):
    python preprocess_simulated_metadata.py --experiment exp35,exp36 --patterns-file simulation_patterns_eo_exp35.parquet
    python preprocess_simulated_metadata.py --model mhm --experiment exp35 --patterns-file simulation_patterns_eo_exp35.parquet
Experiments given with --experiment are added to ALLOWED for the --model models (default mhm).

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""  

#%% Importing libraries
# Standard library imports
import os
import sys
import glob
import warnings
import argparse
import pathlib as pl

# Third-party imports
import numpy as np
import pandas as pd
import xarray as xr
from typing import Optional
from IPython.display import display

# Local imports
# Add the src directory to the path for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.simulation_patterns import extract_simulation_patterns

#%% Simulation patterns recognition
tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))

desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")  # change as needed
observation_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/observations/")
simulation_directory = pl.Path(f"{tier2_directory}/simulations/")
output_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/simulations/")
simulation_mya_directory = pl.Path(f"{tier2_directory}/simulations_mya_{desired_name}")

extents = {
    "europe": [-11, 33, 42, 73],
    "rhine": [3, 46, 13, 53],
    "po": [6, 43, 13, 47],
    "tugela": [28, -30, 32, -27],
}

correction_distance = 0.25 # degrees

# --- Global Configuration ---
target_experiment = "exp40"  # Set to None to process all ALLOWED experiments
overwrite = True            # not used: reset to False before the patterns file is saved (below)
# ----------------------------

# Optional command line overrides (defaults = values in this script)
parser = argparse.ArgumentParser(description="Simulated discharge metadata preprocessing.")
parser.add_argument("--experiment", default=None, help="Comma-separated experiments, e.g. exp35,exp36, or 'all' (default: exp40)")
parser.add_argument("--model", default=None, help="Comma-separated models; restricts processing and receives the --experiment entries in ALLOWED (default: all models, new experiments added to mhm)")
parser.add_argument("--patterns-file", default="simulation_patterns_eo_exp40.parquet", help="Simulation patterns file name in ../../resource/ (or an absolute path)")
cli_args, _ = parser.parse_known_args()
cli_models = [m.strip() for m in cli_args.model.split(",") if m.strip()] if cli_args.model else None
cli_experiments = None
if cli_args.experiment and cli_args.experiment != "all":
    cli_experiments = [e.strip() for e in cli_args.experiment.split(",") if e.strip()]
if cli_args.experiment:
    target_experiment = cli_experiments
if isinstance(target_experiment, str):
    target_experiment = [target_experiment]

#%% Internal functions
def corrected_coordinates(simulated_values: xr.DataArray,
                          observed_lat: float,
                          observed_lon: float,
                          observed_value: float,
                          distance: float,
                          difference_range: Optional[float] = None) -> xr.DataArray:
    """
    corrected_coordinates: This function finds the closest simulated values to observed values within a specified distance.

    Args:
        simulated_values (xr.DataArray): Simulated data values.
        observed_lat (float): Latitude of the observed value.
        observed_lon (float): Longitude of the observed value.
        observed_value (float): The actual observed value.
        distance (float): The distance within which to search for matching values.
        difference_range (Optional[float]): Optional threshold to limit the acceptable difference.

    Returns:
        xr.DataArray: Corrected latitude and longitude closest to the observed value.
    """
    # Find values within distance
    lon_slice = slice(observed_lon - distance, observed_lon + distance)
    lat_slice = slice(observed_lat - distance, observed_lat + distance)
    if simulated_values.lon[0] > simulated_values.lon[-1]:
        lon_slice = slice(observed_lon + distance, observed_lon - distance)
    if simulated_values.lat[0] > simulated_values.lat[-1]:
        lat_slice = slice(observed_lat + distance, observed_lat - distance)
    nearby_values = simulated_values.sel(lon = lon_slice, lat = lat_slice)
    
    # Find minimum difference
    diff_points = np.abs(nearby_values - observed_value)
    sel_points = nearby_values.where(diff_points == diff_points.min(), drop = True)
    if difference_range is not None:
        sel_points = nearby_values.where(diff_points <= observed_value * difference_range, drop = True)
        if sel_points.size == 0:
            sel_points = nearby_values.where(diff_points == diff_points.min(), drop = True)
    
    return sel_points

#%% Simulation patterns recognition
simulation_patterns, invalid_files = extract_simulation_patterns(
    simulation_directory,
    exclude_experiments_startswith="sc"
)

# Display the results
print("\nSimulation Patterns:")
display(simulation_patterns)

if invalid_files:
    print("\nInvalid Files:")
    print(invalid_files)

#%% Drop records
# Drop records with model 'geoframe' and experiment 'exp10' from simulation_patterns
simulation_patterns = simulation_patterns[~((simulation_patterns["model"] == "geoframe") & (simulation_patterns["experiment"] == "exp10"))]
# Drop uparea record of geoframe for exp10 due to their request
simulation_patterns = simulation_patterns[~((simulation_patterns["model"] == "geoframe") & (simulation_patterns["misc"] == "exp10"))]

# Model-experiment combinations evaluated in WRR2 (experiments given with --experiment are added below)
ALLOWED = {
    "clm":       {"exp10", "exp20", "exp21", "exp30", "exp31", "exp32", "exp33", "exp34", "exp41", "exp42", "exp44"},
    "jules":     {"exp10", "exp21", "exp30", "exp31", "exp32", "exp34"},
    "mhm":       {"exp10", "exp20", "exp21", "exp30", "exp31", "exp32", "exp33", "exp34", "exp40", "exp41", "exp42", "exp44"},
    "pcrglobwb": {"exp10", "exp20", "exp30", "exp31", "exp32", "exp34"},
    "tetis":     {"exp10", "exp20", "exp21", "exp30", "exp31", "exp32", "exp34", "exp41", "exp42", "exp44"}
}

# Experiments given on the command line are allowed for the selected models (default: mhm)
if cli_experiments:
    for m in (cli_models or ["mhm"]):
        ALLOWED[m] = set(ALLOWED.get(m, set())) | set(cli_experiments)
# Restrict to the models given on the command line (if any)
if cli_models:
    ALLOWED = {m: e for m, e in ALLOWED.items() if m in cli_models}

simulation_patterns = simulation_patterns[
    simulation_patterns["model"].isin(ALLOWED.keys()) &
    simulation_patterns["experiment"].isin(
        {e for s in ALLOWED.values() for e in s}
    ) &
    simulation_patterns.apply(
        lambda r: r["experiment"] in ALLOWED.get(r["model"], set()), axis=1
    )
].copy()
# Check the unique experiments for each model after filtering
for model in simulation_patterns["model"].unique():
    model_experiments = simulation_patterns[simulation_patterns["model"] == model]["experiment"].unique()
    print(f"Model: {model}, Experiments: {sorted(model_experiments)}")
#%%

# Save the simulation patterns in the resource directory. With overwrite = False an existing
# file is kept, and so are existing meta.parquet files in the correction step below.
desired_directory = pl.Path(f"../../resource/")
file_name = cli_args.patterns_file

# Check whether the file exists and if not, save the simulation patterns to a parquet file
overwrite = False

file_path = desired_directory / file_name

# Check if the file doesn't exist OR if overwrite is True
if not file_path.exists() or overwrite:
    simulation_patterns.to_parquet(file_path)
    print(f"Simulation patterns saved in {file_path} successfully.")
else:
    print(f"File {file_path} already exists. To overwrite, set 'overwrite' to True.")

#%% Simulation upstream area and simulation averages
simulation_upareas = {}
simulation_averages = {}

for model in simulation_patterns["model"].unique():
    print("Model: {}".format(model))

    unique_model_simulation_patterns = simulation_patterns[simulation_patterns["model"] == model]

    # Iterate over unique experiments
    unique_experiments = unique_model_simulation_patterns["experiment"].unique()
    # Drop the None value from the unique experiments
    unique_experiments = unique_experiments[~pd.isnull(unique_experiments)]
    unique_experiments = sorted(unique_experiments)

    # Initialize the dictionary for the current model if not already done
    if model not in simulation_upareas:
        simulation_upareas[model] = {}
        simulation_averages[model] = {}

    for experiment in unique_experiments:
        if target_experiment and experiment not in target_experiment:
            continue
        print("Experiment: {}".format(experiment))
        unique_patterns = unique_model_simulation_patterns[unique_model_simulation_patterns["variable"] == "uparea"]

        # Drop rows that have nor misc equal to experiment
        unique_patterns = unique_patterns[unique_patterns["misc"] == experiment]

        # Reset the index of the DataFrame
        unique_patterns = unique_patterns.reset_index(drop=True)

        # Initialize the dictionary for the current experiment if not already done
        if experiment not in simulation_upareas:
            simulation_upareas[model][experiment] = {}
            simulation_averages[model][experiment] = {}
        
        # Iterate over unique regions within the filtered patterns
        for region in sorted(unique_patterns["region"].unique()):
            print("\t\t Region: {}".format(region))

            # Filter patterns for the current variable, region and experiment
            region_sel = unique_patterns["region"] == region

            region_patterns = unique_patterns.loc[region_sel]

            # Initialize the dictionary for the current region
            simulation_upareas[model][experiment][region] = {}
            simulation_averages[model][experiment][region] = {}

            # Iterate over region patterns
            for pattern_index, fields in region_patterns.iterrows():
                # Construct pattern name
                pattern_name = f"{fields['model']}_{fields['meteo']}_{fields['variable']}_{fields['region']}_{fields['resolution']}_{fields['misc']}"
                print("\t\t\t - Pattern: {}".format(pattern_name))

                pattern_directory = pl.Path("{}/{}/{}".format(simulation_directory, fields['model'], fields['misc']))
                
                # Find the uparea file in this pattern directory
                res = pattern_name.split("_")[-2]
                uparea_file = "_".join(pattern_name.split("_")[:-1])
                uparea_file += ".nc"
                uparea_file_dir = pl.Path(f"{pattern_directory}/{uparea_file}")
                if not uparea_file_dir.exists():
                    print("\t\t> No upstream area file, skipping...")
                    continue
                
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=xr.SerializationWarning)

                    with xr.open_dataset(uparea_file_dir) as dataset:
                        uparea = dataset.data_vars["uparea"]
                
                if uparea.attrs["units"] == "km2":
                    uparea.attrs["units"] = "m2"
                    uparea *= 1e6
                
                simulation_upareas[model][experiment][region][res] = uparea
                
                print("\t\t\t\t Upstream data: {} m2".format(np.nanmean(uparea)))
                
                # List discharge files in the pattern directory that has the region and res in their name
                pattern = pattern_name.replace("uparea", "q")
                pattern = "_".join(pattern.split("_")[:-1])
                pattern += "*.nc"

                discharge_files = list(pattern_directory.glob(pattern))
                discharge_files = np.sort(discharge_files)
                if len(discharge_files) <= 0:
                    print("\t\t\t\t No discharge files found, skipping...")
                    continue

                avg_directory = pl.Path("{}/{}/{}".format(simulation_mya_directory, fields['model'], fields['misc']))
                average_files = np.array([file for file in avg_directory.iterdir() if file.is_file() and file.stem.split("_")[2] == "q"])
                average_files = np.sort(average_files)

                average_file = None
                for file in average_files:
                    if file.stem.split("_")[3] == region and file.stem.split("_")[4] == res:
                        average_file = file
                        break
                
                if average_file is None:
                    print("\t\t\t\t No matching average file found, skipping...")
                    continue

                if not average_file.exists():
                    print(f"\t\t\t\t Average file {average_file} does not exist, skipping...")
                    continue

                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=xr.SerializationWarning)
                        with xr.open_dataset(average_file) as dataset:
                            average = dataset.data_vars["q"]
                    
                    simulation_averages[model][experiment][region][res] = average
                    print("\t\t\t\t - average: {} ms-1".format(np.nanmean(average)))

                except Exception as e:
                    print(f"\t\t\t\t Error processing average file: {e}")
                    continue

print("All patterns processed successfully.")

#%% Correction and saving
print("")
print("Starting the correction and saving process...")
print("")

unique_models = sorted(simulation_patterns["model"].unique())
for model in unique_models:
    print("Model: {}".format(model))

    unique_experiments = simulation_patterns[simulation_patterns["model"] == model]["experiment"].unique()
    unique_experiments = sorted(unique_experiments[~pd.isnull(unique_experiments)])

    for experiment in unique_experiments:
        if target_experiment and experiment not in target_experiment:
            continue

        print("\tExperiment: {}".format(experiment))
        unique_model_experiment_patterns = simulation_patterns[(simulation_patterns["model"] == model) & (simulation_patterns["experiment"] == experiment)]

        # Iterate over unique regions within the filtered patterns
        for region in sorted(unique_model_experiment_patterns["region"].unique()):
            print("\t\t Region: {}".format(region))

            extent = extents[region]
            # Check the existence of simulation_upareas[model][experiment][region]
            if model not in simulation_upareas or experiment not in simulation_upareas[model] or region not in simulation_upareas[model][experiment]:
                print("\t\t> No upstream area file, skipping...")
                continue
            if model not in simulation_averages or experiment not in simulation_averages[model] or region not in simulation_averages[model][experiment]:
                print("\t\t> No average file, skipping...")
                continue

            region_simulation_upareas = simulation_upareas[model][experiment][region]
            region_simulation_averages = simulation_averages[model][experiment][region]

            meta_file = pl.Path(
                "{}/{}/q/{}/meta.parquet".format(observation_directory, experiment, region))
            meta = pd.read_parquet(meta_file)
            print("\t\t- Loaded meta file in experiment {} for region {}".format(experiment, region))

            for res in region_simulation_upareas.keys():
                uparea = region_simulation_upareas[res]
                average = region_simulation_averages.get(res, None)  # Set default value here if not found
                if average is None:
                    continue

                # --- normalize coord names only for this case (latitude/longitude) ---
                def standardize_latlon(obj):
                    rename_map = {}
                    if 'latitude' in obj.coords or 'latitude' in obj.dims:
                        rename_map['latitude'] = 'lat'
                    if 'longitude' in obj.coords or 'longitude' in obj.dims:
                        rename_map['longitude'] = 'lon'
                    return obj.rename(rename_map) if rename_map else obj

                uparea  = standardize_latlon(uparea)
                average = standardize_latlon(average)

                # (optional) sanity check
                coords = set(uparea.coords) | set(uparea.dims)
                if not {'lat','lon'}.issubset(coords):
                    raise ValueError(f"{res}: expected lat/lon coords after renaming, found {sorted(coords)}")

                pattern_directory = pl.Path("{}/{}/{}".format(simulation_directory, model, experiment))
                pattern = "{}_*_q_{}_{}_*_{}_*".format(model, region, res, experiment)
                discharge_files = list(pattern_directory.glob(pattern))
                discharge_files = np.sort(discharge_files)

                if len(discharge_files) == 0:
                    continue

                discharge_file = discharge_files[0]
                print("\t\tPattern: {}".format(pattern))

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=xr.SerializationWarning)

                    try:
                        with xr.open_dataset(discharge_file) as dataset:
                            
                            # Check whether the latitude and longitude need to be renamed
                            if "latitude" in dataset.coords and "longitude" in dataset.coords:
                                dataset = dataset.rename({"latitude": "lat", "longitude": "lon"})

                            lat_slice = slice(extent[1], extent[3]) if dataset.lat.values[0] <= dataset.lat.values[-1] else slice(extent[3], extent[1])
                            lon_slice = slice(extent[0], extent[2]) if dataset.lon.values[0] <= dataset.lon.values[-1] else slice(extent[2], extent[0])
                            dataset = dataset.sel(lat=lat_slice,lon=lon_slice).isel(time=0)
                            discharge = dataset.data_vars["q"]

                    except ValueError as e:
                        if "unable to decode time units" in str(e):
                            print("\t\t\t**Decoding times failed, loading with decode_times=False.**")
                            with xr.open_dataset(discharge_file, decode_times=False) as dataset:
                                
                                # Extract the time units and values
                                time_units = dataset.time.attrs['units']
                                time_values = dataset.time.values
                                
                                # Calculate new time values using the base date from the units
                                base_date = pd.to_datetime(time_units.split('since ')[-1])
                                new_time = base_date + pd.to_timedelta(time_values, unit='D')
                                
                                # Replace the time coordinate
                                dataset = dataset.assign_coords(time=new_time)

                                lat_slice = slice(extent[1], extent[3]) if dataset.lat.values[0] <= dataset.lat.values[-1] else slice(extent[3], extent[1])
                                lon_slice = slice(extent[0], extent[2]) if dataset.lon.values[0] <= dataset.lon.values[-1] else slice(extent[2], extent[0])
                                dataset = dataset.sel(lat=lat_slice,lon=lon_slice).isel(time=0)
                                discharge = dataset.data_vars["q"]

                        else:
                            raise  # Raise other errors if they're not related to time decoding

                discharge_mask = np.isnan(discharge)
                uparea_mask = np.isnan(uparea)
                average_mask = np.isnan(average)

                # Mask the upstream area based on the discharge
                # Needed for wflowsbm that only supplies discharge in the main river stems
                if average_mask.sum().values > uparea_mask.sum().values:
                    mask = np.logical_or(np.logical_or(uparea_mask,
                                                    discharge_mask),
                                                    average_mask).squeeze()
                    
                    # Mask based on discharge
                    uparea, average = uparea.where(~mask), average.where(~mask)

                pattern_meta = meta.copy()
                pattern_meta["simulated_lat"] = np.nan
                pattern_meta["simulated_lon"] = np.nan
                pattern_meta["simulated_area"] = np.nan
                pattern_meta["simulated_average"] = np.nan
                pattern_meta["corrected_simulated_lat"] = np.nan
                pattern_meta["corrected_simulated_lon"] = np.nan
                pattern_meta["corrected_simulated_area"] = np.nan
                pattern_meta["corrected_simulated_average"] = np.nan

                resolution = abs(uparea.coords["lon"].values[1] - uparea.coords["lon"].values[0])

                for index, row in pattern_meta.iterrows():
                    # Attempt to select uparea with standard tolerance
                    try:
                        uncorr_uparea = uparea.sel(lon=row["lon"],
                                                lat=row["lat"],
                                                method="nearest",
                                                tolerance=resolution / 2 + 1e-10)
                    except KeyError:
                        print("\t\t\tGauge not in uparea at standard tolerance. Using exceptional tolerance.")
                        # Retry with increased tolerance
                        try:
                            uncorr_uparea = uparea.sel(lon=row["lon"],
                                                    lat=row["lat"],
                                                    method="nearest",
                                                    tolerance=resolution + 1e-2)
                        except KeyError:
                            raise ValueError("\t\t\tGauge not in uparea, even with exceptional tolerance.")

                    # Attempt to select average with standard tolerance
                    try:
                        uncorr_average = average.sel(lon=row["lon"],
                                                    lat=row["lat"],
                                                    method="nearest",
                                                    tolerance=resolution / 2 + 1e-10)
                    except KeyError:
                        print("\t\t\tGauge not in average at standard tolerance. Using exceptional tolerance.")
                        # Retry with increased tolerance
                        try:
                            uncorr_average = average.sel(lon=row["lon"],
                                                        lat=row["lat"],
                                                        method="nearest",
                                                        tolerance=resolution + 1e-2)
                        except KeyError:
                            raise ValueError("\t\t\tGauge not in average, even with exceptional tolerance.")


                    pattern_meta.at[index, "simulated_lat"] = uncorr_uparea.coords["lat"]
                    pattern_meta.at[index, "simulated_lon"] = uncorr_uparea.coords["lon"]
                    pattern_meta.at[index, "simulated_area"] = uncorr_uparea
                    pattern_meta.at[index, "simulated_average"] = uncorr_average
                    pattern_meta.at[index, "corrected_simulated_lat"] = uncorr_uparea.coords["lat"]
                    pattern_meta.at[index, "corrected_simulated_lon"] = uncorr_uparea.coords["lon"]
                    pattern_meta.at[index, "corrected_simulated_area"] = uncorr_uparea
                    pattern_meta.at[index, "corrected_simulated_average"] = uncorr_average

                    if not np.isnan(pattern_meta.at[index, "area"]):
                        # Take the nearest averages where the nearest upstream areas difference is EITHER
                        # 1. within 10% of the gauge upstream area OR
                        # 2. the minimum difference
                        
                        uparea_sel = corrected_coordinates(simulated_values=uparea,
                                                        observed_lat=row["lat"],
                                                        observed_lon=row["lon"],
                                                        observed_value=row["area"] * 1e6,
                                                        difference_range=0.1,
                                                        distance=correction_distance)
                        nearby_average = average.where(~np.isnan(uparea_sel), drop = True)
                        if nearby_average.size == 0:
                            nearby_average = average.where(~np.isnan(average.sel(lat=uparea_sel['lat'].values, lon=uparea_sel['lon'].values, method="nearest")), drop=True)
                        print("\t\t\tNearby average is calculated based on the upstream area")

                    elif not np.isnan(pattern_meta.at[index, "average"]):
                        # Simply take the nearest averages
                        lon_slice = slice(row["lon"] - correction_distance, row["lon"] + correction_distance)
                        lat_slice = slice(row["lat"] - correction_distance, row["lat"] + correction_distance)
                        if average.lon[0] > average.lon[-1]:
                            lon_slice = slice(row["lon"] + correction_distance, row["lon"] - correction_distance)
                        if average.lat[0] > average.lat[-1]:
                            lat_slice = slice(row["lat"] + correction_distance, row["lat"] - correction_distance)
                        nearby_average = average.sel(lon=lon_slice, lat=lat_slice)
                        print("\t\t\tNearby average is calculated based on the distance")

                    else:
                        raise ValueError("No upstream area or average?")

                    try:
                        corr_min = corrected_coordinates(simulated_values=nearby_average,
                                                        observed_lat=row["lat"],
                                                        observed_lon=row["lon"],
                                                        observed_value=row["average"],
                                                        distance=correction_distance)

                        # Continue with further processing if corr_min was found
                        corr_min = corr_min.sel(lon=row["lon"], lat=row["lat"], method="nearest")
                                            
                        corr_uparea = uparea.sel(lon=corr_min.coords["lon"], lat=corr_min.coords["lat"], method="nearest")
                        corr_average = average.sel(lon=corr_min.coords["lon"], lat=corr_min.coords["lat"], method="nearest")

                        pattern_meta.at[index, "corrected_simulated_lat"] = corr_uparea.coords["lat"]
                        pattern_meta.at[index, "corrected_simulated_lon"] = corr_uparea.coords["lon"]
                        pattern_meta.at[index, "corrected_simulated_area"] = corr_uparea
                        pattern_meta.at[index, "corrected_simulated_average"] = corr_average
                        
                    except ValueError as e:
                        # Log or print a message to know which gauge was skipped, if needed
                        print(f"Skipping gauge at index {index} due to error: {e}")
                        continue  # Skip this gauge and proceed with the next one

                pattern_meta = pattern_meta.astype({"simulated_lat": "float64",
                                                    "simulated_lon": "float64",
                                                    "simulated_area": "float32",
                                                    "corrected_simulated_lat": "float64",
                                                    "corrected_simulated_lon": "float64",
                                                    "corrected_simulated_area": "float32", })

                meta_out = pl.Path("{}/{}/q/{}/{}/{}/meta.parquet".format(output_directory, model, experiment, region, res))

                if not overwrite and meta_out.exists():
                    print(f"\t\t- Skipping {region} {res}: Output already exists.")
                    continue

                meta_out.parent.mkdir(parents=True, exist_ok=True)
                pattern_meta.to_parquet(meta_out)

                meta_sel = pattern_meta["simulated_area"] != pattern_meta["corrected_simulated_area"]
                corrected_meta = pattern_meta.loc[meta_sel]

                print("\t\t- Saved {} ({} corrected) gauges".format(pattern_meta.index.size,
                                                                corrected_meta.index.size))

print("All patterns processed successfully.")