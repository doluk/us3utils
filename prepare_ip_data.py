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

    # Slope and intersect should only be fitted for the 50% to 80% of the radial domain
    r_min = min(radii)
    r_max = max(radii)
    r_range = r_max - r_min
    
    r_start = r_min + 0.50 * r_range
    r_end = r_min + 0.80 * r_range
    
    fit_radii = []
    fit_readings = []
    for r, v in zip(radii, readings):
        if r_start <= r <= r_end:
            fit_radii.append(r)
            fit_readings.append(v)
            
    if not fit_radii:
        # Fallback to full data if domain is too small or no points in range
        # Although with 30% of the range, there should be points if the distribution is decent.
        fit_radii, fit_readings = radii, readings

    # Linear regression: y = mx + c
    slope, intercept = np.polyfit(fit_radii, fit_readings, 1)

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
    all_files = list(input_dir.iterdir())
    ip_files = sorted([f for f in all_files if f.is_file() and ('.IP' in f.suffix.upper() or '.IP' in f.name.upper())])

    if not ip_files:
        print(f"No *.IP files found in {input_dir}")
        return

    # Group files by their cell suffix (e.g., .IP1, .IP2, or .IP if generic)
    # The slope should only consider the same .ip* for the slope
    file_groups = {}
    for f in ip_files:
        suffix = f.suffix.upper()
        if suffix not in file_groups:
            file_groups[suffix] = []
        file_groups[suffix].append(f)

    excluded_scans = []
    total_files_processed = 0

    # Process each cell group independently
    for suffix, group_files in sorted(file_groups.items()):
        valid_slopes = []
        # Sort files within the group to process scans in chronological order
        group_files.sort()
        
        for file_path in group_files:
            total_files_processed += 1
            slope, result = process_ip_file(file_path, nth, output_dir)
            if slope is None:
                continue
            change = -200
            change_prev = -200
            is_faulty = False
            # Check against previous two valid scans in THIS group
            if len(valid_slopes) >= 1:
                # Check against the last valid scan
                last_slope = valid_slopes[-1]
                change = abs(slope - last_slope) / abs(last_slope) if last_slope != 0 else 0
                if change > 0.1:
                    is_faulty = True
                
                # Check against the scan before that if it exists
                if not is_faulty and len(valid_slopes) >= 2:
                    prev_slope = valid_slopes[-2]
                    change_prev = abs(slope - prev_slope) / abs(prev_slope) if prev_slope != 0 else 0
                    if change_prev > 0.1:
                        is_faulty = True

            if is_faulty:
                excluded_scans.append(file_path.name + f"{slope} {change} {change_prev}")
            else:
                valid_slopes.append(slope)
                # Save the file
                output_path, content = result
                print(f"Processed {file_path.name}: Slope = {slope:.4f}")
                try:
                    with open(output_path, 'w') as f:
                        f.writelines(content)
                except Exception as e:
                    print(f"Error writing to {output_path}: {e}")

    if excluded_scans:
        print("\nExcluded scans (faulty due to slope change > 5% within same cell group):")
        for scan in excluded_scans:
            print(f"- {scan}")
    else:
        print("\nNo scans were excluded.")

    print(f"\nProcessed {total_files_processed} files. Results saved in {output_dir}")

if __name__ == '__main__':
    main()
