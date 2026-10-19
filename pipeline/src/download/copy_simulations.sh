#!/bin/bash
# -----------------------------------------------------------------------------
# copy_simulations.sh  (download, step 5)
#
# Copies the checked downloads of one model from /work to the tier-2 simulation
# tree (rsync, one SLURM array task per source folder).
#
# Inputs:  /gpfs1/work/modiri/4dhydro/<model>/
# Outputs: /data/4dhydro/data/processed/tier2/simulations/<model>/
#
# Usage:   sbatch -p download copy_simulations.sh
#          (list the models to copy in SOURCE_DIRS and set --array accordingly)
#
# Author: Ehsan Modiri - UFZ
# Date: 2026-10-19
# -----------------------------------------------------------------------------
#SBATCH --job-name=Copy_Tier2_Simulations
#SBATCH --chdir=/home/modiri/project/4dhydro/wp5/tier2_benchmarking/src/download
#SBATCH --output=/home/modiri/project/4dhydro/wp5/tier2_benchmarking/logs/%x-%A-%a.out
#SBATCH --error=/home/modiri/project/4dhydro/wp5/tier2_benchmarking/logs/%x-%A-%a.err
#SBATCH --mem-per-cpu=7G
#SBATCH --time=05:00:00
#SBATCH --cpus-per-task=1
#SBATCH --array=0-0

# Source folders, one per array task (uncomment the models to copy)
SOURCE_DIRS=( 
              # "/gpfs1/work/modiri/4dhydro/clm"
              # "/gpfs1/work/modiri/4dhydro/geoframe"
              "/gpfs1/work/modiri/4dhydro/jules"
              # "/gpfs1/work/modiri/4dhydro/pcrglobwb"
              # "/gpfs1/work/modiri/4dhydro/tetis"
              # "/gpfs1/work/modiri/4dhydro/wflowsbm"
              )

# Define the target base directory
TARGET_BASE="/data/4dhydro/data/processed/tier2/simulations"

# Select the source directory for this task
SOURCE_DIR=${SOURCE_DIRS[$SLURM_ARRAY_TASK_ID]}

# Run the rsync command to copy the selected directory
rsync -av --no-times "$SOURCE_DIR" "$TARGET_BASE/"

# Print the source and target directories
echo "Copied $SOURCE_DIR to $TARGET_BASE"

# Print the job is done
echo "Job done!"
