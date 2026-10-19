"""
preprocess_observed_data.py  (step 4)

Reads the daily discharge series of the selected gauges from the original
provider formats (GRDC, ARPA Emilia-Romagna, Trento, CAMELS-CH, CAMELS-GB, DWS,
LamaH), removes negative and missing values and cuts them to the common period.

Inputs:  <save tree>/observations/<experiment>/q/<region>/meta.parquet
         <save tree>/common/<experiment>/q/<region>/period.csv
         /data/4dhydro/data/processed/tier1/observations/q/<provider>/data/...
Outputs: <save tree>/observations/<experiment>/q/<region>/data/discharge_<gauge>.parquet
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).

Usage (without options the WRR2 experiment list below is processed):
    python preprocess_observed_data.py --experiment exp35,exp36
    python preprocess_observed_data.py exp35

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""

#%% Import libraries
import os
import pathlib as pl
import warnings
import datetime as dt
import re
import numpy as np
import pandas as pd
import argparse

#%% Functions
def preprocess_discharge_data(experiment_id):
    """Preprocess observed discharge data."""
    desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")
    tier1_directory = pl.Path("/data/4dhydro/data/processed/tier1/")
    tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))
    common_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/common/{experiment_id}/q")
    observations_directory = pl.Path(f"{tier1_directory}/observations/q")
    output_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/observations/{experiment_id}/q")
    save_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/observations/{experiment_id}/q")

    # Get sorted list of regions
    regions = sorted([dir.stem for dir in save_directory.iterdir() if dir.is_dir()])

    for region in regions:
        print(f"Region: {region}")

        save_region_directory = save_directory / region
        common_region_directory = common_directory / region

        meta_file = save_region_directory / "meta.parquet"
        meta = pd.read_parquet(meta_file)

        period_file = common_region_directory / "period.csv"
        period = pd.read_csv(period_file, parse_dates=["start", "end"]).iloc[0]

        exists = all((output_directory / region / f"data/discharge_{index}.parquet").exists() for index, _ in meta.iterrows())
        
        if exists:
            print("- Already exists")
            continue

        for i, (index, row) in enumerate(meta.iterrows()):
            discharge_out = output_directory / region / f"data/discharge_{index}.parquet"

            if discharge_out.exists():
                continue

            row_type = row["type"]
            row_id = row["id"]

            type_directory = observations_directory / row_type
            data_directory = type_directory / "data"

            # Load discharge data based on the row type
            discharge = load_discharge_data(row_type, row_id, data_directory)

            # Drop NaN values and convert types
            discharge = discharge.dropna(axis=0)
            discharge = discharge.astype({"date": "datetime64[ns]", "discharge": "float32"})
        
            # Subset overlap period
            discharge_sel = (discharge["date"] >= period["start"]) & (discharge["date"] <= period["end"])
            discharge = discharge.loc[discharge_sel]

            discharge_out.parent.mkdir(parents=True, exist_ok=True)
            discharge.to_parquet(discharge_out)

            print(f"- Processed gauge {index} ({i + 1} out of {meta.index.size})")
        print(f"Meta data of region: {region}")

    print("")

def load_discharge_data(row_type, row_id, data_directory):
    """Load discharge data based on the gauge type."""
    if row_type == "GRDC":
        data_file = data_directory / f"{row_id}_Q_Day.Cmd.txt"
        discharge = pd.read_csv(data_file, delimiter=";", encoding="ISO-8859-1", comment="#")
        discharge.columns = ["date", None, "discharge"]
        discharge = discharge[["date", "discharge"]]

        discharge["date"] = pd.to_datetime([dt.datetime.strptime(date, "%Y-%m-%d").date() for date in discharge["date"]])
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan
    
    elif row_type == "Arpa_Emilia_Romagna":
        data_file = data_directory / f"{row_id}.csv"
        discharge = pd.read_csv(data_file, skiprows=3, on_bad_lines="skip")
        discharge = discharge.iloc[:-2]
        
        discharge.columns = [None, "date", "discharge"]
        discharge = discharge[["date", "discharge"]]
        
        discharge["date"] = pd.to_datetime([dt.datetime.strptime(re.sub("\\+00:00", "", date), "%Y-%m-%d %H:%M:%S").date() for date in discharge["date"]])
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan
        
    elif row_type == "Trento":
        data_file = data_directory / "discharge_po_river.csv"
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)
            discharge = pd.read_csv(data_file, skiprows=2, header=1).iloc[3:]
        discharge.columns = [c.strip() for c in discharge.columns]
        id_name = f"value_{row_id}"
        discharge = discharge[["timestamp", id_name]]
        discharge.columns = ["date", "discharge"]
        
        discharge["date"] = pd.to_datetime([dt.datetime.strptime(date, "%Y-%m-%d %H:%M").date() for date in discharge["date"]])
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan

    elif row_type == "CAMELS-CH":
        data_file = data_directory.parent / f"time_series/observation_based/CAMELS_CH_obs_based_{row_id}.csv"
        discharge = pd.read_csv(data_file, sep = ";")
        discharge = discharge[["date", "discharge_vol(m3/s)"]]
        discharge.columns = ["date", "discharge"]
        
        discharge["date"] = pd.to_datetime([dt.datetime.strptime(date, "%Y-%m-%d").date() for date in discharge["date"]])
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan

    elif row_type == "CAMELS-GB":
        data_file = data_directory / f"timeseries/CAMELS_GB_hydromet_timeseries_{row_id}_19701001-20150930.csv"
        discharge = pd.read_csv(data_file)
        discharge = discharge[["date", "discharge_vol"]]
        discharge.columns = ["date", "discharge"]
        
        discharge["date"] = pd.to_datetime([dt.datetime.strptime(date, "%Y-%m-%d").date() for date in discharge["date"]])
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan

    elif row_type == "DWS":
        data_file = data_directory / f"{row_id}.csv"
        discharge = pd.read_csv(data_file, skiprows=4, header = None)
        discharge.columns = ["Date","Level (Metres)", "","Cor.Lev. (Metres)", "","Discharge (Cumecs) Final flow", ""]
        discharge = discharge[["Date", "Discharge (Cumecs) Final flow"]]
        discharge.columns = ["date", "discharge"]
        
        discharge["date"] = pd.to_datetime([dt.datetime.strptime(str(date), "%Y%m%d").date() for date in discharge["date"]])
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan
        
    elif row_type == "LamaH":
        data_file = data_directory.parent / f"D_gauges/2_timeseries/daily/ID_{row_id}.csv"
        discharge = pd.read_csv(data_file, sep = ";")
        discharge["date"] = pd.to_datetime([dt.date(r["YYYY"], r["MM"], r["DD"]) for _, r in discharge[["YYYY", "MM", "DD"]].iterrows()])
        discharge = discharge[["date", "qobs"]]
        discharge.columns = ["date", "discharge"]
        
        discharge["discharge"] = pd.to_numeric(discharge["discharge"], errors = "coerce")
        discharge.loc[discharge["discharge"] < 0, "discharge"] = np.nan

    else:
        raise ValueError(f"Unknown discharge meta type {row_type}")

    return discharge

#%% Run the script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess observed discharge data.")
    parser.add_argument(
        "experiment_id", 
        type=str, 
        nargs="?", 
        default=None, 
        help="The ID of the experiment to process. If not provided, all experiments will be processed."
    )
    parser.add_argument(
        "--experiment",
        type=str,
        default=None,
        help="Comma-separated experiments to process, e.g. exp35,exp36."
    )
    args, _ = parser.parse_known_args()

    # If --experiment is provided, process only those experiments
    if args.experiment:
        for exp_id in [e.strip() for e in args.experiment.split(",") if e.strip()]:
            preprocess_discharge_data(exp_id)
            print(f"The preprocessing discharge data for experiment {exp_id} is done.")
            print("")
    # If an experiment_id is provided, process only that experiment
    elif args.experiment_id:
        preprocess_discharge_data(args.experiment_id)
        print(f"The preprocessing discharge data for experiment {args.experiment_id} is done.")
        print("")
    else:
        # No experiment given: the experiments of WRR2
        experiment_ids = ["exp10", "exp20", "exp21", "exp30", "exp31", "exp32", "exp33", "exp34", "exp41", "exp42", "exp44"]
        for exp_id in experiment_ids:
            preprocess_discharge_data(exp_id)
            print(f"The preprocessing discharge data for experiment {exp_id} is done.")
            print("")
