#!/bin/bash
# -----------------------------------------------------------------------------
# wget_download.sh  (download, step 3)
#
# Downloads the files listed in one <model>_<experiment>.txt (one SLURM array
# task per list) into /work/modiri/4dhydro/<model>/<experiment>/, skipping files
# that already exist.
#
# Inputs:  *.txt URL lists in the submit folder (extract_urls.py, url_revision.py)
# Outputs: NetCDF files under /work/modiri/4dhydro/<model>/<experiment>/
#
# Usage:   sbatch -p download wget_download.sh   (set --array to the number of lists - 1)
#
# Author: Ehsan Modiri - UFZ
# Date: 2026-10-19
# -----------------------------------------------------------------------------
#SBATCH --job-name=Tier2_download
#SBATCH --partition=transfer
#SBATCH --chdir=/home/modiri/project/4dhydro/wp5/tier2_benchmarking/src/download
#SBATCH --output=/home/modiri/project/4dhydro/wp5/tier2_benchmarking/logs/%x-%A-%a.out
#SBATCH --error=/home/modiri/project/4dhydro/wp5/tier2_benchmarking/logs/%x-%A-%a.err
#SBATCH --mem-per-cpu=5G
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=1
#SBATCH --array=0-0

# Enable script to exit immediately if a command fails
set -e

# Detect the current directory and store it in a variable
CURRENT_DIR=$(pwd)
echo "Current directory: $CURRENT_DIR"

# Get the list of .txt files in the current directory
FILES=($(ls *.txt))

# Check if there are any .txt files
if [ ${#FILES[@]} -eq 0 ]; then
    echo "No .txt files found in the directory!"
    exit 1
fi

# Get the .txt file for the current SLURM array task
TXT_FILE=${FILES[$SLURM_ARRAY_TASK_ID]}
echo "TXT file: $TXT_FILE"

# Extract model and experiment from the file name (assumes format: {model_name}_{experiment_ID}.txt)
MODEL_NAME=$(basename "$TXT_FILE" | cut -d'_' -f1)
echo "Model name: $MODEL_NAME"
EXPERIMENT_ID=$(basename "$TXT_FILE" | cut -d'_' -f2 | cut -d'.' -f1)
echo "Experiment ID: $EXPERIMENT_ID"

# Define the target directory structure
BASE_DIR="/work/modiri/4dhydro"
TARGET_DIR="${BASE_DIR}/${MODEL_NAME}/${EXPERIMENT_ID}"

# Create the target directory if it doesn't exist
mkdir -p "$TARGET_DIR"
echo "Target directory: $TARGET_DIR is created"

# Change to the directory where the URLs will be downloaded
cd "$TARGET_DIR"
echo "Changed to target directory: $TARGET_DIR"

# Download the list; -nc skips files that already exist
wget -nc -i "${CURRENT_DIR}/${TXT_FILE}" -nv --progress=bar:force

# Check if the download was successful
if [ $? -eq 0 ]; then
    echo "All files downloaded successfully for ${TXT_FILE}"
else
    echo "Some files were not downloaded for ${TXT_FILE}"
fi

echo "Job completed successfully."
