import os
import argparse
import sys
import glob
import numpy as np
from pathlib import Path

def get_args():
    parser = argparse.ArgumentParser(description='Process raw text file matching *.IP from a directory')
    parser.add_argument('--input_dir', type=str, help='Directory containing the input *.IP files')
    parser.add_argument('--output_dir', type=str, help='Directory to save the resulting files')
    parser.add_argument('--nth', type=int, help='Exclude every nth line (excluding header)')

    # Use parse_known_args for manual interactive prompt fallback if needed
    args, unknown = parser.parse_known_args()

    # Interactively prompt for missing arguments
    if not args.input_dir:
        args.input_dir = input('Enter input directory: ').strip()
    if not args.output_dir:
        args.output_dir = input('Enter output directory: ').strip()
    if not args.nth:
        while True:
            try:
                args.nth = int(input('Enter n (to exclude every nth line): ').strip())
                break
            except ValueError:
                print('Please enter a valid integer for n.')

    return args

def process_ip_file(file_path, nth, output_dir):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None, None

    if len(lines) < 2:
        return None, None

    header = lines[:2]
    data_lines = lines[2:]

    # Exclude every nth line from data_lines (1-indexed exclusion)
    # If nth = 2, we exclude lines 2, 4, 6... (0-indexed indices 1, 3, 5...)
    filtered_data_lines = [line for i, line in enumerate(data_lines) if (i + 1) % nth != 0]

    # Parse radius and reading for linear regression
    radii = []
    readings = []
    for line in filtered_data_lines:
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                radii.append(float(parts[0]))
                readings.append(float(parts[-1]))
            except ValueError:
                continue

    if not radii:
        return None, None

    # Linear regression: y = mx + c
    slope, intercept = np.polyfit(radii, readings, 1)

    # Prepare the output file content
    output_content = header + filtered_data_lines
    output_path = Path(output_dir) / Path(file_path).name

    return slope, (output_path, output_content)

def main():
    args = get_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    nth = args.nth

    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory.")
        sys.exit(1)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    # Find all files matching *.IP or *.IPX where X is a cell number
    # Cluster_packs uses .IPX where X is cell number.
    # The requirement says matching *.IP. 
    # Let's search for *.IP* and check if the name contains .IP
    all_files = list(input_dir.iterdir())
    ip_files = sorted([f for f in all_files if f.is_file() and ('.IP' in f.suffix or '.IP' in f.name)])

    if not ip_files:
        print(f"No *.IP files found in {input_dir}")
        return

    valid_slopes = []
    excluded_scans = []

    for file_path in ip_files:
        slope, result = process_ip_file(file_path, nth, output_dir)
        if slope is None:
            continue

        is_faulty = False
        # "Compare the previous two valid scans and their respective fitted linear function 
        # to the fitted linear function of the current scan. a change in the slop of more 
        # than 5% makes the scan faulty and it should be excluded."
        
        # Check against previous two valid scans
        if len(valid_slopes) >= 1:
            # Check against the last valid scan
            last_slope = valid_slopes[-1]
            change = abs(slope - last_slope) / abs(last_slope) if last_slope != 0 else 0
            if change > 0.05:
                is_faulty = True
            
            # Check against the scan before that if it exists
            if not is_faulty and len(valid_slopes) >= 2:
                prev_slope = valid_slopes[-2]
                change_prev = abs(slope - prev_slope) / abs(prev_slope) if prev_slope != 0 else 0
                if change_prev > 0.05:
                    is_faulty = True

        if is_faulty:
            excluded_scans.append(file_path.name)
        else:
            valid_slopes.append(slope)
            # Save the file
            output_path, content = result
            try:
                with open(output_path, 'w') as f:
                    f.writelines(content)
            except Exception as e:
                print(f"Error writing to {output_path}: {e}")

    if excluded_scans:
        print("\nExcluded scans (faulty due to slope change > 5%):")
        for scan in excluded_scans:
            print(f"- {scan}")
    else:
        print("\nNo scans were excluded.")

    print(f"\nProcessed {len(ip_files)} files. Results saved in {output_dir}")

if __name__ == '__main__':
    main()
