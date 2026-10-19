"""
preprocess_simulated_data.py  (step 7)

Extracts the simulated daily discharge at the corrected gauge cells (nearest grid
index to corrected_simulated_lat/lon of step 6) for the common period and writes
one series per gauge. Files whose time units cannot be decoded are read with
decode_times=False and the dates are rebuilt from the units.

Inputs:  <root>/resource/<patterns file> (written by step 6)
         <save tree>/common/<experiment>/q/<region>/period.csv
         <save tree>/simulations/<model>/q/<experiment>/<region>/<res>/meta.parquet
         <root>/simulations/<model>/<experiment>/*_q_<region>_<res>_*_<experiment>_*.nc
Outputs: <save tree>/simulations/<model>/q/<experiment>/<region>/<res>/data/discharge_<gauge>.parquet
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).
(<root>/resource/ is the repository folder resource/, read as ../../resource/ from src/preprocessing.)

Usage (defaults: experiment exp40, simulation_patterns_eo_exp40.parquet):
    python preprocess_simulated_data.py --experiment exp35,exp36 --patterns-file simulation_patterns_eo_exp35.parquet

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""

#%% Import required libraries
import numpy as np
import pandas as pd
import xarray as xr
import datetime as dt
import os
import pathlib as pl
import warnings
import argparse

parser = argparse.ArgumentParser(description="Preprocessing of simulated data.")
parser.add_argument("--experiment", default="exp40", help="Comma-separated experiments, e.g. exp35,exp36 (default: exp40)")
parser.add_argument("--patterns-file", default="simulation_patterns_eo_exp40.parquet", help="Simulation patterns file name in ../../resource/ (or an absolute path)")
cli_args, _ = parser.parse_known_args()
target_experiments = [e.strip() for e in cli_args.experiment.split(",") if e.strip()]

tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))

desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")
common_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/common/")
output_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/simulations/")
save_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/simulations/")
simulation_directory = pl.Path(f"{tier2_directory}/simulations/")

#%% Internal functions
def convert_dates(time) -> list[dt.date]:
    """Converts time to daily dates"""
    if type(time) is not pd.DatetimeIndex:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            dates = pd.to_datetime([d for d in time.to_datetimeindex()])
    else:
        dates = pd.to_datetime(time)
    dates = pd.to_datetime(dates.date) # convert to daily dates
    return dates

#%% Main body
# Load simulation patterns (written by preprocess_simulated_metadata.py)
simulation_patterns = pd.read_parquet(pl.Path("../../resource/") / cli_args.patterns_file)

models = simulation_patterns.model.unique()
# Only discharge is extracted
variables = sorted(["et", "q", "sm", "tws"])
variables = [variables[1]]
print("Variable: {}".format(variables))

for model in models:
    print("Model: {}".format(model))

    for var in variables:
        print("\tVariable: {}".format(var))
        var_directory = pl.Path("{}/{}/{}/".format(save_directory, model, var))
        # list of experiments in the current model and variable from simulation patterns
        experiments = simulation_patterns[(simulation_patterns.model == model) & (simulation_patterns.variable == var)].experiment.unique()
        experiments = np.sort(experiments)

        for experiment in experiments:
            # only keep the selected experiments (default "exp40") and do not process the rest
            if experiment not in target_experiments:
                continue
            print("\t\tExperiment: {}".format(experiment))
            experiment_directory = pl.Path("{}/{}/".format(var_directory, experiment))
            regions = [dir.stem for dir in experiment_directory.iterdir() if dir.is_dir()]
            regions = np.sort(regions)

            for region in regions:
                print("\t\t\tRegion: {}".format(region))
                region_directory = pl.Path("{}/{}/".format(experiment_directory, region))
                resolutions = [dir.stem for dir in region_directory.iterdir() if dir.is_dir()]
                resolutions = np.sort(resolutions)

                # Read common time period for these variable, experiment, and region
                period_file = pl.Path("{}/{}/{}/{}/period.csv".format(common_directory, experiment, var, region))
                period = pd.read_csv(period_file, parse_dates=["start", "end"]).iloc[0]

                for resolution in resolutions:
                    print("\t\t\t\tResolution: {}".format(resolution))
                    desired_directory = pl.Path("{}/{}/".format(region_directory, resolution))
                            
                    meta_file = pl.Path("{}/meta.parquet".format(desired_directory))
                    meta = pd.read_parquet(meta_file)
                    print("\t\t\t\t\t- reading meta file: {}".format(meta_file))
                    print("\t\t\t\t\t- {} gauges".format(meta.index.size))
                    
                    start_date = period["start"]
                    end_date = period["end"]
                    lons = meta["corrected_simulated_lon"]
                    lats = meta["corrected_simulated_lat"]
                        
                    pattern_directory = pl.Path("{}/{}/{}".format(simulation_directory, model, experiment))
                    # Find files in the pattern_directory for the given regions, resolutions, and experiment
                    pattern = "*_{}_{}_{}_*_{}_*.nc".format(var, region, resolution, experiment)
                    files = np.sort(list(pattern_directory.glob(pattern)))
                    
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=xr.SerializationWarning)
                        try:
                            with xr.open_dataset(files[0]) as dataset:
                                # Check whether the latitude and longitude need to be renamed
                                if "latitude" in dataset.coords and "longitude" in dataset.coords:
                                    dataset = dataset.rename({"latitude": "lat", "longitude": "lon"})

                                lon_indices = []
                                for lon in lons:
                                    lon_diff = np.abs(dataset.coords["lon"].values - lon)
                                    lon_index = np.where(lon_diff == np.min(lon_diff))[0][0]
                                    lon_indices.append(lon_index)
                                lat_indices = []
                                for lat in lats:
                                    lat_diff = np.abs(dataset.coords["lat"].values - lat)
                                    lat_index = np.where(lat_diff == np.min(lat_diff))[0][0]
                                    lat_indices.append(lat_index)

                        except ValueError as e:
                            if "unable to decode time units" in str(e):
                                print("\t\t\t\t\t**Decoding times failed, loading with decode_times=False.**")

                                with xr.open_dataset(files[0], decode_times=False) as dataset:

                                    # Extract the time units and values
                                    time_units = dataset.time.attrs['units']
                                    time_values = dataset.time.values
                                    
                                    # Calculate new time values using the base date from the units
                                    base_date = pd.to_datetime(time_units.split('since ')[-1])
                                    new_time = base_date + pd.to_timedelta(time_values, unit='D')
                                    
                                    # Replace the time coordinate
                                    dataset = dataset.assign_coords(time=new_time)

                                    # Check whether the latitude and longitude need to be renamed
                                    if "latitude" in dataset.coords and "longitude" in dataset.coords:
                                        dataset = dataset.rename({"latitude": "lat", "longitude": "lon"})

                                    lon_indices = []
                                    for lon in lons:
                                        lon_diff = np.abs(dataset.coords["lon"].values - lon)
                                        lon_index = np.where(lon_diff == np.min(lon_diff))[0][0]
                                        lon_indices.append(lon_index)
                                    lat_indices = []
                                    for lat in lats:
                                        lat_diff = np.abs(dataset.coords["lat"].values - lat)
                                        lat_index = np.where(lat_diff == np.min(lat_diff))[0][0]
                                        lat_indices.append(lat_index)
                            else:
                                raise e

                    var_name = "discharge" if var == "q" else var                    
                    exists = True
                    overwrite = True

                    for i, (index, row) in enumerate(meta.iterrows()):
                        # Define the base path
                        base_path = pl.Path("{}/{}/{}/{}/{}/{}/data/".format(output_directory, model, var, experiment, region, resolution))
                        file_out = base_path / f"{var_name}_{index}.parquet"

                        if not file_out.exists():
                            exists = False
                            break

                    # Check if the file already exists and overwrite is not enabled
                    if not overwrite and file_out.exists():
                        print("\t\t\t\t\t\t File {} already exists".format(file_out))
                        continue

                    # Initialize variables for the current gauge
                    vars = []
                    dates_list = []
                    
                    # Loop over the simulation files
                    for j, var_file in enumerate(files):
                        with warnings.catch_warnings():
                            warnings.filterwarnings("ignore", category=xr.SerializationWarning)
                            
                            try: 
                                with xr.open_dataset(var_file) as dataset:
                                    dates = convert_dates(dataset.indexes["time"])
                                    print("\t\t\t\t\t\t> {} converted to daily.".format(var_file.stem))

                            except ValueError as e:
                                if "unable to decode time units" in str(e):
                                    print("\t\t\t\t\t**Decoding times failed, loading with decode_times=False.**")

                                    with xr.open_dataset(var_file, decode_times=False) as dataset:
                                        
                                        # Extract the time units and values
                                        time_units = dataset.time.attrs['units']
                                        time_values = dataset.time.values
                                        
                                        # Calculate new time values using the base date from the units
                                        base_date = pd.to_datetime(time_units.split('since ')[-1])
                                        new_time = base_date + pd.to_timedelta(time_values, unit='D')
                                        
                                        # Replace the time coordinate
                                        dataset = dataset.assign_coords(time=new_time)

                                        dates = convert_dates(dataset.indexes["time"])
                                        print("\t\t\t\t\t\t> {} converted to daily.".format(var_file.stem))
                                else:
                                    raise e

                        # Check if the file is within the date range
                        if max(dates) < start_date or min(dates) > end_date:
                            continue

                        print("\t\t\t\t\t\t>> File: {} ({} out of {})".format(var_file.stem, j, len(files)))

                        # Select the date range and sort the dataset
                        with warnings.catch_warnings():
                            warnings.filterwarnings("ignore", category=xr.SerializationWarning)

                            try:
                                with xr.open_dataset(var_file) as dataset:
                                    date_slice = slice(str(start_date), str(end_date))
                                    dataset = dataset.sel(time=date_slice)
                                    dataset = dataset.sortby("time")
                                    selected_variable = dataset[var]

                            except ValueError as e:
                                if "unable to decode time units" in str(e):
                                    print("\t\t\t\t\t**Decoding times failed, loading with decode_times=False.**")

                                    with xr.open_dataset(var_file, decode_times=False) as dataset:

                                        # Extract the time units and values
                                        time_units = dataset.time.attrs['units']
                                        time_values = dataset.time.values
                                        
                                        # Calculate new time values using the base date from the units
                                        base_date = pd.to_datetime(time_units.split('since ')[-1])
                                        new_time = base_date + pd.to_timedelta(time_values, unit='D')
                                        
                                        # Replace the time coordinate
                                        dataset = dataset.assign_coords(time=new_time)

                                        date_slice = slice(str(start_date), str(end_date))
                                        dataset = dataset.sel(time=date_slice)
                                        dataset = dataset.sortby("time")
                                        selected_variable = dataset[var]
                                else:
                                    raise e

                        # Collect variable data and dates
                        vars.append(selected_variable.values[:, lat_indices, lon_indices])
                        dates = convert_dates(selected_variable.indexes["time"])
                        dates_list.append(dates)

                    # Concatenate all data and dates
                    selected_variable = np.concatenate(vars, axis=0)
                    dates = np.concatenate(dates_list, axis=0)

                    for i, (index, row) in enumerate(meta.iterrows()):
                        # Define the base path
                        base_path = pl.Path("{}/{}/{}/{}/{}/{}/data/".format(output_directory, model, var, experiment, region, resolution))
                        file_out = base_path / f"{var_name}_{index}.parquet"

                        # Create a dataframe for the current gauge
                        selected_variable_df = {"date": dates, var_name: selected_variable[:, i]}
                        selected_variable_df = pd.DataFrame(selected_variable_df)
                        selected_variable_df = selected_variable_df.astype({"date": "datetime64[ns]", var_name: "float32"})
                        selected_variable_df = selected_variable_df.sort_values("date")

                        # Create the parent directory if it doesn't exist
                        file_out.parent.mkdir(parents=True, exist_ok=True)

                        # Save the dataframe to a parquet file
                        selected_variable_df.to_parquet(file_out)
                        print("\t\t\t\t\t=> Dataframe saved to {}".format(file_out))

                # Final print statement indicating how many gauges were processed
                print("\t\t\t\t- Saved {} gauges from {} simulation files".format(meta.index.size, len(vars)))

    print("\tPreprocessing of {} simulated data is done!".format(model))

print("\nPreprocessing of all simulated data is done!")
