"""
pcr_deliniation_files.py

Copies the PCR-GLOBWB mask and upstream-area files (delivered once, in the
delineation folder) into every exp3x folder of PCR-GLOBWB, without the forcing
token in the name, so that the preprocessing finds them.

Inputs:  /data/4dhydro/data/processed/tier2/simulations/pcrglobwb/delineation/*.nc
Outputs: /data/4dhydro/data/processed/tier2/simulations/pcrglobwb/exp3*/pcrglobwb_{mask|uparea}_<region>_<res>.nc

Usage:
    python pcr_deliniation_files.py

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
import os
import shutil

# Define the source directory and the target base directory
source_dir = '/data/4dhydro/data/processed/tier2/simulations/pcrglobwb/delineation'
target_base_dir = '/data/4dhydro/data/processed/tier2/simulations/pcrglobwb/'

# List of filenames to copy
files_to_copy = [
    "pcrglobwb_chirps_mask_tugela_03min.nc",
    "pcrglobwb_chirps_mask_tugela_30sec.nc",
    "pcrglobwb_chirps_uparea_tugela_03min.nc",
    "pcrglobwb_chirps_uparea_tugela_30sec.nc",
    "pcrglobwb_emo_mask_po_03min.nc",
    "pcrglobwb_emo_mask_po_30sec.nc",
    "pcrglobwb_emo_mask_rhine_03min.nc",
    "pcrglobwb_emo_mask_rhine_30sec.nc",
    "pcrglobwb_emo_uparea_po_03min.nc",
    "pcrglobwb_emo_uparea_po_30sec.nc",
    "pcrglobwb_emo_uparea_rhine_03min.nc",
    "pcrglobwb_emo_uparea_rhine_30sec.nc"
]

# Identify directories starting with 'exp3'
exp3_dirs = [d for d in os.listdir(target_base_dir) if d.startswith('exp3') and os.path.isdir(os.path.join(target_base_dir, d))]

# Function to remove 'chirps' and 'emo' from filenames
def clean_filename(filename):
    return filename.replace("chirps_", "").replace("emo_", "")

# Copy and rename the files in each exp3 directory
for exp3_dir in exp3_dirs:
    # Create the target directory path
    target_dir = os.path.join(target_base_dir, exp3_dir)
    
    # Copy files to the target directory
    for file in files_to_copy:
        # Construct the source and target file paths
        source_file = os.path.join(source_dir, file)
        
        # Clean the filename by removing "chirps" and "emo"
        target_file_name = clean_filename(file)
        target_file = os.path.join(target_dir, target_file_name)
        
        # Copy the file
        shutil.copy(source_file, target_file)
        print(f"Copied {file} to {target_file_name}")
