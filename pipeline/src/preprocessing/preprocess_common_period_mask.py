"""
preprocess_common_period_mask.py  (step 2)

Common simulation period and common mask of each experiment, variable and region:
the period is the overlap of all model simulations of the experiment, the mask is
the overlap of their discharge masks on the finest grid.

Inputs:  <root>/simulations/<model>/<experiment>/*.nc (file names parsed by utils/simulation_patterns.py)
Outputs: <save tree>/common/<experiment>/<variable>/<region>/period.csv and mask.nc
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).

Usage (existing outputs are kept unless --overwrite is given):
    python preprocess_common_period_mask.py                         # all experiments
    python preprocess_common_period_mask.py --experiment exp35,exp36
    python preprocess_common_period_mask.py --experiment exp35 --overwrite

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
#%% Import necessary libraries
# Standard library imports
import os
import sys
import glob
import argparse
import warnings
import datetime as dt
import pathlib as pl

# Third-party imports
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from IPython.display import display

# Local imports
# Add the src directory to the path for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.simulation_patterns import extract_simulation_patterns

#%% Command line options (defaults keep the original behaviour)
parser = argparse.ArgumentParser(description="Common simulation period and mask.")
parser.add_argument("--experiment", default=None, help="Comma-separated experiments, e.g. exp35,exp36 (default: all)")
parser.add_argument("--overwrite", action="store_true", help="Rewrite existing period.csv/mask.nc of the selected experiments")
args, _ = parser.parse_known_args()
selected_experiments = [e.strip() for e in args.experiment.split(",") if e.strip()] if args.experiment else None

#%% Define the directories and file paths
tier1_directory = pl.Path("/data/4dhydro/data/processed/tier1/")
tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))

observation_directory = pl.Path(f"{tier1_directory}/observations/")
simulation_directory = pl.Path(f"{tier2_directory}/simulations/")
desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")
output_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/common/")

# Geographical extents
extents = {
    "europe": [-11, 33, 42, 73],
    "rhine": [3, 46, 13, 53],
    "po": [6, 43, 13, 47],
    "tugela": [28, -30, 32, -27],
}

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
# GEOframe exp10 is left out (partner request)
simulation_patterns = simulation_patterns[~((simulation_patterns["model"] == "geoframe") & (simulation_patterns["experiment"] == "exp10"))]

#%% Simulation periods
simulation_periods = {}

# Iterate over unique experiments
unique_experiments = simulation_patterns["experiment"].unique()
# Drop the None value from the unique experiments
unique_experiments = unique_experiments[~pd.isnull(unique_experiments)]
unique_experiments = sorted(unique_experiments)
# Keep only the experiments given on the command line (if any)
if selected_experiments:
    missing = [e for e in selected_experiments if e not in unique_experiments]
    if missing:
        print("Experiments not found in simulation patterns: {}".format(missing))
    unique_experiments = [e for e in unique_experiments if e in selected_experiments]
print("Unique experiments: {}".format(unique_experiments))

for experiment in unique_experiments:
    print("Experiment: {}".format(experiment))

    # Filter patterns for the current experiment
    experiment_patterns = simulation_patterns[simulation_patterns["experiment"] == experiment]

    # Unique patterns of models, meteo, variable, region, resolution and experiment
    unique_patterns = experiment_patterns[["model", "meteo", "variable", "region", "resolution", "experiment"]].drop_duplicates()

    # Drop rows with variable 'mask' and 'uparea'
    unique_patterns = unique_patterns[~unique_patterns["variable"].isin(["mask", "uparea"])]

    # Reset the index of the DataFrame
    unique_patterns = unique_patterns.reset_index(drop=True)
    print("Unique patterns: {} in {}".format(unique_patterns.shape[0], experiment))
    
    # Iterate over unique variables within the filtered patterns
    for var in sorted(unique_patterns["variable"].unique()):
        print("\t Variable: {}".format(var))

        var_patterns = unique_patterns[unique_patterns["variable"] == var]  # Use var_patterns to avoid overwriting unique_patterns
        print("\t Unique patterns: {} in {} and {}".format(var_patterns.shape[0], var, experiment))

        # Iterate over unique regions within the filtered patterns
        for region in sorted(experiment_patterns["region"].unique()):
            print("\t\t Region: {}".format(region))

            # Filter patterns for the current variable, region and experiment
            region_sel = var_patterns["region"] == region

            if region != "tugela":
                region_sel = np.logical_or(region_sel, var_patterns["region"] == "europe")
            region_patterns = var_patterns.loc[region_sel]

            # Initialize the dictionary for the current experiment if not already done
            if experiment not in simulation_periods:
                simulation_periods[experiment] = {}

            # Initialize the dictionary for the current variable if not already done
            if var not in simulation_periods[experiment]:
                simulation_periods[experiment][var] = {}

            # Initialize the dictionary for the current region
            simulation_periods[experiment][var][region] = {}

            # Iterate over region patterns
            for pattern_index, fields in region_patterns.iterrows():
                # Construct pattern name
                pattern_name = f"{fields['model']}_{fields['meteo']}_{fields['variable']}_{fields['region']}_{fields['resolution']}_{fields['experiment']}"
                print("\t\t\t - Pattern: {}".format(pattern_name))

                # Find this pattern in the simulation_patterns
                pattern_sel = (simulation_patterns["model"] == fields["model"]) & \
                                (simulation_patterns["meteo"] == fields["meteo"]) & \
                                (simulation_patterns["variable"] == fields["variable"]) & \
                                (simulation_patterns["region"] == fields["region"]) & \
                                (simulation_patterns["resolution"] == fields["resolution"]) & \
                                (simulation_patterns["experiment"] == fields["experiment"])
                
                pattern = simulation_patterns.loc[pattern_sel]

                # Convert start and end dates to datetime using .loc to avoid SettingWithCopyWarning
                pattern.loc[:, 'start_date'] = pd.to_datetime(pattern['start_date'], format='%Y%m%d')
                pattern.loc[:, 'end_date'] = pd.to_datetime(pattern['end_date'], format='%Y%m%d')

                # Min and max of start and end dates
                min_start_dates = pattern['start_date'].min().strftime('%Y-%m-%d')
                max_end_dates = pattern['end_date'].max().strftime('%Y-%m-%d')

                # Store the simulation period in the nested dictionary
                simulation_periods[experiment][var][region][pattern_name] = {
                    "start": min_start_dates,
                    "end": max_end_dates
                }

                print("\t\t\t - Simulation period: {} to {}".format(min_start_dates, max_end_dates))

#%% Common simulation periods
common_periods = {}
print("")

# Determine the common periods for each variable and region
for experiment in simulation_periods:
    print("Experiment: {}".format(experiment))

    # Initialize the dictionary for the current experiment if not already done
    if experiment not in common_periods:
        common_periods[experiment] = {}

    # Iterate over variables
    for var in simulation_periods[experiment]:
        print("\t Variable: {}".format(var))

        # Initialize the dictionary for the current variable if not already done
        if var not in common_periods[experiment]:
            common_periods[experiment][var] = {}

        # Iterate over regions
        for region in simulation_periods[experiment][var]:
            print("\t\t Region: {}".format(region))

            # Initialize the dictionary for the current region if not already done
            if region not in common_periods[experiment][var]:
                common_periods[experiment][var][region] = {}

            # Get the simulation periods for the current variable and region
            periods = simulation_periods[experiment][var][region]

            if len(periods) == 0:
                print("\t\t\t - No overlapping periods found / No patterns found")
                continue

            # Get the start and end dates for each pattern
            start_dates = [dt.datetime.strptime(periods[pattern]["start"], '%Y-%m-%d') for pattern in periods]
            end_dates = [dt.datetime.strptime(periods[pattern]["end"], '%Y-%m-%d') for pattern in periods]

            # Determine the common start and end dates
            common_start_date = max(start_dates).strftime('%Y-%m-%d')
            common_end_date = min(end_dates).strftime('%Y-%m-%d')

            # Store the common period in the nested dictionary
            common_periods[experiment][var][region] = {
                "start": common_start_date,
                "end": common_end_date
            }

            print("\t\t\t - Overlapping period: {} to {}".format(common_start_date, common_end_date))

#%% Simulation masks
simulation_masks = {}

for experiment in unique_experiments:
    print("Experiment: {}".format(experiment))

    # Filter patterns for the current experiment
    experiment_patterns = simulation_patterns[simulation_patterns["experiment"] == experiment]

    var = "q"

    # Filter patterns for the current variable
    var_patterns = experiment_patterns[experiment_patterns["variable"] == var]

    for region in sorted(var_patterns["region"].unique()):
        print("\t\t Region: {}".format(region))

        extent = extents[region]
        
        region_sel = var_patterns["region"] == region
        if region != "tugela":
            region_sel = np.logical_or(region_sel, var_patterns["region"] == "europe")
        region_patterns = var_patterns.loc[region_sel]
        
        # Initialize the dictionary for the current experiment if not already done
        if experiment not in simulation_masks:
            simulation_masks[experiment] = {}

        # Initialize the dictionary for the current region if not already done
        if region not in simulation_masks[experiment]:
            simulation_masks[experiment][region] = {}

        # Creat a pandas dataframe for the unique models and distinct patterns from the region patterns
        selected_patterns = region_patterns[["model", "meteo", "region", "resolution", "experiment"]].drop_duplicates()
        selected_patterns = selected_patterns.sort_values(by="resolution", ascending=False)

        # Iterate over region patterns
        for pattern_index, fields in selected_patterns.iterrows():
            # Construct mask name
            mask_name = f"{fields['model']}_{fields['meteo']}_mask_{fields['region']}_{fields['resolution']}"
            print("\t\t\t - Mask: {}".format(mask_name))

            # Drop "mask" part from the mask name
            pattern = mask_name.replace("_mask", "")
            
            # Initialize the dictionary for the current region
            simulation_masks[experiment][region][pattern] = {}
        
            pattern_directory = pl.Path("{}/{}/{}".format(simulation_directory, fields['model'], fields['experiment']))

            mask_file = pattern_directory / f"{mask_name}.nc"

            # Check if mask file exists
            if not mask_file.exists():
                print("\t\t\t -> Mask file not found <-")

                # Determining the first netcdf file in the pattern_directory for the variable q

                if fields['model'] == "geoframe":
                    pattern_files = list(sorted(pattern_directory.glob(f"*_et_{fields['region']}_{fields['resolution']}_*.nc")))
                    var_file = pattern_files[0]
                else:    
                    pattern_files = list(sorted(pattern_directory.glob(f"*_{var}_{fields['region']}_{fields['resolution']}_*.nc")))
                    var_file = pattern_files[0]
            
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=xr.SerializationWarning)
                    
                    try:
                        # First try to open normally
                        with xr.open_dataset(var_file) as dataset:
                            lat_slice = slice(extent[1], extent[3])
                            lon_slice = slice(extent[0], extent[2])

                            # Check whether the latitude and longitude need to be renamed
                            if "latitude" in dataset.coords and "longitude" in dataset.coords:
                                dataset = dataset.rename({"latitude": "lat", "longitude": "lon"})

                            if dataset.lat.values[0] > dataset.lat.values[-1]:
                                lat_slice = slice(extent[3], extent[1])
                            if dataset.lon.values[0] > dataset.lon.values[-1]:
                                lon_slice = slice(extent[2], extent[0])
                            
                            dataset = dataset.sel(lat=lat_slice,
                                                lon=lon_slice).isel(time = 0)
                            if fields['model'] == "geoframe":
                                mask = dataset.data_vars["et"]
                            else:
                                mask = dataset.data_vars["q"]
                            
                    except ValueError as e:
                        # If we get the time decoding error, try again with decode_times=False
                        if "Failed to decode variable 'time'" in str(e):
                            with xr.open_dataset(var_file, decode_times=False) as dataset:
                                lat_slice = slice(extent[1], extent[3])
                                lon_slice = slice(extent[0], extent[2])
                            
                                # Check whether the latitude and longitude need to be renamed
                                if "latitude" in dataset.coords and "longitude" in dataset.coords:
                                    dataset = dataset.rename({"latitude": "lat", "longitude": "lon"})

                                if dataset.lat.values[0] > dataset.lat.values[-1]:
                                    lat_slice = slice(extent[3], extent[1])
                                if dataset.lon.values[0] > dataset.lon.values[-1]:
                                    lon_slice = slice(extent[2], extent[0])
                                
                                dataset = dataset.sel(lat=lat_slice,
                                                    lon=lon_slice).isel(time = 0)

                                if fields['model'] == "geoframe":
                                    mask = dataset.data_vars["et"]
                                else:
                                    mask = dataset.data_vars[var]

                                    # Soilmoisture mask
                                    if "depth" in mask.dims:
                                        mask = mask.isel(depth = 0)
                        else:
                            # If it's a different ValueError, raise it
                            raise

                mask = mask * 0 + 1
                
            else:
                # Get mask from mask file
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=xr.SerializationWarning)
                    
                    with xr.open_dataset(mask_file) as dataset:
                        lat_slice = slice(extent[1], extent[3])
                        lon_slice = slice(extent[0], extent[2])

                        # Check whether the latitude and longitude need to be renamed
                        if "latitude" in dataset.coords and "longitude" in dataset.coords:
                            dataset = dataset.rename({"latitude": "lat", "longitude": "lon"})
                    
                        if dataset.lat.values[0] > dataset.lat.values[-1]:
                            lat_slice = slice(extent[3], extent[1])
                        if dataset.lon.values[0] > dataset.lon.values[-1]:
                            lon_slice = slice(extent[2], extent[0])
                        
                        dataset = dataset.sel(lat=lat_slice,
                                            lon=lon_slice)
                        mask = dataset.data_vars["mask"]
                        
            pattern_mask = ~np.logical_or(np.isnan(mask), mask <= 0)
            
            simulation_masks[experiment][region][pattern] = pattern_mask
            
            print("\t\t\t - Mask: {} out of {}".format(pattern_mask.to_numpy().sum(),
                                                pattern_mask.to_numpy().size))

#%% Common simulation masks
common_masks = {}
print("")

# Determine the common masks for each variable and region
for experiment in simulation_masks:
    print("Experiment: {}".format(experiment))

    # Initialize the dictionary for the current experiment if not already done
    if experiment not in common_masks:
        common_masks[experiment] = {}

        # Iterate over regions
        for region in simulation_masks[experiment]:
            print("\t\t Region: {}".format(region))

            # Initialize the dictionary for the current region if not already done
            if region not in common_masks[experiment]:
                common_masks[experiment][region] = {}
           
            extent = extents[region]

            # Variables to track the finest resolution and bounding box
            min_mask = None
            min_resolution = None
            min_lon, max_lon = None, None
            min_lat, max_lat = None, None

            for pattern_name, mask in simulation_masks[experiment][region].items():
                lon_vals = mask.coords["lon"].values
                lat_vals = mask.coords["lat"].values
                resolution = lon_vals[1] - lon_vals[0]

                # Update the mask with the finest resolution
                if min_resolution is None or resolution < min_resolution:
                    min_resolution = resolution
                    min_mask = mask            
                
                # Update bounding box extents
                if min_lon is None or lon_vals.min() > min_lon:
                    min_lon = lon_vals.min()
                if max_lon is None or lon_vals.max() < max_lon:
                    max_lon = lon_vals.max()
                if min_lat is None or lat_vals.min() > min_lat:
                    min_lat = lat_vals.min()
                if max_lat is None or lat_vals.max() < max_lat:
                    max_lat = lat_vals.max()

            # Ensure min_mask is sliced to the common extent     
            common_mask = None
            for pattern_name, mask in simulation_masks[experiment][region].items():
                lat_slice = slice(min_lat, max_lat)
                lon_slice = slice(min_lon, max_lon)
                
                if mask.lat.values[0] > mask.lat.values[-1]:
                    lat_slice = slice(max_lat, min_lat)
                if mask.lon.values[0] > mask.lon.values[-1]:
                    lon_slice = slice(max_lon, min_lon)
                    
                mask = mask.sel(lat=lat_slice,
                                lon=lon_slice)
                mask = mask.astype("float")
                mask = mask.interp(coords = {"lat": min_mask.coords["lat"],
                                            "lon": min_mask.coords["lon"]},
                                method = "linear")
                mask.values[mask.values < 1.0] = 0.0
                mask.values[np.isnan(mask.values)] = 0.0
                
                if common_mask is None:
                    common_mask = mask
                else:
                    common_mask = np.logical_and(common_mask, mask)
            
            common_mask = common_mask.rename("mask")
            common_masks[experiment][region] = common_mask
            print("\t\t\t - Common mask created with resolution: {} for region: {}".format(min_resolution, region))
            
            print(common_mask.plot())
            plt.title(region)
            plt.show()
            print("- Mask: {} out of {}".format(common_mask.to_numpy().sum(),
                                                common_mask.to_numpy().size))
            
#%% Save the common periods to a csv file
print("")
overwrite = False  # Change this to True if you want to allow overwriting
overwrite = overwrite or args.overwrite

for experiment in common_periods:
    print("Experiment: {}".format(experiment))

    for var in common_periods[experiment]:
        print("\t Variable: {}".format(var))

        for region in common_periods[experiment][var]:
            print("\t\t Region: {}".format(region))

            period = common_periods[experiment][var][region]
            
            if len(period) == 0:
                print("\t\t\t - No overlapping periods found / No patterns found")
                continue
            
            # Save the common period to a CSV file
            period_out = pl.Path(f"{output_directory}/{experiment}/{var}/{region}/period.csv")
            period_out.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists and if overwrite is allowed
            if not period_out.exists() or overwrite:
                # Convert the period dictionary to a DataFrame for saving
                period_df = pd.DataFrame([period])
                period_df.to_csv(period_out, index=False)
                print(f"\t\t\t - Overlapping period: {period['start']} to {period['end']} saved in {period_out}")
            else:
                print(f"\t\t\t - File already exists: {period_out} (overwrite is set to False)")

            mask = common_masks[experiment][region]
            mask_out = pl.Path(f"{output_directory}/{experiment}/{var}/{region}/mask.nc")
            mask_out.parent.mkdir(parents=True, exist_ok=True)

            if not mask_out.exists() or overwrite:
                mask.to_netcdf(mask_out)
                print(f"<<< Common mask is saved in this directory {mask_out} >>>")
            else:
                print(f"<<< File already exists: {mask_out} (overwrite is set to False) >>>")