import pathlib
import re
import numpy as np
import pandas as pd
from collections import defaultdict
from scipy.interpolate import interp1d
from read_auc import read_auc

DIR = pathlib.Path(r"PATH")
FILEPATTERN = re.compile(r"(?P<runID>[A-Za-z0-9-_]*)\.(?P<optic>[A-Z]*)\.(?P<cell>[0-9])\.(?P<channel>[A-Z])\.(?P<wavelength>[0-9]+)\.auc")


def align_scan_to_reference(radial_positions, scan_values, reference_positions, reference_values, align_range=(6.0, 6.2)):
    """
    Align a scan to a reference by interpolating in the specified range and applying offset correction.

    Parameters:
    - radial_positions: array of radial positions for the scan
    - scan_values: array of absorbance values for the scan
    - reference_positions: array of radial positions for the reference
    - reference_values: array of absorbance values for the reference
    - align_range: tuple (min_radius, max_radius) for alignment region

    Returns:
    - aligned_scan_values: scan values shifted to align with reference
    """
    min_align, max_align = align_range
    
    # Create interpolation functions for both scan and reference
    scan_interp = interp1d(radial_positions, scan_values, kind='linear',
                           bounds_error=False, fill_value=np.nan)
    ref_interp = interp1d(reference_positions, reference_values, kind='linear',
                          bounds_error=False, fill_value=np.nan)
    
    # Create dense grid in alignment region
    align_positions = np.linspace(min_align, max_align, 100)
    
    # Interpolate both curves in alignment region
    scan_align_values = scan_interp(align_positions)
    ref_align_values = ref_interp(align_positions)
    
    # Calculate average difference (offset) in alignment region
    # Only use finite values
    valid_mask = np.isfinite(scan_align_values) & np.isfinite(ref_align_values)
    
    if np.any(valid_mask):
        offset = np.mean(ref_align_values[valid_mask] - scan_align_values[valid_mask])
    else:
        offset = 0.0
        print(f"Warning: No valid values in alignment region {align_range}")
    
    # Apply offset to entire scan
    aligned_scan_values = scan_values + offset
    
    return aligned_scan_values



def process_auc_files():
    """Process all .auc files in the directory according to the specified workflow."""
    
    # Step 1: Find all .auc files and extract metadata
    auc_files = list(DIR.glob("*.auc"))
    
    # Dictionary to store processed data grouped by runID, cell, channel
    grouped_data = {}
    
    print(f"Found {len(auc_files)} .auc files")
    counter = 0
    for file_path in auc_files:
        filename = file_path.name
        
        # Extract metadata from filename
        match = FILEPATTERN.match(filename)
        if not match:
            print(f"Skipping file {filename} - doesn't match pattern")
            continue
        
        runID = match.group('runID')
        optic = match.group('optic')
        cell = match.group('cell')
        channel = match.group('channel')
        wavelength = int(match.group('wavelength'))
        
        #print(f"Processing: {filename}")
        #print(f"  runID: {runID}, optic: {optic}, cell: {cell}, channel: {channel}, wavelength: {wavelength}")
        
        try:
            # Read the .auc file
            data = read_auc(str(file_path))
            
            # Calculate maximum for every radial position
            scan_data = data['scanData']
            if not scan_data:
                print(f"  No scan data found in {filename}")
                continue
            if scan_data[-1]['seconds'] > 35637:
                print(f"  runID: {runID}, optic: {optic}, cell: {cell}, channel: {channel}, wavelength: {wavelength}")
                print(f"{scan_data[-1]['seconds']} {scan_data[-1]['omega2t']}")
                counter += 1
            #continue
            # Get the number of radial positions from the first scan
            num_positions = data['valueCount']
            
            # Initialize arrays for radial positions and maximum values
            max_values = np.full(num_positions, 0.001)
            
            # Calculate radial positions
            # Based on the read_auc.py code, we need to reconstruct the radius vector
            # This seems to be missing from the original read_auc function
            min_radius = 0  # This would need to be extracted from the file
            delta_radius = 0  # This would need to be extracted from the file
            
            # Since the original read_auc doesn't return radius info, we'll use index positions
            # In a real implementation, you'd need to modify read_auc to return radius information
            radial_positions = data['radius']
            
            # some scans are slightly shifted interpolate the scan between 6.0 and 6.2 and shift the whole scan by the offset to the
            # average value in that region
            aligned_scans = []
            if scan_data:
                reference_values = np.array(scan_data[0]['reading_values'])

            
                # Find maximum value at each radial position across all scans
                for i, scan in enumerate(scan_data):
                    reading_values = np.array(scan['reading_values'])
                    if len(reading_values) == num_positions:
                        if i == 0:
                            aligned_values = reading_values
                        else:
                            aligned_values = align_scan_to_reference(radial_positions, reading_values,
                                                                     radial_positions, reference_values,
                                                                     align_range=(6.0, 6.2))
                        aligned_scans.append(aligned_values)
                    else:
                        print(f"  Warning: Scan {i} has {len(reading_values)} values, expected {num_positions}")
                        
            if aligned_scans:
                max_values = np.full(num_positions, 0.001)
                for aligned_scan in aligned_scans:
                    max_values = np.maximum(max_values, aligned_scan)
            else:
                max_values = np.full(num_positions, 0.001)
            
            # Create key for grouping
            group_key = (runID, cell, channel)
            if group_key not in grouped_data:
                grouped_data[group_key] = []
            # Store the data for this wavelength
            grouped_data[group_key].append({
                'wavelength': wavelength,
                'radial_positions': radial_positions,
                'max_values': max_values
            })
            
            print(f"  Successfully processed with {len(scan_data)} scans")
        
        except Exception as e:
            print(f"  Error processing {filename}: {e}")
            continue
    #print(counter)
    #return
    # Step 2: Process grouped data
    print(f"\nProcessing {len(grouped_data)} groups")
    
    for group_key, wavelength_data in grouped_data.items():
        runID, cell, channel = group_key
        
        print(f"\nProcessing group: runID={runID}, cell={cell}, channel={channel}")
        print(f"  Found {len(wavelength_data)} wavelengths")
        
        # Sort by wavelength
        wavelength_data.sort(key=lambda x: x['wavelength'])
        
        # Create output data structure
        output_data = {}
        
        # Get the radial positions (should be the same for all wavelengths)
        if wavelength_data:
            reference_positions = np.array(wavelength_data[0]['radial_positions'])
            
            # Interpolate to consistent intervals of 0.001
            min_pos = np.min(reference_positions)
            max_pos = np.max(reference_positions)
            
            # Create new radial positions with 0.001 intervals
            new_positions = np.arange(min_pos, max_pos, 0.001)
            
            # Store the interpolated radial positions
            output_data['cm'] = new_positions
            
            # Interpolate each wavelength's data
            for wl_data in wavelength_data:
                wavelength = wl_data['wavelength']
                max_values = wl_data['max_values']
                
                # Create interpolation function
                # Handle potential infinite values
                finite_mask = np.isfinite(max_values)
                if np.any(finite_mask):
                    interp_func = interp1d(
                            reference_positions[finite_mask],
                            max_values[finite_mask],
                            kind='linear',
                            bounds_error=False,
                            fill_value=0
                    )
                    
                    # Interpolate to new positions
                    interpolated_values = interp_func(new_positions)
                    
                    # Store with wavelength as column name
                    output_data[f'{wavelength}nm'] = interpolated_values
                else:
                    # If no finite values, fill with zeros
                    output_data[f'{wavelength}nm'] = np.zeros_like(new_positions)
        
        # Create output filename
        output_filename = f"{runID}_{cell}_{channel}.csv"
        output_path = DIR / output_filename
        
        # Convert to DataFrame and save
        if output_data:
            df = pd.DataFrame(output_data)
            
            # Save as semicolon-separated file
            df.to_csv(output_path, sep=';', index=False)
            
            print(f"  Saved to: {output_filename}")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
        else:
            print(f"  No data to save for group {group_key}")


if __name__ == "__main__":
    process_auc_files()
