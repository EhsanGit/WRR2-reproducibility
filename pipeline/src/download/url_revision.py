"""
url_revision.py  (download, step 2)

Keeps only the URLs of the experiment in each <model>_<experiment>.txt list
written by extract_urls.py (plus the mask and uparea files) and writes the list back.

Inputs:  *.txt in the current folder
Outputs: the same files, filtered in place

Usage:
    python url_revision.py

Author: Ehsan Modiri - UFZ
Date: 2026-10-19
"""
import os
import re

# List all .txt files in the current directory
txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]

# Sort files alphabetically
txt_files.sort()

# Pattern to extract model name and experiment ID from the filenames
pattern = r"([a-zA-Z0-9_]+)_(exp\d+)\.txt"

# Loop through each file in the directory
for file_name in txt_files:
    # Try to match the pattern and extract model and experiment ID
    match = re.match(pattern, file_name)
    if match:
        model = match.group(1)  # Extracted model name
        exp_id = match.group(2)  # Extracted experiment ID
        
        print(f"Processing file: {file_name} (Model: {model}, Exp ID: {exp_id})")

        # Open the file for reading
        with open(file_name, 'r') as f:
            # Read all lines from the file
            lines = f.readlines()

        # Filter lines: include only those containing exp_id, 'mask', or 'uparea'
        filtered_lines = [
            line for line in lines
            if exp_id in line or 'mask' in line or 'uparea' in line
        ]

        # Write the filtered lines back to the file
        with open(file_name, 'w') as f:
            f.writelines(filtered_lines)

        print(f"Filtered lines have been written back to {file_name}")
    else:
        print(f"File {file_name} does not match the expected format. Skipping...")
