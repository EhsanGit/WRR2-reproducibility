"""
mask_uparea_checking.py  (step 1)

Checks that every model/experiment folder has a mask and an upstream-area file
for each region and resolution, named {model}_{forcing}_{mask|uparea}_{region}_{res}.nc.
A missing file is copied from an earlier experiment of the same model (same
region and resolution, with simple resolution aliases). Dry run by default.

Inputs:  <root>/simulations/<model>/<experiment>/*.nc
Outputs: missing mask/uparea files copied into <root>/simulations/<model>/<experiment>/ (only with --apply)
Folders: root = $T2B_TIER2_DIRECTORY (default /data/4dhydro/data/processed/tier2/),
save tree = <root>/saves_$T2B_DESIRED_NAME (default saves_eo_alternative).

Usage:
    python mask_uparea_checking.py --model mhm --experiment exp35,exp36          # dry run
    python mask_uparea_checking.py --model mhm --experiment exp35,exp36 --apply

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
import os
from pathlib import Path
import shutil
import re
import argparse

# ---------- toggles ----------
BASE_DIR = Path(os.environ.get("T2B_TIER2_DIRECTORY", "/data/4dhydro/data/processed/tier2/")) / "simulations"
MODELS = sorted(["pcrglobwb"])
EXPERIMENTS = sorted(["exp10","exp20","exp21","exp30","exp31","exp32","exp33","exp34","exp41","exp42","exp44"])
VARS = ["mask","uparea"]
DRY_RUN = True  # set False to actually copy

# ---------- optional command line overrides (defaults = toggles above) ----------
parser = argparse.ArgumentParser(description="Check and fill missing mask/uparea files.")
parser.add_argument("--experiment", default=None, help="Comma-separated experiments, e.g. exp35,exp36 (overrides EXPERIMENTS)")
parser.add_argument("--model", default=None, help="Comma-separated models, e.g. mhm,clm (overrides MODELS)")
parser.add_argument("--apply", action="store_true", help="Actually copy files (default: dry run)")
args, _ = parser.parse_known_args()
# Experiments searched for source files: the default list plus any given on the command line
SOURCE_EXPERIMENTS = list(EXPERIMENTS)
if args.experiment:
    EXPERIMENTS = sorted([e.strip() for e in args.experiment.split(",") if e.strip()])
    SOURCE_EXPERIMENTS = sorted(set(SOURCE_EXPERIMENTS) | set(EXPERIMENTS))
if args.model:
    MODELS = sorted([m.strip() for m in args.model.split(",") if m.strip()])
if args.apply:
    DRY_RUN = False

# ---------- helpers ----------
def forcing_for(exp: str, region: str) -> str:
    if exp in {"exp10", "exp20", "exp21"}:
        return {"tugela": "chirps", "po": "emo", "rhine": "emo"}.get(region, "emo")
    # Existing exp3x/exp4x experiments keep their original forcing label
    if exp in {"exp30", "exp31", "exp32", "exp33", "exp34", "exp41", "exp42", "exp43", "exp44"}:
        return "mergedera5gpmsm2a"
    # New experiments: exp40 and expX1-expX4 -> eo; expX5-expX8 -> emo (po/rhine) / chirps (tugela)
    m = re.match(r"^exp\d(\d)$", exp)
    if exp == "exp40" or (m and m.group(1) in "1234"):
        return "eo"
    if m and m.group(1) in "5678":
        return {"tugela": "chirps", "po": "emo", "rhine": "emo"}.get(region, "emo")
    return "mergedera5gpmsm2a"

# Parse region + resolution from filenames like:
#   model_forcing_var_REGION_RES_.nc...   (tws/q files: next token after RES is an underscore)
#   model_forcing_mask_REGION_RES.nc      (mask/uparea: RES is right before .nc)
# Captures REGION as group 1, RES as group 2 (RES = any non-underscore, non-dot chunk)
def parse_region_res(model: str, name: str):
    m = re.match(rf"^{re.escape(model)}_[^_]+_[A-Za-z0-9]+_([a-z0-9]+)_([^_.]+)(?:_|\.nc)", name)
    if m:
        region, res = m.group(1), m.group(2)
        return region, res
    return None, None

# Resolution aliases to tolerate naming differences during lookup
# Extend here if you discover more mismatches
def res_aliases(res: str):
    if res == "0p0166deg":
        return [res, "0p01667deg"]
    if res == "0p01667deg":
        return [res, "0p0166deg"]
    return [res]

if not BASE_DIR.is_dir():
    raise SystemExit(f"Base dir not found: {BASE_DIR}")

overall_created = overall_present = overall_missing = 0

for model in sorted(MODELS):
    model_dir = BASE_DIR / model
    if not model_dir.is_dir():
        print(f"skip (no dir): {model_dir}")
        continue

    print(f"\n=== Model: {model} ===")
    existing_exps = sorted([e for e in EXPERIMENTS if (model_dir / e).is_dir()])
    if not existing_exps:
        print("  (no experiment directories found)")
        continue
    source_exps = sorted([e for e in SOURCE_EXPERIMENTS if (model_dir / e).is_dir()])

    m_created = m_present = m_missing = 0

    for exp in existing_exps:
        exp_dir = model_dir / exp

        # Discover (region, res) pairs by scanning filenames in this exp
        pairs = set()
        for p in exp_dir.glob("*.nc"):
            region, res = parse_region_res(model, p.name)
            if region and res:
                pairs.add((region, res))

        if not pairs:
            print(f"  No region/res discovered in {exp_dir}")
            continue

        for (region, res) in sorted(pairs):
            forcing = forcing_for(exp, region)
            for var in VARS:
                target_name = f"{model}_{forcing}_{var}_{region}_{res}.nc"
                target_path = exp_dir / target_name

                if target_path.exists():
                    m_present += 1
                    continue

                # Search previous experiments (same model) for any *_{var}_{region}_{res}.nc
                # Try exact resolution and its aliases (handles 0p0166deg vs 0p01667deg)
                try:
                    start_idx = source_exps.index(exp)
                except ValueError:
                    start_idx = 0

                source_path = None
                for idx in range(start_idx - 1, -1, -1):
                    prev_dir = model_dir / source_exps[idx]
                    if not prev_dir.is_dir():
                        continue
                    for res_try in res_aliases(res):
                        tail = f"_{var}_{region}_{res_try}.nc"
                        for cand in prev_dir.glob(f"*{tail}"):
                            if cand.name.startswith(f"{model}_"):
                                source_path = cand
                                break
                        if source_path:
                            break
                    if source_path:
                        break

                if source_path:
                    if DRY_RUN:
                        print(f"[DRY] COPY {source_path} -> {target_path}")
                        m_created += 1
                    else:
                        try:
                            exp_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(source_path, target_path)
                            print(f"COPIED {source_path} -> {target_path}")
                            m_created += 1
                        except Exception as e:
                            print(f"FAILED: {source_path} -> {target_path}: {e}")
                            m_missing += 1
                else:
                    print(f"No previous source found for {target_path}")
                    m_missing += 1

    overall_created += m_created
    overall_present += m_present
    overall_missing += m_missing
    print(f"- {model}: created {m_created}, present {m_present}, unresolved {m_missing}")

print(f"\nTotals: created: {overall_created}, present: {overall_present}, unresolved: {overall_missing} | Mode: {'DRY' if DRY_RUN else 'APPLY'}")
