"""
preprocess_average_discharge_simulations.py  (step 5)

Long-term mean discharge of each model, experiment, region and resolution (mean of
annual means), used in step 6 to match gauges to model cells.

The discharge files (*_q_*.nc) are checked first; files that cannot be opened, have
no time axis or zero-sized dimensions are reported and left out. The remaining
files are combined (if the time units cannot be decoded, the dates are rebuilt from
"<units> since <date>"), annual means are computed, every year between the first
and the last one is added (missing years as NaN), and the mean over the years is
written.

Inputs:  <root>/simulations/<model>/<experiment>/<model>_<forcing>_q_<region>_<res>_<step>_<experiment>_<start>_<end>.nc
Outputs: <root>/simulations_mya_$T2B_DESIRED_NAME/<model>/<experiment>/<model>_<forcing>_q_<region>_<res>_<step>_<experiment>_<first start>_<last end>.nc
         (an existing output is kept)
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
T2B_DESIRED_NAME defaults to eo_alternative.

Usage (comma-separated lists allowed):
    python preprocess_average_discharge_simulations.py --model mhm --experiment exp35,exp36
    python preprocess_average_discharge_simulations.py --model pcrglobwb --experiment exp30

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""

#%% Import required libraries
import pathlib as pl
import numpy as np
import pandas as pd
import xarray as xr
import argparse
import os

#%% Script configuration
tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))
simulation_directory = pl.Path(f"{tier2_directory}/simulations")
desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")  # change as needed
simulation_mya_directory = pl.Path(f"{tier2_directory}/simulations_mya_{desired_name}")
regions = ['po', 'rhine', 'tugela']

# -------- helpers --------
def check_file_ok(path: pl.Path) -> tuple[bool, str]:
    """
    Fast validation of a NetCDF file.
    Returns (ok, reason_if_bad).
    """
    try:
        # light-weight open
        with xr.open_dataset(path, decode_times=False, mask_and_scale=False, engine="netcdf4") as ds:
            # must have at least one dimension and none of them zero-sized
            if not ds.sizes:
                return False, "no dimensions"
            if any(sz == 0 for sz in ds.sizes.values()):
                return False, f"zero-sized dims: {dict(ds.sizes)}"
            # must have 'time' with length > 0 for this workflow
            if "time" not in ds.dims:
                return False, "no 'time' dimension"
            if ds.sizes.get("time", 0) == 0:
                return False, "time length == 0"
    except Exception as e:
        return False, f"failed to open: {e.__class__.__name__}: {e}"
    return True, ""

def open_combined(files: list[pl.Path]) -> xr.Dataset:
    """
    Robust open_mfdataset with fallback if time decoding fails.
    """
    try:
        return xr.open_mfdataset(
            [str(f) for f in files],
            combine="by_coords",
            data_vars="minimal",
            coords="minimal",
            compat="override",
            engine="netcdf4",
        )
    except Exception as e:
        msg = str(e).lower()
        if "decode time" in msg or "unable to decode time units" in msg:
            # fallback: open without decoding, then rebuild time
            ds = xr.open_mfdataset(
                [str(f) for f in files],
                combine="by_coords",
                data_vars="minimal",
                coords="minimal",
                compat="override",
                engine="netcdf4",
                decode_times=False,
            )
            if "time" in ds.coords:
                units = ds.time.attrs.get("units", "")
                if "since" in units:
                    unit_part, base_part = units.split("since", 1)
                    unit_part = unit_part.strip().lower()
                    base_time = pd.to_datetime(base_part.strip())
                    # map common units to pandas offset alias
                    unit_map = {
                        "days": "D", "day": "D",
                        "hours": "h", "hour": "h",
                        "minutes": "m", "minute": "m",
                        "seconds": "s", "second": "s",
                    }
                    pandas_unit = unit_map.get(unit_part, None)
                    if pandas_unit is not None:
                        # convert to float then Timedelta
                        vals = xr.DataArray(ds.time).astype("float64").values
                        new_time = base_time + pd.to_timedelta(vals, unit=pandas_unit)
                        ds = ds.assign_coords(time=("time", new_time))
                    else:
                        # last resort: let xarray try CF decode
                        ds = xr.decode_cf(ds)
            return ds
        # re-raise unrelated errors
        raise

#%% Define the main function
def main(args):
    model = args.model
    experiment = args.experiment

    subdir = f"{model}/{experiment}"
    parent_directory = simulation_directory / subdir
    if not parent_directory.is_dir():
        raise ValueError(f"Subdirectory '{subdir}' is not a valid directory.")

    print(f"Processing pattern '{subdir}'...")

    for region in regions:
        print(f"\tRegion: {region}")
        # all files for this region (any variable) just to infer available resolutions
        region_files = list(parent_directory.glob(f"*{region}*.nc"))
        if len(region_files) == 0:
            print(f"\t\tNo files found for region '{region}'. Skipping...")
            continue

        # infer resolutions from name structure: model_meteo_var_region_resolution_timestep_experiment_start_end.nc
        try:
            spatial_res = sorted(set(f.stem.split("_")[4] for f in region_files))
        except Exception:
            # if any file doesn't match expected pattern, ignore it for resolution detection
            spatial_res = sorted(set(f.stem.split("_")[4] for f in region_files if len(f.stem.split("_")) >= 9))

        for res in spatial_res:
            print(f"\t\tResolution: {res}")

            # candidate files: variable 'q' for region+res
            all_candidates = sorted(parent_directory.glob(f"*q_{region}_{res}*.nc"))
            if len(all_candidates) == 0:
                print(f"\t\t\tNo 'q' files found for {region} @ {res}. Skipping...")
                continue

            # Build patterns DF from ALL candidates (even those we may drop) so we can create the expected year index
            file_fields = [f.stem.split("_") for f in all_candidates if len(f.stem.split("_")) >= 9]
            file_patterns = pd.DataFrame(
                data=file_fields,
                index=[f.stem for f in all_candidates if len(f.stem.split("_")) >= 9],
                columns=["model","meteo","variable","region","resolution","timestep","experiment","start_date","end_date"],
            )

            # years from filenames (each file is 1 year)
            # prefer start_date; fallback to end_date if needed
            years_from_names = sorted({int(sd[:4]) for sd in file_patterns["start_date"].dropna()})
            if not years_from_names and "end_date" in file_patterns:
                years_from_names = sorted({int(ed[:4]) for ed in file_patterns["end_date"].dropna()})
            expected_index = pd.to_datetime([f"{y}-12-31" for y in years_from_names]) if years_from_names else None

            # Validate candidates
            bad = []
            good = []
            for f in all_candidates:
                ok, reason = check_file_ok(f)
                if ok:
                    good.append(f)
                else:
                    bad.append((f, reason))

            # Report status BEFORE opening
            if bad:
                print(f"\t\t\tValidating files: {len(good)} OK, {len(bad)} dropped")
                for f, why in bad[:8]:
                    print(f"\t\t\t  - drop {f.name}: {why}")
                if len(bad) > 8:
                    print(f"\t\t\t  ... and {len(bad)-8} more")
            else:
                print(f"\t\t\tValidating files: all {len(good)} OK")

            if not good:
                print(f"\t\t\tNo valid files remain for {region} @ {res}. Skipping...")
                continue

            # Generate output file name
            mya_name = "{}_{}_{}.nc".format(
                "_".join(file_patterns[["model","meteo","variable","region","resolution","timestep","experiment"]].iloc[0]),
                (file_patterns["start_date"].min() if not file_patterns["start_date"].isna().all() else "NA"),
                (file_patterns["end_date"].max() if not file_patterns["end_date"].isna().all() else "NA"),
            )
            mya_file = pl.Path(f"{simulation_mya_directory}/{model}/{experiment}/{mya_name}")

            if mya_file.exists():
                print(f"\t\t\t> Output file '{mya_name}' already exists. Skipping...")
                continue

            # ---- Open combined dataset (robust to time decode issues) ----
            dataset = open_combined(good)

            # ---- Compute annual means ----
            if "time" not in dataset.dims or dataset.sizes.get("time", 0) == 0:
                print(f"\t\t\tNo time steps in combined dataset for {region} @ {res}. Skipping...")
                continue

            annual_mean = dataset.resample(time="YE").mean(keep_attrs=True)

            # Build a matching index using the same calendar/type
            time_idx = annual_mean.indexes["time"]          # CFTimeIndex or DatetimeIndex
            start_year = int(annual_mean["time"].dt.year.min())
            end_year   = int(annual_mean["time"].dt.year.max())
            if hasattr(annual_mean.time.dt, "calendar"):    # CF calendars
                cal = annual_mean.time.dt.calendar
                # 'A-DEC' yields the correct year-end for that calendar (e.g., Dec 30 for 360_day)
                full_idx = xr.cftime_range(start=f"{start_year}-12-31",
                                        end=f"{end_year}-12-31",
                                        freq="YE-DEC",
                                        calendar=cal)
            else:                                           # Gregorian
                full_idx = pd.date_range(f"{start_year}-12-31",
                                        f"{end_year}-12-31",
                                        freq="YE-DEC")
                
            # ---- Ensure missing years appear as NaN ----
            if full_idx is not None and len(full_idx) > 0:
                # Add missing year-ends (NaN-filled); keep order stable
                annual_mean = annual_mean.reindex(time=full_idx)

            # ---- Multi-year mean (NaNs ignored by default for numeric dtypes) ----
            mean_annual_mean = annual_mean.mean(dim="time", keep_attrs=True)

            # ---- Write output ----
            if not mya_file.parent.exists():
                mya_file.parent.mkdir(parents=True, exist_ok=True)
            mean_annual_mean.to_netcdf(mya_file)
            print(f"\t\t\t> Final mean of annual average file '{mya_file}' created successfully.")

#%% Run the script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process model and experiment")
    parser.add_argument("--model", required=True, help="Model name (comma-separated list allowed)")
    parser.add_argument("--experiment", required=True, help="Experiment name (comma-separated list allowed, e.g. exp35,exp36)")
    args, _ = parser.parse_known_args()
    for model in [m.strip() for m in args.model.split(",") if m.strip()]:
        for experiment in [e.strip() for e in args.experiment.split(",") if e.strip()]:
            main(argparse.Namespace(model=model, experiment=experiment))
    print("All patterns processed successfully.")
