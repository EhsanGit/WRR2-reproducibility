"""
benchmark_performance.py  (step 8)

Compares simulated with observed discharge at every gauge and writes the scores
per model, experiment, region and resolution. Series are merged on date; gauges
with less than two years of overlap are skipped. Scores are computed for daily
and monthly means: normalised mean error, normalised RMSE, NSE, and KGE, KGE'
and non-parametric KGE with their components (hydroeval).

Inputs:  ../../resource/<patterns file> (written by step 6)
         <save tree>/observations/<experiment>/q/<region>/data/discharge_<gauge>.parquet
         <save tree>/simulations/<model>/q/<experiment>/<region>/<res>/meta.parquet and data/
Outputs: <save tree>/performance/<model>/q/<experiment>/<region>/<res>/performance.csv
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).

Usage (defaults: model mhm, experiment exp40, all regions, variable q, no overwrite):
    python benchmark_performance.py --experiment exp35,exp36 --patterns-file simulation_patterns_eo_exp35.parquet
    python benchmark_performance.py --model mhm --experiment exp35 --region rhine --overwrite

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
import argparse
import os
import pathlib as pl
import warnings
import datetime as dt
import pandas as pd
import numpy as np
import hydroeval as he

tier2_directory = pl.Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/"))
desired_name = os.environ.get("T2B_DESIRED_NAME", "eo_alternative")
observation_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/observations/")
output_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/performance/")
simulation_directory = pl.Path(f"{tier2_directory}/saves_{desired_name}/simulations/")

min_overlap = 365 * 2 # days

aggregations = {"daily": "%Y%m%d",
                "monthly": "%Y%m"}

# --- Global Configuration ---
# Set to None to process all, or provide a string/list (e.g., "exp40" or ["exp40", "exp41"])
target_model      = "mhm"           # e.g., "mhm", "None" for all
target_experiment = "exp40"        # e.g., "exp40"
target_region     = None           # e.g., "rhine"
target_variable   = "q"            # e.g., "q"
overwrites        = False          # False = skip existing; True = redo all
patterns_file     = "simulation_patterns_eo_exp40.parquet"
# ----------------------------

# Optional command line overrides (defaults = values above); comma lists allowed, "all" = None
def _cli_filter(value):
    if value.lower() in ("all", "none"):
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items[0] if len(items) == 1 else items

parser = argparse.ArgumentParser(description="Benchmark simulated discharge performance.")
parser.add_argument("--model", default=None, help="Comma-separated models or 'all' (default: mhm)")
parser.add_argument("--experiment", default=None, help="Comma-separated experiments, e.g. exp35,exp36, or 'all' (default: exp40)")
parser.add_argument("--region", default=None, help="Comma-separated regions or 'all' (default: all)")
parser.add_argument("--variable", default=None, help="Comma-separated variables or 'all' (default: q)")
parser.add_argument("--overwrite", action="store_true", help="Redo existing performance files")
parser.add_argument("--patterns-file", default=None, help="Simulation patterns file name in ../../resource/ (or an absolute path)")
cli_args, _ = parser.parse_known_args()
if cli_args.model is not None:
    target_model = _cli_filter(cli_args.model)
if cli_args.experiment is not None:
    target_experiment = _cli_filter(cli_args.experiment)
if cli_args.region is not None:
    target_region = _cli_filter(cli_args.region)
if cli_args.variable is not None:
    target_variable = _cli_filter(cli_args.variable)
overwrites = overwrites or cli_args.overwrite
if cli_args.patterns_file is not None:
    patterns_file = cli_args.patterns_file

def should_process(current_value, filter_value):
    """Helper to check if current loop item matches the user filter."""
    if filter_value is None:
        return True
    if isinstance(filter_value, list):
        return current_value in filter_value
    return current_value == filter_value

#%% Load simulation patterns (written by preprocess_simulated_metadata.py)
simulation_patterns = pd.read_parquet(pl.Path("../../resource/") / patterns_file)

#%% Save the performance of the model
# Filter the initial model list based on configuration
models = [m for m in simulation_patterns.model.unique() if should_process(m, target_model)]
# Print Header for Model
for model in models:
    # --- Level 1 Header: Model ---
    # Using a clear, distinct separator for the top level
    print("="*60)
    print(f"MODEL: {model}")
    print("="*60)

    # Filter variables
    available_vars = simulation_patterns[simulation_patterns.model == model].variable.unique()
    vars_to_run = [v for v in available_vars if should_process(v, target_variable)]

    for var in vars_to_run:
        # --- Level 2 Header: Variable ---
        print(f"\n\t--- VARIABLE: {var} ---")

        # Filter experiments
        available_exps = simulation_patterns[(simulation_patterns.model == model) & (simulation_patterns.variable == var)].experiment.unique()
        exps_to_run = [e for e in available_exps if should_process(e, target_experiment)]
        exps_to_run = np.sort(exps_to_run)


        for experiment in exps_to_run:
            # --- Level 3 Header: Experiment ---
            print(f"\t\tEXPERIMENT: {experiment}")
            model_var_exp_directory = pl.Path("{}/{}/{}/{}".format(simulation_directory, model, var, experiment))
            if not model_var_exp_directory.exists():
                continue
            
            # Filter regions
            available_regions = [dir.stem for dir in model_var_exp_directory.iterdir() if dir.is_dir()]
            regions_to_run = [r for r in available_regions if should_process(r, target_region)]
            regions_to_run = sorted(regions_to_run)


            for region in regions_to_run:    
                # --- Level 4 Header: Region ---
                print(f"\t\t\tREGION: {region}")

                model_var_exp_region_directory = pl.Path("{}/{}/".format(model_var_exp_directory, region))
                resolutions = [dir.stem for dir in model_var_exp_region_directory.iterdir() if dir.is_dir()]
                resolutions = sorted(resolutions)
                
                for resolution in resolutions:
                    # --- Level 5 Header: Resolution ---
                    print(f"\t\t\t\tRESOLUTION: {resolution}")
                
                    performance_out = pl.Path("{}/{}/{}/{}/{}/{}/performance.csv".format(output_directory, model, var, experiment, region, resolution))
                    if not overwrites and performance_out.exists():
                        print(f"\t\t\t\t\t- Performance indices already saved in {performance_out}")
                        continue
                
                    meta_file = pl.Path("{}/{}/{}/{}/{}/{}/meta.parquet".format(simulation_directory, model, var, experiment, region, resolution))
                    meta = pd.read_parquet(meta_file)
                    # --- Level 5 Detail: File Load ---
                    print(f"\t\t\t\t\t- Loaded meta data {meta_file}")

                    performance_dfs = []
                    
                    for index, row in meta.iterrows():
                        if var == "q":
                            observed_discharge_file = pl.Path("{}/{}/{}/{}/data/discharge_{}.parquet".format(observation_directory, experiment, var, region, index))
                        observed_discharge = pd.read_parquet(observed_discharge_file)
                        # --- Level 6 Detail: Station Data Load ---
                        print(f"\t\t\t\t\t\t- Loaded observed discharge for station {index}: {observed_discharge_file}")
                        simulated_discharge_file = pl.Path("{}/{}/{}/{}/{}/{}/data/discharge_{}.parquet".format(simulation_directory, model, var, experiment, region, resolution, index))
                        simulated_discharge = pd.read_parquet(simulated_discharge_file)
                        print(f"\t\t\t\t\t\t- Loaded simulated discharge for station {index}: {simulated_discharge_file}")
                        
                        discharge = pd.merge(observed_discharge, simulated_discharge, on = "date")
                        discharge = discharge.rename(columns = {"discharge_x": "observed",
                                                                "discharge_y": "simulated"})
                        discharge = discharge[["date", "observed", "simulated"]]
                        
                        if discharge.index.size == 0:
                            print(f"\t\t\t\t\t\t> No discharge in overlap period for gauge {index}, skipping...")
                            continue
                        
                        if discharge.index.size < min_overlap:
                            print(f"\t\t\t\t\t\t> Too few discharge in overlap period (only {discharge.index.size} days) for gauge {index}, skipping...")
                            continue
                        
                        for aggregation, format in aggregations.items():
                            
                            aggregated_discharge = discharge.copy()
                            aggregated_discharge["agg"] = [dt.datetime.strftime(date, format) for date in aggregated_discharge["date"]]
                            aggregated_discharge = aggregated_discharge.groupby("agg").aggregate({"date": "min",
                                                                                                "observed": "mean",
                                                                                                "simulated": "mean"})
                            
                            me = np.mean(aggregated_discharge["simulated"] - aggregated_discharge["observed"])
                            rmse = np.sqrt(np.mean((aggregated_discharge["simulated"] - aggregated_discharge["observed"])**2))
                            nme = me / np.mean(aggregated_discharge["observed"])
                            nrmse = rmse / np.mean(aggregated_discharge["observed"])
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore", category=RuntimeWarning)
                                kge, r, alpha, beta = he.evaluator(he.kge, aggregated_discharge["simulated"], aggregated_discharge["observed"])
                                kge_prime, r_prime, alpha_prime, beta_prime = he.evaluator(he.kgeprime, aggregated_discharge["simulated"], aggregated_discharge["observed"])
                                kge_np, r_np, alpha_np, beta_np = he.evaluator(he.kgenp, aggregated_discharge["simulated"], aggregated_discharge["observed"])
                                nse = he.evaluator(he.nse, aggregated_discharge["simulated"], aggregated_discharge["observed"])
                            
                            performance_df = {"station": index,
                                            "aggregation": aggregation,
                                            "nme": nme,
                                            "nrmse": nrmse,
                                            "nse": nse[0],
                                            "kge": kge[0],
                                            "kge_r": r[0],
                                            "kge_alpha": alpha[0],
                                            "kge_beta": beta[0],
                                            "kge-prime": kge_prime[0],
                                            "kge-prime_r": r_prime[0],
                                            "kge-prime_alpha": alpha_prime[0],
                                            "kge-prime_beta": beta_prime[0],
                                            "kge-nonpar": kge_np[0],
                                            "kge-nonpar_r": r_np[0],
                                            "kge-nonpar_alpha": alpha_np[0],
                                            "kge-nonpar_beta": beta_np[0],}
                            performance_dfs.append(performance_df)
                            
                    if len(performance_dfs) <= 0:
                        continue
                    
                    performance_df = {}
                    for key in performance_dfs[0].keys():
                        performance_df[key] = [df[key] for df in performance_dfs]
                    performance_df = pd.DataFrame(performance_df)
                    performance_df["model"] = model
                    performance_df["variable"] = var
                    performance_df["experiment"] = experiment
                    performance_df["region"] = region
                    performance_df["resolution"] = resolution
                    pattern = f"{model}_{var}_{experiment}_{region}_{resolution}"
                    performance_df["pattern"] = pattern
                    
                    performance_df = pd.merge(performance_df, meta, left_on = "station", right_index = True)
                    performance_df = performance_df.reset_index(drop = True)
                    
                    performance_out.parent.mkdir(parents=True, exist_ok=True)
                    performance_df.to_csv(performance_out, index = False)
                    
                    # --- Level 5 Footer/Success Message ---
                    print(f"\t\t\t\t\t- SUCCESS: Performance indices saved to {performance_out}")
                    
    # --- Model Footer ---
    print(f"\n{'='*60}")
    print(f"FINISHED Model: {model}")
    print(f"{'='*60}\n")


print("\nAll model performance indices saved successfully.")
