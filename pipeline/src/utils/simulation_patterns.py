"""
simulation_patterns.py

Parses the simulation file names of the tier-2 tree into a table (one row per file):
model, meteo (forcing), variable, region, resolution, temporal resolution,
experiment, start and end date, and the experiment folder ("misc"). File names
follow {model}_{forcing}_{variable}_{region}_{res}_{step}_{experiment}_{start}_{end}.nc,
or {model}_{forcing}_{mask|uparea}_{region}_{res}.nc for static files.

Inputs:  a folder <root>/simulations/<model>/<experiment>/
Outputs: (DataFrame of patterns, list of file names that do not match)
Used by steps 2 and 6.

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
import glob
import os
import pandas as pd

def extract_simulation_patterns(
    simulation_directory,
    exclude_experiments_startswith=None,
    exclude_experiments_list=None
):
    # Find all .nc files in the directory
    file_paths = glob.glob(f"{simulation_directory}/**/*.nc", recursive=True)
    file_paths = sorted(file_paths)

    simulation_patterns = []
    invalid_files = []

    for file_path in file_paths:
        # Split path into parts
        path_parts = file_path.strip("/").split("/")
        
        # Find model and experiment folders
        try:
            simulations_index = path_parts.index("simulations")
            model = path_parts[simulations_index + 1].lower()
            experiment = path_parts[simulations_index + 2].lower()
        except (ValueError, IndexError):
            # If folder structure doesn't match, skip this file
            invalid_files.append(file_path)
            continue

        # Exclusion logic (before reading filename)
        exclude = False
        if exclude_experiments_startswith:
            if experiment.startswith(exclude_experiments_startswith.lower()):
                exclude = True

        if exclude_experiments_list:
            if experiment in [e.lower() for e in exclude_experiments_list]:
                exclude = True

        if exclude:
            continue

        # Process filename
        file_name = os.path.basename(file_path)
        components = file_name.split('_')
        
        if len(components) >= 9:
            simulation_patterns.append({
                "model": components[0].lower(),
                "meteo": components[1].lower(),
                "variable": components[2].lower(),
                "region": components[3].lower(),
                "resolution": components[4],
                "temp_res": components[5],
                "experiment": experiment,
                "start_date": components[7],
                "end_date": components[8].split('.')[0],
                "misc": path_parts[-2]  # experiment folder
            })

        elif len(components) == 5:
            simulation_patterns.append({
                "model": components[0].lower(),
                "meteo": components[1].lower(),
                "variable": components[2].lower(),
                "region": components[3].lower(),
                "resolution": components[4].split('.')[0],
                "temp_res": None,
                "experiment": experiment,
                "start_date": None,
                "end_date": None,
                "misc": path_parts[-2]
            })
        else:
            invalid_files.append(file_name)

    # Convert to DataFrame and sort if there are valid patterns
    if simulation_patterns:
        simulation_patterns_df = pd.DataFrame(simulation_patterns)
        simulation_patterns_df = simulation_patterns_df.sort_values(
            by=["model", "experiment", "variable", "region", "resolution", "start_date"]
        ).reset_index(drop=True)
    else:
        simulation_patterns_df = pd.DataFrame()
        print("No valid patterns found in the filenames.")

    return simulation_patterns_df, invalid_files
